import re
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.contrib import messages

from memberships.models import Membership
from tenants.models import Tenant, ChatMessage, auto_detect_category
from .models import Post, Like, Comment, CommentLike, Poll, PollOption, PollVote
from .permissions import get_membership, can_create_post, can_edit_post, can_delete_post


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _permission_denied(request, message="You don't have permission to perform this action."):
    """Render a 403 page with a human-readable message."""
    return render(request, 'posts/403.html', {'message': message}, status=403)


def _not_a_member(request, tenant=None):
    """Render the 403 page with a 'not a member' message."""
    return _permission_denied(
        request,
        "You are not a member of this tenant and cannot access this page."
    )


def format_video_metadata(video_url):
    """
    Transforms any video URL into a clean card format.
    For YouTube: extracts video ID, builds thumbnail URL and watch URL.
    For direct videos (.mp4 etc.): keeps is_direct = True.
    """
    if not video_url:
        return {'embed_url': '', 'is_direct': False, 'watch_url': '', 'thumbnail_url': ''}

    url = video_url.strip()
    url_lower = url.lower().split('?')[0]

    # Check direct video
    if url_lower.endswith(('.mp4', '.webm', '.ogg', '.mov')):
        return {'embed_url': url, 'is_direct': True, 'watch_url': url, 'thumbnail_url': ''}

    # Match YouTube video ID
    match = re.search(r'(?:v=|\/v\/|youtu\.be\/|\/embed\/|\/shorts\/)([a-zA-Z0-9_-]{11})', url)
    if match:
        video_id = match.group(1)
        return {
            'embed_url': f"https://www.youtube-nocookie.com/embed/{video_id}?rel=0",
            'is_direct': False,
            'watch_url': f"https://www.youtube.com/watch?v={video_id}",
            'thumbnail_url': f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
        }

    return {'embed_url': url, 'is_direct': False, 'watch_url': url, 'thumbnail_url': ''}


# ---------------------------------------------------------------------------
# Home / Dashboard
# ---------------------------------------------------------------------------

@login_required
def home(request):
    """
    Dashboard: shows all tenants/communities the current user is a member of.
    """
    memberships = (
        Membership.objects
        .filter(user=request.user)
        .select_related('tenant')
        .order_by('tenant__name')
    )
    return render(request, 'posts/home.html', {'memberships': memberships})


# ---------------------------------------------------------------------------
# Community Feed / Post List
# ---------------------------------------------------------------------------

@login_required
def post_list(request, tenant_id):
    """
    Community Feed: List all posts for the given tenant with category filtering,
    search, likes, comments, member stats, and live Crew Chat.
    """
    user = request.user
    tenant = get_object_or_404(Tenant, id=tenant_id)
    membership = get_membership(user, tenant)

    if tenant.is_private and not membership:
        return _permission_denied(
            request,
            "This community is private. You must be an approved member to view its feed and posts."
        )

    # Base query for posts in this tenant
    posts_qs = Post.objects.filter(tenant=tenant).select_related('author')

    # Category Filter (dynamic)
    category_filter = request.GET.get('category', '').strip()
    if category_filter and category_filter.lower() != 'all':
        posts_qs = posts_qs.filter(category__iexact=category_filter)

    # Search scoped to this tenant
    search_query = request.GET.get('q', '').strip()
    if search_query:
        posts_qs = posts_qs.filter(
            Q(title__icontains=search_query) | Q(content__icontains=search_query) | Q(category__icontains=search_query)
        )

    posts_qs = (
        posts_qs
        .annotate(
            like_count=Count('likes', distinct=True),
            comment_count=Count('comments', distinct=True)
        )
        .order_by('-created_at')
    )

    # Set of post IDs liked by current user
    user_liked_post_ids = set(
        Like.objects.filter(post__tenant=tenant, user=user).values_list('post_id', flat=True)
    )

    posts = list(posts_qs)
    for p in posts:
        p.is_liked = p.id in user_liked_post_ids
        vmeta = format_video_metadata(p.video_url)
        p.embed_video_url = vmeta['embed_url']
        p.is_direct_video = vmeta['is_direct']
        p.watch_url = vmeta['watch_url']
        p.thumbnail_url = vmeta['thumbnail_url']

    # Dynamic distinct categories in this community
    all_categories = list(
        Post.objects.filter(tenant=tenant).exclude(category='').values_list('category', flat=True).distinct().order_by('category')
    )

    # Community metadata
    member_count = tenant.membership_set.count()
    admin_membership = Membership.objects.filter(tenant=tenant, role='ADMIN').select_related('user').first()
    admin_user = admin_membership.user if admin_membership else None

    # Crew Chat Messages
    chat_messages = tenant.chat_messages.select_related('author').all().order_by('created_at')

    return render(request, 'posts/post_list.html', {
        'tenant': tenant,
        'posts': posts,
        'membership': membership,
        'search_query': search_query,
        'category_filter': category_filter,
        'categories': all_categories,
        'member_count': member_count,
        'admin_user': admin_user,
        'chat_messages': chat_messages,
    })


