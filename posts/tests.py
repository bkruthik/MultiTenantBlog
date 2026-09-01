from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from tenants.models import Tenant, ChatMessage
from memberships.models import Membership
from posts.models import Post, Like, Comment
from posts.templatetags.video_tags import youtube_embed_url, is_direct_video


class MultiTenantBlogRBACAndSecurityTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Users
        self.admin_user = User.objects.create_user(username='admin_user', password='password123')
        self.editor_user = User.objects.create_user(username='editor_user', password='password123')
        self.viewer_user = User.objects.create_user(username='viewer_user', password='password123')
        self.other_user = User.objects.create_user(username='other_user', password='password123')

        # Tenants
        self.public_tenant_a = Tenant.objects.create(name='Tenant A', slug='tenant-a', is_private=False)
        self.private_tenant_b = Tenant.objects.create(name='Tenant B', slug='tenant-b', is_private=True)
        self.sports_tenant = Tenant.objects.create(name='Sports Hub', slug='sports-hub', description='All sports discussions', is_private=False)

        # Memberships for Tenant A
        self.mem_admin = Membership.objects.create(user=self.admin_user, tenant=self.public_tenant_a, role='ADMIN')
        self.mem_editor = Membership.objects.create(user=self.editor_user, tenant=self.public_tenant_a, role='EDITOR')
        self.mem_viewer = Membership.objects.create(user=self.viewer_user, tenant=self.public_tenant_a, role='VIEWER')

        # Membership for Tenant B (only other_user is admin in B)
        Membership.objects.create(user=self.other_user, tenant=self.private_tenant_b, role='ADMIN')

        # Posts
        self.post_a1 = Post.objects.create(
            author=self.admin_user,
            tenant=self.public_tenant_a,
            title='Post A1 by Admin',
            content='Content for A1 Django community'
        )
        self.post_a2 = Post.objects.create(
            author=self.editor_user,
            tenant=self.public_tenant_a,
            title='Post A2 python tips',
            content='Awesome Python tricks'
        )
        self.post_b1 = Post.objects.create(
            author=self.other_user,
            tenant=self.private_tenant_b,
            title='Post B1 by Other',
            content='Secret content for B1'
        )

    # 1. Unauthenticated / Anonymous Access
    def test_anonymous_redirected_to_login(self):
        urls = [
            reverse('home'),
            reverse('post_list', args=[self.public_tenant_a.id]),
            reverse('post', args=[self.public_tenant_a.id]),
            reverse('post_detail', args=[self.public_tenant_a.id, self.post_a1.id]),
            reverse('post_edit', args=[self.public_tenant_a.id, self.post_a1.id]),
            reverse('post_delete', args=[self.public_tenant_a.id, self.post_a1.id]),
            reverse('profile'),
            reverse('explore'),
            reverse('tenant_create'),
            reverse('tenant_members', args=[self.public_tenant_a.id]),
        ]
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertIn('/accounts/login/', response.url)

    # 2. ADMIN Permissions
    def test_admin_can_view_create_edit_delete(self):
        self.client.login(username='admin_user', password='password123')

        # View List
        res = self.client.get(reverse('post_list', args=[self.public_tenant_a.id]))
        self.assertEqual(res.status_code, 200)

        # View Detail
        res = self.client.get(reverse('post_detail', args=[self.public_tenant_a.id, self.post_a1.id]))
        self.assertEqual(res.status_code, 200)

        # Create Post GET and POST
        res = self.client.get(reverse('post', args=[self.public_tenant_a.id]))
        self.assertEqual(res.status_code, 200)
        res = self.client.post(reverse('post', args=[self.public_tenant_a.id]), {
            'title': 'New Admin Post',
            'content': 'Admin post body'
        })
        self.assertRedirects(res, reverse('post_list', args=[self.public_tenant_a.id]))
        self.assertTrue(Post.objects.filter(title='New Admin Post', tenant=self.public_tenant_a).exists())

        # Edit Post GET and POST
        res = self.client.get(reverse('post_edit', args=[self.public_tenant_a.id, self.post_a1.id]))
        self.assertEqual(res.status_code, 200)
        res = self.client.post(reverse('post_edit', args=[self.public_tenant_a.id, self.post_a1.id]), {
            'title': 'Updated Post A1',
            'content': 'Updated content'
        })
        self.assertRedirects(res, reverse('post_detail', args=[self.public_tenant_a.id, self.post_a1.id]))
        self.post_a1.refresh_from_db()
        self.assertEqual(self.post_a1.title, 'Updated Post A1')

        # Delete Post GET (confirmation) and POST (action)
        res = self.client.get(reverse('post_delete', args=[self.public_tenant_a.id, self.post_a1.id]))
        self.assertEqual(res.status_code, 200)
        self.assertTrue(Post.objects.filter(id=self.post_a1.id).exists())

        res = self.client.post(reverse('post_delete', args=[self.public_tenant_a.id, self.post_a1.id]))
        self.assertRedirects(res, reverse('post_list', args=[self.public_tenant_a.id]))
        self.assertFalse(Post.objects.filter(id=self.post_a1.id).exists())

    # 3. EDITOR Permissions
    def test_editor_can_view_create_edit_but_not_delete(self):
        self.client.login(username='editor_user', password='password123')

        # View List
        res = self.client.get(reverse('post_list', args=[self.public_tenant_a.id]))
        self.assertEqual(res.status_code, 200)

        # Create
        res = self.client.post(reverse('post', args=[self.public_tenant_a.id]), {
            'title': 'Editor Post',
            'content': 'Editor content'
        })
        self.assertEqual(res.status_code, 302)

        # Edit
        res = self.client.post(reverse('post_edit', args=[self.public_tenant_a.id, self.post_a1.id]), {
            'title': 'Editor Edited Post',
            'content': 'Edited by editor'
        })
        self.assertEqual(res.status_code, 302)

        # Delete (Must be forbidden - 403)
        res = self.client.get(reverse('post_delete', args=[self.public_tenant_a.id, self.post_a1.id]))
        self.assertEqual(res.status_code, 403)
        res = self.client.post(reverse('post_delete', args=[self.public_tenant_a.id, self.post_a1.id]))
        self.assertEqual(res.status_code, 403)
        self.assertTrue(Post.objects.filter(id=self.post_a1.id).exists())

    # 4. VIEWER Permissions
    def test_viewer_can_view_only(self):
        self.client.login(username='viewer_user', password='password123')

        # View
        res = self.client.get(reverse('post_list', args=[self.public_tenant_a.id]))
        self.assertEqual(res.status_code, 200)
        res = self.client.get(reverse('post_detail', args=[self.public_tenant_a.id, self.post_a1.id]))
        self.assertEqual(res.status_code, 200)

        # Create (Denied - 403)
        res = self.client.get(reverse('post', args=[self.public_tenant_a.id]))
        self.assertEqual(res.status_code, 403)
        res = self.client.post(reverse('post', args=[self.public_tenant_a.id]), {
            'title': 'Viewer Title',
            'content': 'Viewer content'
        })
        self.assertEqual(res.status_code, 403)

        # Edit (Denied - 403)
        res = self.client.get(reverse('post_edit', args=[self.public_tenant_a.id, self.post_a1.id]))
        self.assertEqual(res.status_code, 403)
        res = self.client.post(reverse('post_edit', args=[self.public_tenant_a.id, self.post_a1.id]), {
            'title': 'Hacked by viewer',
            'content': 'Viewer content'
        })
        self.assertEqual(res.status_code, 403)

        # Delete (Denied - 403)
        res = self.client.get(reverse('post_delete', args=[self.public_tenant_a.id, self.post_a1.id]))
        self.assertEqual(res.status_code, 403)
        res = self.client.post(reverse('post_delete', args=[self.public_tenant_a.id, self.post_a1.id]))
        self.assertEqual(res.status_code, 403)

    # 5. Cross-Tenant Isolation
    def test_cross_tenant_access_rejected(self):
        self.client.login(username='admin_user', password='password123')

        # Admin of Tenant A trying to access Tenant B's post via Tenant A's URL -> 404
        res = self.client.get(reverse('post_detail', args=[self.public_tenant_a.id, self.post_b1.id]))
        self.assertEqual(res.status_code, 404)

        res = self.client.post(reverse('post_edit', args=[self.public_tenant_a.id, self.post_b1.id]), {
            'title': 'Tampered title',
            'content': 'Tampered'
        })
        self.assertEqual(res.status_code, 404)

        res = self.client.post(reverse('post_delete', args=[self.public_tenant_a.id, self.post_b1.id]))
        self.assertEqual(res.status_code, 404)

    # 6. Private Tenant Isolation
    def test_private_tenant_requires_membership(self):
        self.client.login(username='admin_user', password='password123')

        # Trying to access private tenant B list -> 403
        res = self.client.get(reverse('post_list', args=[self.private_tenant_b.id]))
        self.assertEqual(res.status_code, 403)

        # Trying to access private tenant B post detail -> 403
        res = self.client.get(reverse('post_detail', args=[self.private_tenant_b.id, self.post_b1.id]))
        self.assertEqual(res.status_code, 403)

    # 7. Signup Flow
    def test_signup_flow(self):
        res = self.client.get(reverse('signup'))
        self.assertEqual(res.status_code, 200)

        res = self.client.post(reverse('signup'), {
            'username': 'new_community_user',
            'password1': 'StrongPass123!@#',
            'password2': 'StrongPass123!@#',
        })
        self.assertRedirects(res, reverse('login'))
        self.assertTrue(User.objects.filter(username='new_community_user').exists())

    # 8. Likes System & Toggle
    def test_likes_toggle_and_tenant_isolation(self):
        self.client.login(username='viewer_user', password='password123')

        # Viewer can like post in Tenant A
        like_url = reverse('post_like', args=[self.public_tenant_a.id, self.post_a1.id])
        res = self.client.post(like_url)
        self.assertEqual(res.status_code, 302)
        self.assertTrue(Like.objects.filter(post=self.post_a1, user=self.viewer_user).exists())
        self.assertEqual(self.post_a1.likes.count(), 1)

        # Liking again unlikes (toggle)
        res = self.client.post(like_url)
        self.assertEqual(res.status_code, 302)
        self.assertFalse(Like.objects.filter(post=self.post_a1, user=self.viewer_user).exists())
        self.assertEqual(self.post_a1.likes.count(), 0)

        # Cross-tenant like attempt returns 404
        fake_like_url = reverse('post_like', args=[self.public_tenant_a.id, self.post_b1.id])
        res = self.client.post(fake_like_url)
        self.assertEqual(res.status_code, 404)

        # Liking post in private tenant B without membership returns 403
        private_like_url = reverse('post_like', args=[self.private_tenant_b.id, self.post_b1.id])
        res = self.client.post(private_like_url)
        self.assertEqual(res.status_code, 403)

    # 9. Comments System & Permissions
    def test_comment_creation_and_permissions(self):
        self.client.login(username='viewer_user', password='password123')

        # Viewer can comment on post in Tenant A
        comment_url = reverse('post_comment', args=[self.public_tenant_a.id, self.post_a1.id])
        res = self.client.post(comment_url, {'content': 'Great post!'})
        # Comment view redirects to the post detail with #comments anchor
        expected_base = reverse('post_detail', args=[self.public_tenant_a.id, self.post_a1.id])
        self.assertIn(expected_base, res['Location'])
        comment = Comment.objects.filter(post=self.post_a1, author=self.viewer_user).first()
        self.assertIsNotNone(comment)
        self.assertEqual(comment.content, 'Great post!')

        # Cross-tenant comment attempt returns 404
        fake_comment_url = reverse('post_comment', args=[self.public_tenant_a.id, self.post_b1.id])
        res = self.client.post(fake_comment_url, {'content': 'Cross-tenant attempt'})
        self.assertEqual(res.status_code, 404)

        # Viewer can delete their OWN comment
        del_url = reverse('comment_delete', args=[self.public_tenant_a.id, self.post_a1.id, comment.id])
        res = self.client.post(del_url)
        self.assertRedirects(res, reverse('post_detail', args=[self.public_tenant_a.id, self.post_a1.id]))
        self.assertFalse(Comment.objects.filter(id=comment.id).exists())

        # Editor creates comment
        self.client.login(username='editor_user', password='password123')
        self.client.post(comment_url, {'content': 'Editor comment'})
        editor_comment = Comment.objects.get(post=self.post_a1, author=self.editor_user)

        # Viewer CANNOT delete editor's comment (403)
        self.client.login(username='viewer_user', password='password123')
        del_editor_comment_url = reverse('comment_delete', args=[self.public_tenant_a.id, self.post_a1.id, editor_comment.id])
        res = self.client.post(del_editor_comment_url)
        self.assertEqual(res.status_code, 403)
        self.assertTrue(Comment.objects.filter(id=editor_comment.id).exists())

        # Tenant ADMIN CAN delete editor's comment
        self.client.login(username='admin_user', password='password123')
        res = self.client.post(del_editor_comment_url)
        self.assertRedirects(res, reverse('post_detail', args=[self.public_tenant_a.id, self.post_a1.id]))
        self.assertFalse(Comment.objects.filter(id=editor_comment.id).exists())

    # 10. Community Feed Search
    def test_community_feed_search_scoped_to_tenant(self):
        self.client.login(username='viewer_user', password='password123')

        feed_url = reverse('post_list', args=[self.public_tenant_a.id])

        # Search for 'python' -> matches post_a2 only
        res = self.client.get(feed_url, {'q': 'python'})
        self.assertEqual(res.status_code, 200)
        posts_in_context = res.context['posts']
        self.assertEqual(len(posts_in_context), 1)
        self.assertEqual(posts_in_context[0].id, self.post_a2.id)

        # Search for 'Secret' (only in Tenant B) -> returns 0 posts in Tenant A
        res = self.client.get(feed_url, {'q': 'Secret'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.context['posts']), 0)

    # 11. User Profile
    def test_user_profile(self):
        self.client.login(username='admin_user', password='password123')

        # Own profile
        res = self.client.get(reverse('profile'))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['profile_user'], self.admin_user)
        self.assertIn(self.post_a1, res.context['posts'])

        # Viewing another user's profile
        res = self.client.get(reverse('user_profile', args=['other_user']))
        self.assertEqual(res.status_code, 200)
        # Admin is not in Tenant B, so post_b1 (from private tenant B) is NOT leaked
        self.assertNotIn(self.post_b1, res.context['posts'])

    # 12. Explore & Global Keyword Search
    def test_explore_communities_and_search(self):
        self.client.login(username='viewer_user', password='password123')

        # GET explore page
        res = self.client.get(reverse('explore'))
        self.assertEqual(res.status_code, 200)

        # Search for 'sports' keyword -> matches Sports Hub
        res = self.client.get(reverse('explore'), {'q': 'sports'})
        self.assertEqual(res.status_code, 200)
        matched_tenants = [d['tenant'] for d in res.context['tenants_data']]
        self.assertIn(self.sports_tenant, matched_tenants)
        self.assertNotIn(self.public_tenant_a, matched_tenants)

    # 13. Create Community makes Creator ADMIN
    def test_tenant_creation_makes_creator_admin(self):
        self.client.login(username='viewer_user', password='password123')

        res = self.client.post(reverse('tenant_create'), {
            'name': 'Tech Enthusiasts',
            'description': 'Tech community',
            'is_private': 'on',
        })
        new_tenant = Tenant.objects.get(name='Tech Enthusiasts')
        self.assertRedirects(res, reverse('post_list', args=[new_tenant.id]))
        self.assertTrue(new_tenant.is_private)

        # Check membership: viewer_user must be ADMIN of this new tenant
        membership = Membership.objects.get(user=self.viewer_user, tenant=new_tenant)
        self.assertEqual(membership.role, 'ADMIN')

    # 14. Join Community (Public vs Private)
    def test_tenant_join_public_success_and_private_rejected(self):
        self.client.login(username='viewer_user', password='password123')

        # Join public Sports Hub
        join_url = reverse('tenant_join', args=[self.sports_tenant.id])
        res = self.client.post(join_url)
        self.assertRedirects(res, reverse('post_list', args=[self.sports_tenant.id]))
        self.assertTrue(Membership.objects.filter(user=self.viewer_user, tenant=self.sports_tenant, role='VIEWER').exists())

        # Attempt to join private Tenant B directly -> rejected with redirect to explore
        join_private_url = reverse('tenant_join', args=[self.private_tenant_b.id])
        res = self.client.post(join_private_url)
        self.assertRedirects(res, reverse('explore'))
        self.assertFalse(Membership.objects.filter(user=self.viewer_user, tenant=self.private_tenant_b).exists())

    # 15. Crew Chat Posting
    def test_crew_chat_posting_and_tenant_isolation(self):
        self.client.login(username='viewer_user', password='password123')

        # Post to Tenant A crew chat
        chat_url = reverse('tenant_chat_post', args=[self.public_tenant_a.id])
        res = self.client.post(chat_url, {'message': 'Hello team A!'})
        self.assertEqual(res.status_code, 302)
        chat = ChatMessage.objects.filter(tenant=self.public_tenant_a, author=self.viewer_user).first()
        self.assertIsNotNone(chat)
        self.assertEqual(chat.message, 'Hello team A!')

        # Chat in Tenant A is NOT present in Sports Hub
        self.assertFalse(ChatMessage.objects.filter(tenant=self.sports_tenant).exists())

    # 16. Rich Media Posts (Image & Video URL)
    def test_post_with_image_and_video(self):
        self.client.login(username='admin_user', password='password123')

        res = self.client.post(reverse('post', args=[self.public_tenant_a.id]), {
            'title': 'Post with Image and Video',
            'content': 'Check out this video demo and picture.',
            'image_url': 'https://example.com/demo.jpg',
            'video_url': 'https://www.youtube.com/embed/dQw4w9WgXcQ',
        })
        self.assertEqual(res.status_code, 302)
        p = Post.objects.get(title='Post with Image and Video')
        self.assertEqual(p.image_url, 'https://example.com/demo.jpg')
        self.assertEqual(p.video_url, 'https://www.youtube.com/embed/dQw4w9WgXcQ')

    # 17. Admin Member Management (Promote to Editor & Demote to Viewer)
    def test_admin_can_promote_and_demote_editor(self):
        self.client.login(username='admin_user', password='password123')

        # Promote viewer_user to EDITOR
        promote_url = reverse('tenant_member_role_update', args=[self.public_tenant_a.id, self.mem_viewer.id])
        res = self.client.post(promote_url, {'role': 'EDITOR'})
        self.assertRedirects(res, reverse('tenant_members', args=[self.public_tenant_a.id]))
        self.mem_viewer.refresh_from_db()
        self.assertEqual(self.mem_viewer.role, 'EDITOR')

        # Demote back to VIEWER
        res = self.client.post(promote_url, {'role': 'VIEWER'})
        self.assertRedirects(res, reverse('tenant_members', args=[self.public_tenant_a.id]))
        self.mem_viewer.refresh_from_db()
        self.assertEqual(self.mem_viewer.role, 'VIEWER')

    # 18. Transfer Admin Rights
    def test_admin_can_transfer_admin_role(self):
        self.client.login(username='admin_user', password='password123')

        transfer_url = reverse('tenant_member_transfer_admin', args=[self.public_tenant_a.id, self.mem_editor.id])
        res = self.client.post(transfer_url)
        self.assertRedirects(res, reverse('tenant_members', args=[self.public_tenant_a.id]))

        self.mem_editor.refresh_from_db()
        self.mem_admin.refresh_from_db()
        self.assertEqual(self.mem_editor.role, 'ADMIN')
        self.assertEqual(self.mem_admin.role, 'EDITOR')

    # 19. Kick Member Permissions
    def test_admin_can_kick_member_and_editor_cannot(self):
        # Editor cannot kick member
        self.client.login(username='editor_user', password='password123')
        kick_url = reverse('tenant_member_kick', args=[self.public_tenant_a.id, self.mem_viewer.id])
        res = self.client.post(kick_url)
        self.assertRedirects(res, reverse('tenant_members', args=[self.public_tenant_a.id]))
        self.assertTrue(Membership.objects.filter(id=self.mem_viewer.id).exists())

        # Admin CAN kick member
        self.client.login(username='admin_user', password='password123')
        res = self.client.post(kick_url)
        self.assertRedirects(res, reverse('tenant_members', args=[self.public_tenant_a.id]))
        self.assertFalse(Membership.objects.filter(id=self.mem_viewer.id).exists())

    # 20. Mutual Communities on Profile
    def test_mutual_communities_on_profile(self):
        self.client.login(username='admin_user', password='password123')

        # Both admin_user and editor_user are in Tenant A
        res = self.client.get(reverse('user_profile', args=['editor_user']))
        self.assertEqual(res.status_code, 200)
        mutual_memberships = res.context['mutual_memberships']
        self.assertEqual(len(mutual_memberships), 1)
        self.assertEqual(mutual_memberships[0].tenant, self.public_tenant_a)

    # 21. Video Filter Helpers
    def test_video_tags_filters(self):
        # YouTube watch format
        embed_url = youtube_embed_url('https://www.youtube.com/watch?v=dQw4w9WgXcQ')
        self.assertEqual(embed_url, 'https://www.youtube.com/embed/dQw4w9WgXcQ')

        # YouTube short format
        embed_url_short = youtube_embed_url('https://youtu.be/dQw4w9WgXcQ')
        self.assertEqual(embed_url_short, 'https://www.youtube.com/embed/dQw4w9WgXcQ')

        # Direct video files
        self.assertTrue(is_direct_video('https://example.com/demo.mp4'))
        self.assertFalse(is_direct_video('https://example.com/demo.jpg'))
