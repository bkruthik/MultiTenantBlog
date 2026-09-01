from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from tenants.models import Tenant, ChatMessage
from memberships.models import Membership
from posts.models import Post, Like, Comment, CommentLike, Poll, PollOption, PollVote
import random


class Command(BaseCommand):
    help = "Expanded seed: categorized communities with avatars, 4-5 posts each, polls, nested replies, comment likes."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding expanded community data..."))

        # 1. Admin
        admin_user, _ = User.objects.get_or_create(
            username='admin',
            defaults={'email': 'admin@example.com', 'is_staff': True, 'is_superuser': True}
        )
        admin_user.set_password('AdminPass123!@#')
        admin_user.save()

        # 2. 50 Users
        names = [
            'paul', 'alex', 'sarah', 'david', 'emily', 'michael', 'elena', 'liam', 'maya',
            'noah', 'olivia', 'aravind', 'ananya', 'marcus', 'sophia', 'james', 'chloe',
            'ethan', 'priya', 'lucas', 'mia', 'rahul', 'isabella', 'benjamin', 'ava',
            'samuel', 'grace', 'rohan', 'hannah', 'daniel', 'lily', 'vikram', 'zoe',
            'gabriel', 'leila', 'ryan', 'clara', 'dev', 'nora', 'julian', 'stella',
            'aditya', 'eva', 'leo', 'victoria', 'kavya', 'hazel', 'aiden', 'aurora',
            'neil', 'penelope'
        ]
        sample_avatars = [
            'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80',
            'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80',
            'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=150&auto=format&fit=crop&q=80',
            'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150&auto=format&fit=crop&q=80',
            'https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=150&auto=format&fit=crop&q=80',
            'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=150&auto=format&fit=crop&q=80',
            'https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=150&auto=format&fit=crop&q=80',
            'https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?w=150&auto=format&fit=crop&q=80',
        ]

        users = [admin_user]
        # Admin avatar
        if hasattr(admin_user, 'profile'):
            admin_user.profile.avatar_url = 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150&auto=format&fit=crop&q=80'
            admin_user.profile.bio = 'Platform Administrator & Multi-Tenant Architect'
            admin_user.profile.save()

        for idx, name in enumerate(names):
            u, created = User.objects.get_or_create(username=name, defaults={'email': f"{name}@example.com"})
            if created:
                u.set_password('StudyPass123!@#')
                u.save()
            if hasattr(u, 'profile'):
                u.profile.avatar_url = sample_avatars[idx % len(sample_avatars)]
                u.profile.bio = f"Developer and enthusiastic community member | @{name}"
                u.profile.save()
            users.append(u)

        self.stdout.write(self.style.SUCCESS(f"Verified {len(users)} accounts with Instagram-style profile photos."))

        # 3. Communities with avatars
        communities_config = [
            {
                'slug': 'full-stack-web-dev',
                'name': 'Full-Stack Web Developers',
                'description': 'Master Django, React, Tailwind CSS, API design, database optimization, and modern web architectures.',
                'category': 'TECH', 'is_private': False,
                'avatar_emoji': '💻', 'avatar_url': '',
            },
            {
                'slug': 'data-science-ai-lab',
                'name': 'AI & Machine Learning Lab',
                'description': 'Deep learning research, PyTorch models, computer vision, NLP, and LLM fine-tuning.',
                'category': 'TECH', 'is_private': False,
                'avatar_emoji': '🤖', 'avatar_url': '',
            },
            {
                'slug': 'university-study-circle',
                'name': 'College Study & Exam Hub',
                'description': 'Collaborative study notes, semester exam prep, past paper reviews, and group sessions.',
                'category': 'STUDY', 'is_private': False,
                'avatar_emoji': '📚', 'avatar_url': '',
            },
            {
                'slug': 'sports-fitness-league',
                'name': 'Sports & Athlete Fitness Club',
                'description': 'Marathon training, football tactics, strength workouts, sports nutrition, and match discussions.',
                'category': 'SPORTS', 'is_private': False,
                'avatar_emoji': '⚽', 'avatar_url': '',
            },
            {
                'slug': 'tech-humor-memes',
                'name': 'Dev Humor & Meme Lounge',
                'description': 'Daily programmer humor, code review memes, deployment fails, and developer jokes.',
                'category': 'FUNNY', 'is_private': False,
                'avatar_emoji': '😂', 'avatar_url': '',
            },
            {
                'slug': 'competitive-coding-league',
                'name': 'Competitive Coding League',
                'description': 'Advanced DP, graph theory, LeetCode Hard problems, and algorithmic optimization.',
                'category': 'STUDY', 'is_private': True,
                'avatar_emoji': '🏆', 'avatar_url': '',
            }
        ]

        communities = []
        for cconf in communities_config:
            t, _ = Tenant.objects.get_or_create(slug=cconf['slug'], defaults={
                'name': cconf['name'], 'description': cconf['description'],
                'category': cconf['category'], 'is_private': cconf['is_private'],
                'avatar_emoji': cconf['avatar_emoji'], 'avatar_url': cconf['avatar_url'],
            })
            t.category = cconf['category']
            t.avatar_emoji = cconf['avatar_emoji']
            t.save()
            communities.append(t)

        self.stdout.write(self.style.SUCCESS(f"Created/verified {len(communities)} communities."))

        # 4. Memberships
        for c in communities:
            Membership.objects.get_or_create(user=admin_user, tenant=c, defaults={'role': 'ADMIN'})

        for i, comm in enumerate(communities[:5]):
            for u in users[1 + i*2: 3 + i*2]:
                Membership.objects.get_or_create(user=u, tenant=comm, defaults={'role': 'EDITOR'})
            for u in users[10:35]:
                Membership.objects.get_or_create(user=u, tenant=comm, defaults={'role': 'VIEWER'})

        for u in users[1:15]:
            Membership.objects.get_or_create(user=u, tenant=communities[5], defaults={'role': 'VIEWER'})

        # 5. Rich Posts — 4-5 per community
        all_posts_data = [
            # ─── Community 0: Full-Stack Web Developers ───
            {
                'tenant': communities[0], 'author': admin_user, 'category': 'TECH',
                'title': 'Building Scalable Multi-Tenant Applications with Django & PostgreSQL',
                'content': "Multi-tenancy allows one app to serve hundreds of orgs with strict data isolation.\n\nKey pillars:\n1. Scoped ORM: every query filtered by tenant_id\n2. RBAC: View / Create / Edit / Delete role enforcement\n3. Connection pooling (CONN_MAX_AGE=60) for 1000+ concurrent users",
                'image_url': 'https://images.unsplash.com/photo-1555066931-4365d14bab8c?w=1000&auto=format&fit=crop&q=80',
                'video_url': 'https://www.youtube.com/watch?v=rHux0gMZ3Eg',
                'poll': {'question': 'Which backend framework do you use?', 'options': ['Django / DRF', 'FastAPI', 'Flask', 'Node / Express']},
            },
            {
                'tenant': communities[0], 'author': users[1], 'category': 'TECH',
                'title': 'Mastering Tailwind CSS: Build Stunning UI Without Writing Custom CSS',
                'content': "Tailwind CSS is a utility-first framework that lets you build complex UIs by composing small, single-purpose classes directly in HTML.\n\nKey tips:\n- Use @apply to group repeated utility combinations into components.\n- Leverage JIT mode for instant on-demand CSS generation.\n- Pair with shadcn/ui or Headless UI for accessible components.",
                'image_url': 'https://images.unsplash.com/photo-1587620962725-abab7fe55159?w=1000&auto=format&fit=crop&q=80',
                'video_url': 'https://www.youtube.com/watch?v=mr15Xzb1Ook',
                'poll': {'question': 'Preferred CSS approach?', 'options': ['Tailwind CSS', 'CSS Modules', 'Styled Components', 'Plain CSS']},
            },
            {
                'tenant': communities[0], 'author': users[2], 'category': 'TECH',
                'title': 'REST API Design Best Practices Every Developer Should Know',
                'content': "Good REST API design makes your application maintainable, scalable, and a pleasure to integrate with.\n\n1. Use nouns not verbs: /users not /getUsers\n2. Version your API: /api/v1/users\n3. Use proper HTTP methods: GET, POST, PUT/PATCH, DELETE\n4. Return consistent JSON error shapes\n5. Paginate large collections",
                'image_url': 'https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=1000&auto=format&fit=crop&q=80',
                'video_url': '',
                'poll': None,
            },
            {
                'tenant': communities[0], 'author': users[10], 'category': 'TECH',
                'title': 'PostgreSQL Performance Tips: Indexes, EXPLAIN ANALYZE & Query Optimization',
                'content': "Slow queries can kill your application under real load. Here's how to diagnose and fix them.\n\n- Use EXPLAIN ANALYZE to see the query plan and actual rows.\n- Add B-tree indexes on frequently filtered columns.\n- Use PARTIAL indexes for filtered queries (e.g., WHERE status='active').\n- Avoid N+1 queries — use select_related() or prefetch_related() in Django ORM.",
                'image_url': 'https://images.unsplash.com/photo-1544383835-bda2bc66a55d?w=1000&auto=format&fit=crop&q=80',
                'video_url': '',
                'poll': None,
            },

            # ─── Community 1: AI & Machine Learning Lab ───
            {
                'tenant': communities[1], 'author': admin_user, 'category': 'TECH',
                'title': 'Getting Started with Deep Learning & Neural Networks in PyTorch',
                'content': "PyTorch is the premier library for deep learning research and production AI.\n\nKey concepts:\n- Tensors and Automatic Differentiation (torch.autograd)\n- Building neural net layers with torch.nn.Module\n- Loss functions & Optimizers (torch.optim.AdamW)\n- Training loops with validation evaluation",
                'image_url': 'https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=1000&auto=format&fit=crop&q=80',
                'video_url': 'https://www.youtube.com/watch?v=V_xro1bcAuA',
                'poll': {'question': 'Your primary AI/ML focus?', 'options': ['Large Language Models', 'Computer Vision', 'Reinforcement Learning', 'Speech & Audio']},
            },
            {
                'tenant': communities[1], 'author': users[4], 'category': 'TECH',
                'title': 'Fine-Tuning LLMs with LoRA & PEFT: A Practical Guide',
                'content': "LoRA (Low-Rank Adaptation) lets you fine-tune massive language models on a single GPU by adding small adapter layers.\n\nSteps:\n1. Load base model (e.g. LLaMA-3 or Mistral)\n2. Apply PEFT / LoRA config\n3. Train on your domain dataset\n4. Merge adapters back for inference",
                'image_url': 'https://images.unsplash.com/photo-1677442135703-1787eea5ce01?w=1000&auto=format&fit=crop&q=80',
                'video_url': '',
                'poll': {'question': 'Favorite LLM for fine-tuning?', 'options': ['LLaMA 3 / Meta AI', 'Mistral 7B', 'Gemma / Google', 'Phi-3 / Microsoft']},
            },
            {
                'tenant': communities[1], 'author': users[5], 'category': 'TECH',
                'title': 'Computer Vision with YOLO v8: Real-Time Object Detection Tutorial',
                'content': "YOLO (You Only Look Once) is the gold standard for real-time object detection.\n\nYOLO v8 improvements:\n- Anchor-free detection for better small object performance\n- Improved backbone (CSPNet)\n- Native support for segmentation and pose estimation\n- Ultralytics ecosystem for training and deployment",
                'image_url': 'https://images.unsplash.com/photo-1635070041078-e363dbe005cb?w=1000&auto=format&fit=crop&q=80',
                'video_url': 'https://www.youtube.com/watch?v=5ku7npMjW0I',
                'poll': None,
            },

            # ─── Community 2: College Study & Exam Hub ───
            {
                'tenant': communities[2], 'author': users[2], 'category': 'STUDY',
                'title': 'How to Structure Effective Group Study Sessions Before Finals',
                'content': "Group study doubles retention if structured well.\n\nTips:\n1. Set a concrete agenda for each 45-minute block.\n2. Teach each concept to your partner without notes.\n3. Solve past exam questions under timed conditions.\n4. End with a 10-minute doubt-clearing session.",
                'image_url': 'https://images.unsplash.com/photo-1434030216411-0b793f4b4173?w=1000&auto=format&fit=crop&q=80',
                'video_url': '',
                'poll': {'question': 'Best study technique?', 'options': ['Active Recall & Flashcards', 'Pomodoro 25/5', 'Mind Mapping', 'Teaching Peers']},
            },
            {
                'tenant': communities[2], 'author': users[11], 'category': 'STUDY',
                'title': 'Top 10 Free Resources to Learn Data Structures & Algorithms',
                'content': "DSA is the most-asked topic in coding interviews. Here are the best free resources:\n\n1. NeetCode.io — structured roadmap with YouTube explanations\n2. CS50 on edX — Harvard's intro to CS\n3. GeeksForGeeks DSA Self-Paced\n4. CLRS (Introduction to Algorithms) — for deep theory\n5. Visualgo.net — animated visualizations",
                'image_url': 'https://images.unsplash.com/photo-1509228468518-180dd4864904?w=1000&auto=format&fit=crop&q=80',
                'video_url': 'https://www.youtube.com/watch?v=pkYVOmU3MgA',
                'poll': {'question': 'Favorite DSA platform?', 'options': ['LeetCode', 'Codeforces', 'HackerRank', 'GeeksForGeeks']},
            },
            {
                'tenant': communities[2], 'author': users[12], 'category': 'STUDY',
                'title': 'Mathematics for Machine Learning — What You Actually Need',
                'content': "You don't need a PhD in math to do ML, but you need these foundations:\n\n- Linear Algebra: matrices, dot products, eigendecomposition\n- Calculus: derivatives, chain rule, gradient descent\n- Probability & Statistics: Bayes theorem, distributions, MLE\n- Optimization: SGD, Adam, learning rate schedules",
                'image_url': 'https://images.unsplash.com/photo-1635070041078-e363dbe005cb?w=1000&auto=format&fit=crop&q=80',
                'video_url': '',
                'poll': None,
            },

            # ─── Community 3: Sports & Fitness ───
            {
                'tenant': communities[3], 'author': users[6], 'category': 'SPORTS',
                'title': 'HIIT Training for Cardiovascular Endurance: A 20-Minute Protocol',
                'content': "HIIT maximizes caloric burn and VO2 max in minimal time.\n\nSample 20-minute HIIT:\n- 30s Sprint or Burpees\n- 30s Active Recovery walk\n- Repeat x10 rounds\n- 5 min dynamic cool-down stretch",
                'image_url': 'https://images.unsplash.com/photo-1517838277536-f5f99be501cd?w=1000&auto=format&fit=crop&q=80',
                'video_url': '',
                'poll': {'question': 'Favorite workout style?', 'options': ['HIIT / Cardio', 'Weight Training', 'Yoga / Flexibility', 'Team Sports']},
            },
            {
                'tenant': communities[3], 'author': users[7], 'category': 'SPORTS',
                'title': 'Football Tactics 101: Understanding the 4-3-3 Formation',
                'content': "The 4-3-3 is used by Barcelona, Manchester City, and most elite clubs.\n\nKey principles:\n- Wide forwards create width and isolate full-backs\n- A box-to-box midfielder (CM) drives transitions\n- High defensive line requires fast center-backs\n- Positional play (juego de posicion) is the foundation",
                'image_url': 'https://images.unsplash.com/photo-1431324155629-1a6deb1dec8d?w=1000&auto=format&fit=crop&q=80',
                'video_url': '',
                'poll': None,
            },
            {
                'tenant': communities[3], 'author': users[14], 'category': 'SPORTS',
                'title': 'Sports Nutrition: What to Eat Before, During and After Training',
                'content': "Nutrition is 70% of athletic performance. Here's the breakdown:\n\n🍌 PRE-WORKOUT (1-2h before):\n- Complex carbs: oats, sweet potato, banana\n- Moderate protein: Greek yogurt, eggs\n\n⚡ INTRA-WORKOUT:\n- Hydration + electrolytes\n- Simple carbs if session > 90 min\n\n🍗 POST-WORKOUT (within 30min):\n- 30-40g fast protein (whey, chicken)\n- High GI carbs to replenish glycogen",
                'image_url': 'https://images.unsplash.com/photo-1490645935967-10de6ba17061?w=1000&auto=format&fit=crop&q=80',
                'video_url': '',
                'poll': None,
            },

            # ─── Community 4: Dev Humor & Memes ───
            {
                'tenant': communities[4], 'author': users[8], 'category': 'FUNNY',
                'title': 'When production goes down on a Friday at 5:00 PM 🔥',
                'content': "\"It works on my machine\" — Famous last words before pushing to master without unit tests.\n\nNot even hotfix branches can save you now. The on-call alert is already pinging and the Slack channel is on fire.",
                'image_url': 'https://images.unsplash.com/photo-1531482615713-2afd69097998?w=1000&auto=format&fit=crop&q=80',
                'video_url': '',
                'poll': {'question': 'Have you ever broken prod on a Friday?', 'options': ['Yes and it was chaotic 😅', 'Almost — caught it in staging 😅', 'Never (100% test coverage 😤)', 'I AM the on-call engineer 😭']},
            },
            {
                'tenant': communities[4], 'author': users[9], 'category': 'FUNNY',
                'title': 'Types of Developers You Meet at Every Code Review 😂',
                'content': "Every engineering team has these characters:\n\n🔴 The Nitpicker: \"This variable name could be more descriptive.\"\n🟡 The Silent Approver: Approves everything without reading.\n🟢 The Philosopher: \"But have we considered the architectural implications?\"\n🔵 The Copy-Paster: \"I found this on Stack Overflow, it should work.\"\n⚫ The One Who Fixed it 3 Years Ago: \"We had this issue before...\"",
                'image_url': 'https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=1000&auto=format&fit=crop&q=80',
                'video_url': '',
                'poll': {'question': 'Which developer type are YOU?', 'options': ['The Nitpicker', 'The Silent Approver', 'The Philosopher', 'The Stack Overflow Hero']},
            },
            {
                'tenant': communities[4], 'author': admin_user, 'category': 'FUNNY',
                'title': '10 Signs You\'ve Been Coding Too Long 😴',
                'content': "1. You dream in Python syntax errors.\n2. You name your pets after data structures (Hash, Queue, Stack).\n3. You tried to Ctrl+Z real life.\n4. Your coffee mug says \"git stash pop\".\n5. You debug conversations by adding print statements.\n6. Everything is either a feature or a bug.\n7. You version-control your grocery list.\n8. You auto-complete sentences in your head.\n9. \"Have you tried turning it off and on again?\" is your answer to everything.\n10. You're reading a list numbered 10 looking for the off-by-one error.",
                'image_url': 'https://images.unsplash.com/photo-1555099962-4199c345e5dd?w=1000&auto=format&fit=crop&q=80',
                'video_url': '',
                'poll': None,
            },

            # ─── Community 5: Competitive Coding (private) ───
            {
                'tenant': communities[5], 'author': admin_user, 'category': 'STUDY',
                'title': 'Weekly Challenge: Dynamic Programming & 0-1 Knapsack Optimizations',
                'content': "This week: 0/1 Knapsack and Unbounded Knapsack DP variations.\n\nFocus on space optimization from O(N*W) down to O(W) using 1D rolling arrays.\n\nPost your solutions and time complexities in comments!",
                'image_url': 'https://images.unsplash.com/photo-1509228468518-180dd4864904?w=1000&auto=format&fit=crop&q=80',
                'video_url': '',
                'poll': None,
            },
            {
                'tenant': communities[5], 'author': users[1], 'category': 'STUDY',
                'title': 'Graph Algorithms Deep Dive: Dijkstra, Bellman-Ford & Floyd-Warshall',
                'content': "Shortest path algorithms are a staple of competitive programming.\n\nDijkstra: O((V+E) log V) — greedy, no negative weights\nBellman-Ford: O(VE) — handles negative edges, detects cycles\nFloyd-Warshall: O(V³) — all-pairs shortest path, small graphs\n\nKey tip: Use priority queues (min-heaps) for Dijkstra in Python with heapq.",
                'image_url': '',
                'video_url': '',
                'poll': {'question': 'Which graph algorithm trips you up most?', 'options': ['Dijkstra', 'Bellman-Ford', 'Floyd-Warshall', 'Topological Sort']},
            },
        ]

        created_posts = []
        for pdata in all_posts_data:
            post, _ = Post.objects.get_or_create(
                tenant=pdata['tenant'],
                title=pdata['title'],
                defaults={
                    'author': pdata['author'],
                    'content': pdata['content'],
                    'category': pdata['category'],
                    'image_url': pdata.get('image_url', ''),
                    'video_url': pdata.get('video_url', ''),
                }
            )
            post.category = pdata['category']
            post.save()
            created_posts.append(post)

            # Create Poll
            if pdata.get('poll'):
                poll_info = pdata['poll']
                poll, _ = Poll.objects.get_or_create(post=post, defaults={'question': poll_info['question']})
                options_objs = []
                for opt_text in poll_info['options']:
                    opt, _ = PollOption.objects.get_or_create(poll=poll, text=opt_text)
                    options_objs.append(opt)

                # Seed poll votes
                voters = random.sample(users[1:30], k=random.randint(10, 20))
                for voter in voters:
                    chosen = random.choice(options_objs)
                    PollVote.objects.get_or_create(poll=poll, user=voter, defaults={'option': chosen})

        self.stdout.write(self.style.SUCCESS(f"Created {len(created_posts)} posts across all communities."))

        # 6. Likes
        for p in created_posts:
            likers = random.sample(users[1:40], k=random.randint(5, 18))
            for liker in likers:
                Like.objects.get_or_create(post=p, user=liker)

        # 7. Comments & Nested Replies with Likes
        comments_pool = [
            "This is exactly what I needed — great writeup!",
            "Super clean explanation, bookmarking this for my team.",
            "I ran into this exact issue last week, wish I had this earlier.",
            "Can you share a GitHub repo? Would love to see the full implementation.",
            "The step-by-step breakdown makes this really accessible for beginners.",
            "Tried this approach in my project — works perfectly!",
            "Great post! What's your recommendation for handling edge cases here?",
        ]
        replies_pool = [
            "Totally agree with this point!",
            "This worked for me too — thanks for sharing!",
            "Great question — I found using indexes helped a lot here.",
            "You're right, should have mentioned that in the post!",
            "Good catch, will update the post with that detail.",
        ]

        for p in created_posts:
            commenters = random.sample(users[1:25], k=random.randint(3, 6))
            for commenter in commenters:
                parent_comment = Comment.objects.create(
                    post=p, author=commenter, content=random.choice(comments_pool)
                )
                # Like the comment
                c_likers = random.sample(users[1:30], k=random.randint(2, 8))
                for cl in c_likers:
                    CommentLike.objects.get_or_create(comment=parent_comment, user=cl)

                # Nested reply
                replier = random.choice(users[1:25])
                if replier != commenter:
                    reply = Comment.objects.create(
                        post=p, author=replier, parent=parent_comment,
                        content=random.choice(replies_pool)
                    )
                    CommentLike.objects.get_or_create(comment=reply, user=commenter)

        # 8. Crew Chat
        crew_msgs = [
            (communities[0], users[1], "Hey everyone! Welcome to Full-Stack Web Developers 💻"),
            (communities[0], users[2], "Who else is working with Django + React? Let's connect!"),
            (communities[0], admin_user, "Welcome crew! Check out the new interactive polls on each post."),
            (communities[1], users[4], "Welcome to the AI & Machine Learning Lab 🤖"),
            (communities[1], users[5], "Anyone running LLMs locally? Trying Ollama with Mistral 7B right now."),
            (communities[2], users[2], "Study circle is live 📚 — let's prep for finals together!"),
            (communities[3], users[6], "Fitness crew activated! ⚽ Post your workout milestones."),
            (communities[4], users[8], "Welcome to dev humor 😂 — drop your best deployment fail story!"),
            (communities[5], admin_user, "Elite coding league is active 🏆 — weekly challenges every Monday!"),
        ]

        for tenant, author, msg in crew_msgs:
            ChatMessage.objects.create(tenant=tenant, author=author, message=msg)

        self.stdout.write(self.style.SUCCESS(
            f"\n[OK] Seed complete!\n"
            f"   Communities: {len(communities)}\n"
            f"   Posts: {len(created_posts)}\n"
            f"   Users: {len(users)}\n"
            f"\nAdmin login: username=admin, password=AdminPass123!@#"
        ))