# ---------------------------------------------------------------------------
# Post CRUD
# ---------------------------------------------------------------------------

@login_required
def post(request, tenant_id):
    """
    Create a new post with category, optional image, video, and optional Poll.
    Auto-detects category from title and content if not explicitly specified.
    """
    user = request.user
    tenant = get_object_or_404(Tenant, id=tenant_id)
    membership = get_membership(user, tenant)

    if not membership:
        return _not_a_member(request, tenant)

    if not can_create_post(membership):
        return _permission_denied(request, "Only ADMINs and EDITORs can create posts.")

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        custom_category = request.POST.get('custom_category', '').strip()
        category_choice = request.POST.get('category', '').strip()
        image_url = request.POST.get('image_url', '').strip()
        video_url = request.POST.get('video_url', '').strip()

        # Poll fields (optional)
        poll_question = request.POST.get('poll_question', '').strip()
        poll_options = [
            request.POST.get(f'poll_option_{i}', '').strip()
            for i in range(1, 5)
            if request.POST.get(f'poll_option_{i}', '').strip()
        ]

        if not title or not content:
            return render(request, 'posts/post_create.html', {
                'tenant': tenant,
                'membership': membership,
                'error': 'Both title and content are required.',
                'form_title': title,
                'form_content': content,
                'form_category': category_choice,
                'form_custom_category': custom_category,
                'form_image_url': image_url,
                'form_video_url': video_url,
                'form_poll_question': poll_question,
            })

        # Category resolution
        if custom_category:
            final_category = custom_category
        elif category_choice and category_choice != 'AUTO':
            final_category = category_choice
        else:
            final_category = auto_detect_category(title, content)

        new_post = Post.objects.create(
            author=user,
            tenant=tenant,
            title=title,
            content=content,
            category=final_category,
            image_url=image_url,
            video_url=video_url
        )

        # Create Poll if question and at least 2 options provided
        if poll_question and len(poll_options) >= 2:
            new_poll = Poll.objects.create(post=new_post, question=poll_question)
            for opt_text in poll_options:
                PollOption.objects.create(poll=new_poll, text=opt_text)

        messages.success(request, f"Post published in [{final_category}] successfully!")
        return redirect('post_list', tenant_id=tenant_id)

    # GET: fetch dynamic categories for suggestions
    existing_categories = list(
        Post.objects.filter(tenant=tenant).exclude(category='').values_list('category', flat=True).distinct().order_by('category')
    )

    return render(request, 'posts/post_create.html', {
        'tenant': tenant,
        'membership': membership,
        'existing_categories': existing_categories,
    })


@login_required
def post_detail(request, tenant_id, post_id):
    """
    Display full post details with media, poll, nested comments, and comment likes.
    """
    user = request.user
    tenant = get_object_or_404(Tenant, id=tenant_id)
    membership = get_membership(user, tenant)

    if tenant.is_private and not membership:
        return _permission_denied(
            request,
            "This tenant is private. You must be a member to view its posts."
        )

    post = get_object_or_404(
        Post.objects.select_related('author', 'tenant'),
        id=post_id,
        tenant=tenant
    )

    # Video metadata
    vmeta = format_video_metadata(post.video_url)
    post.embed_video_url = vmeta['embed_url']
    post.is_direct_video = vmeta['is_direct']
    post.watch_url = vmeta['watch_url']
    post.thumbnail_url = vmeta['thumbnail_url']

    # Post Likes
    like_count = post.likes.count()
    is_liked = post.likes.filter(user=user).exists()

    # Poll processing
    poll_data = None
    if hasattr(post, 'poll'):
        poll = post.poll
        total_votes = poll.votes.count()
        user_vote = poll.votes.filter(user=user).first()
        user_voted_option_id = user_vote.option_id if user_vote else None

        options_data = []
        for opt in poll.options.all():
            opt_vote_count = opt.votes.count()
            percentage = round((opt_vote_count / total_votes * 100), 1) if total_votes > 0 else 0
            options_data.append({
                'id': opt.id,
                'text': opt.text,
                'vote_count': opt_vote_count,
                'percentage': percentage,
                'is_user_choice': opt.id == user_voted_option_id,
            })

        poll_data = {
            'poll': poll,
            'total_votes': total_votes,
            'has_voted': user_vote is not None,
            'options': options_data,
        }

    # Top-level comments with replies and comment likes
    user_liked_comment_ids = set(
        CommentLike.objects.filter(comment__post=post, user=user).values_list('comment_id', flat=True)
    )

    top_comments = (
        post.comments
        .filter(parent__isnull=True)
        .select_related('author')
        .prefetch_related('replies__author', 'replies__likes', 'likes')
        .order_by('created_at')
    )

    comments_list = []
    total_comments_count = post.comments.count()

    for c in top_comments:
        c.is_liked = c.id in user_liked_comment_ids
        c.likes_count = c.likes.count()
        replies = list(c.replies.all())
        for r in replies:
            r.is_liked = r.id in user_liked_comment_ids
            r.likes_count = r.likes.count()
        c.threaded_replies = replies
        comments_list.append(c)

    return render(request, 'posts/post.html', {
        'post': post,
        'tenant': tenant,
        'membership': membership,
        'comments': comments_list,
        'total_comments_count': total_comments_count,
        'like_count': like_count,
        'is_liked': is_liked,
        'poll_data': poll_data,
    })


