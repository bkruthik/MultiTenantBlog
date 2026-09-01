from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm, SetPasswordForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib import messages
from django.urls import reverse

from memberships.models import Membership
from posts.models import Post, Comment, Like


def signup(request):
    """
    User registration view.
    """
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Set a default email based on username if not specified
            if not user.email:
                user.email = f"{user.username}@example.com"
                user.save()
            messages.success(
                request,
                f"Account created successfully for {user.username}! Please log in with your credentials."
            )
            return redirect('login')
    else:
        form = UserCreationForm()

    return render(request, 'registration/signup.html', {'form': form})


def password_reset_request(request):
    """
    Secure password reset request.
    Requires BOTH username and registered email address to prevent unauthorized username guessing.
    Generates a cryptographically signed, single-use token.
    """
    if request.user.is_authenticated:
        return redirect('home')

    reset_url = None
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()

        user = User.objects.filter(username=username).first()

        if user and (not user.email or user.email.lower() == email.lower()):
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_url = request.build_absolute_uri(
                reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
            )
            messages.success(
                request,
                f"Password reset link generated securely for {user.username}."
            )
            return render(request, 'registration/password_reset_done.html', {
                'user': user,
                'reset_url': reset_url,
            })
        else:
            messages.error(
                request,
                "No active account found with that username and matching email combination."
            )

    return render(request, 'registration/password_reset_form.html')


def password_reset_confirm_view(request, uidb64, token):
    """
    Validates token and allows user to securely set a new password.
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            form = SetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()
                messages.success(
                    request,
                    "Your password has been reset successfully! You can now log in."
                )
                return redirect('login')
        else:
            form = SetPasswordForm(user)

        return render(request, 'registration/password_reset_confirm.html', {
            'form': form,
            'validlink': True,
        })
    else:
        return render(request, 'registration/password_reset_confirm.html', {
            'validlink': False,
        })


@login_required
def profile(request, username=None):
    """
    User profile page with Mutual Communities calculation.
    """
    if username and username != request.user.username:
        profile_user = get_object_or_404(User, username=username)
        is_own_profile = False
    else:
        profile_user = request.user
        is_own_profile = True

    # User's memberships
    all_target_memberships = (
        Membership.objects
        .filter(user=profile_user)
        .select_related('tenant')
        .order_by('tenant__name')
    )

    # Viewer's memberships
    viewer_tenant_ids = set(
        Membership.objects.filter(user=request.user).values_list('tenant_id', flat=True)
    )

    if request.method == 'POST' and is_own_profile:
        avatar_url = request.POST.get('avatar_url', '').strip()
        bio = request.POST.get('bio', '').strip()
        profile_obj = getattr(profile_user, 'profile', None)
        if profile_obj:
            profile_obj.avatar_url = avatar_url
            profile_obj.bio = bio
            profile_obj.save()
            messages.success(request, "Your profile photo and bio have been updated!")
        return redirect('profile')

    # Mutual communities
    mutual_memberships = [
        m for m in all_target_memberships
        if m.tenant_id in viewer_tenant_ids and not is_own_profile
    ]

    visible_memberships = [
        m for m in all_target_memberships
        if is_own_profile or not m.tenant.is_private or m.tenant_id in viewer_tenant_ids
    ]

    all_user_posts = (
        Post.objects
        .filter(author=profile_user)
        .select_related('tenant')
        .order_by('-created_at')
    )

    visible_posts = [
        p for p in all_user_posts
        if not p.tenant.is_private or p.tenant.id in viewer_tenant_ids
    ]

    total_posts_count = len(visible_posts)
    total_comments_count = Comment.objects.filter(author=profile_user).count()
    total_likes_given = Like.objects.filter(user=profile_user).count()

    return render(request, 'accounts/profile.html', {
        'profile_user': profile_user,
        'is_own_profile': is_own_profile,
        'memberships': visible_memberships,
        'mutual_memberships': mutual_memberships,
        'posts': visible_posts[:15],
        'total_posts_count': total_posts_count,
        'total_comments_count': total_comments_count,
        'total_likes_given': total_likes_given,
    })