@login_required
def post_edit(request, tenant_id, post_id):
    """
    Edit an existing post.
    """
    user = request.user
    tenant = get_object_or_404(Tenant, id=tenant_id)
    membership = get_membership(user, tenant)

    if not membership:
        return _not_a_member(request, tenant)

    post = get_object_or_404(Post, id=post_id, tenant=tenant)

    if not can_edit_post(membership):
        return _permission_denied(request, "Only ADMINs and EDITORs can edit posts.")

    existing_categories = list(
        Post.objects.filter(tenant=tenant).exclude(category='').values_list('category', flat=True).distinct().order_by('category')
    )

    if request.method == 'POST':
        new_title = request.POST.get('title', '').strip()
        new_content = request.POST.get('content', '').strip()
        custom_category = request.POST.get('custom_category', '').strip()
        new_image_url = request.POST.get('image_url', '').strip()
        new_video_url = request.POST.get('video_url', '').strip()

        if not new_title or not new_content:
            return render(request, 'posts/post_edit.html', {
                'post': post,
                'tenant': tenant,
                'membership': membership,
                'existing_categories': existing_categories,
                'error': 'Both title and content are required.',
            })

        final_category = custom_category if custom_category else auto_detect_category(new_title, new_content)

        post.title = new_title
        post.content = new_content
        post.category = final_category
        post.image_url = new_image_url
        post.video_url = new_video_url
        post.save()

        messages.success(request, "Post updated successfully!")
        return redirect('post_detail', tenant_id=tenant_id, post_id=post_id)

    # GET
    return render(request, 'posts/post_edit.html', {
        'post': post,
        'tenant': tenant,
        'membership': membership,
        'existing_categories': existing_categories,
    })


@login_required
def post_delete(request, tenant_id, post_id):
    """
    Delete a post (ADMIN role only).
    """
    user = request.user
    tenant = get_object_or_404(Tenant, id=tenant_id)
    membership = get_membership(user, tenant)

    if not membership:
        return _not_a_member(request, tenant)

    post = get_object_or_404(Post, id=post_id, tenant=tenant)

    if not can_delete_post(membership):
        return _permission_denied(request, "Only ADMINs can delete posts.")

    if request.method == 'POST':
        post.delete()
        messages.success(request, "Post deleted successfully.")
        return redirect('post_list', tenant_id=tenant_id)

    # GET
    return render(request, 'posts/post_delete.html', {
        'post': post,
        'tenant': tenant,
        'membership': membership,
    })


# ---------------------------------------------------------------------------
# Likes
# ---------------------------------------------------------------------------

@login_required
def post_like(request, tenant_id, post_id):
    """
    Toggle like/unlike for a post.
    """
    if request.method != 'POST':
        return redirect('post_detail', tenant_id=tenant_id, post_id=post_id)

    user = request.user
    tenant = get_object_or_404(Tenant, id=tenant_id)
    membership = get_membership(user, tenant)

    if tenant.is_private and not membership:
        return _permission_denied(
            request,
            "This tenant is private. You must be a member to like its posts."
        )

    post = get_object_or_404(Post, id=post_id, tenant=tenant)

    like = Like.objects.filter(post=post, user=user).first()
    if like:
        like.delete()
    else:
        Like.objects.create(post=post, user=user)

    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
    if next_url:
        return redirect(next_url)
    return redirect('post_detail', tenant_id=tenant_id, post_id=post_id)


# ---------------------------------------------------------------------------
# Comments & Replies
# ---------------------------------------------------------------------------

@login_required
def post_comment(request, tenant_id, post_id):
    """
    Add a top-level comment or nested reply to a post.
    """
    if request.method != 'POST':
        return redirect('post_detail', tenant_id=tenant_id, post_id=post_id)

    user = request.user
    tenant = get_object_or_404(Tenant, id=tenant_id)
    membership = get_membership(user, tenant)

    if tenant.is_private and not membership:
        return _permission_denied(
            request,
            "This tenant is private. You must be a member to comment."
        )

    post = get_object_or_404(Post, id=post_id, tenant=tenant)
    content = request.POST.get('content', '').strip()
    parent_id = request.POST.get('parent_id', '').strip()

    parent_comment = None
    if parent_id:
        parent_comment = get_object_or_404(Comment, id=parent_id, post=post)

    if content:
        Comment.objects.create(
            post=post,
            author=user,
            content=content,
            parent=parent_comment
        )
        if parent_comment:
            messages.success(request, f"Reply posted to {parent_comment.author.username}.")
        else:
            messages.success(request, "Comment posted.")
    else:
        messages.error(request, "Comment cannot be empty.")

    return redirect(f"/posts/{tenant.id}/{post.id}/#comments")


@login_required
def comment_like(request, tenant_id, post_id, comment_id):
    """
    Toggle like on a comment.
    """
    if request.method != 'POST':
        return redirect('post_detail', tenant_id=tenant_id, post_id=post_id)

    user = request.user
    tenant = get_object_or_404(Tenant, id=tenant_id)
    membership = get_membership(user, tenant)

    if tenant.is_private and not membership:
        return _permission_denied(request, "Cannot like comments in private community without membership.")

    post = get_object_or_404(Post, id=post_id, tenant=tenant)
    comment = get_object_or_404(Comment, id=comment_id, post=post)

    clike = CommentLike.objects.filter(comment=comment, user=user).first()
    if clike:
        clike.delete()
    else:
        CommentLike.objects.create(comment=comment, user=user)

    return redirect(f"/posts/{tenant.id}/{post.id}/#comment-{comment.id}")


@login_required
def comment_delete(request, tenant_id, post_id, comment_id):
    """
    Delete a comment. Allowed for author OR tenant ADMIN.
    """
    if request.method != 'POST':
        return redirect('post_detail', tenant_id=tenant_id, post_id=post_id)

    user = request.user
    tenant = get_object_or_404(Tenant, id=tenant_id)
    membership = get_membership(user, tenant)

    post = get_object_or_404(Post, id=post_id, tenant=tenant)
    comment = get_object_or_404(Comment, id=comment_id, post=post)

    is_author = comment.author == user
    is_tenant_admin = membership and membership.role == 'ADMIN'

    if not (is_author or is_tenant_admin):
        return _permission_denied(
            request,
            "You can only delete your own comments unless you are a tenant Admin."
        )

    comment.delete()
    messages.success(request, "Comment deleted.")
    return redirect('post_detail', tenant_id=tenant_id, post_id=post_id)


# ---------------------------------------------------------------------------
# Poll Voting
# ---------------------------------------------------------------------------

@login_required
def poll_vote(request, tenant_id, post_id, poll_id):
    """
    Submit vote for a poll option.
    Allows only 1 vote per user.
    """
    if request.method != 'POST':
        return redirect('post_detail', tenant_id=tenant_id, post_id=post_id)

    user = request.user
    tenant = get_object_or_404(Tenant, id=tenant_id)
    membership = get_membership(user, tenant)

    if tenant.is_private and not membership:
        return _permission_denied(request, "Cannot vote in a private community without membership.")

    post = get_object_or_404(Post, id=post_id, tenant=tenant)
    poll = get_object_or_404(Poll, id=poll_id, post=post)

    option_id = request.POST.get('option_id')
    if not option_id:
        messages.error(request, "Please select an option before voting.")
        return redirect('post_detail', tenant_id=tenant_id, post_id=post_id)

    option = get_object_or_404(PollOption, id=option_id, poll=poll)

    # Check if already voted
    existing_vote = PollVote.objects.filter(poll=poll, user=user).first()
    if existing_vote:
        existing_vote.option = option
        existing_vote.save()
        messages.success(request, f"Your vote has been updated to '{option.text}'.")
    else:
        PollVote.objects.create(poll=poll, option=option, user=user)
        messages.success(request, f"You voted for '{option.text}'. Thank you for participating!")

    return redirect(f"/posts/{tenant.id}/{post.id}/#poll")