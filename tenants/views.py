from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils.text import slugify
from django.db.models import Q, Count
from django.contrib import messages

from .models import Tenant, ChatMessage, auto_detect_category
from memberships.models import Membership
from posts.models import Post


@login_required
def explore(request):
    """
    Explore & Discover communities.
    Supports keyword search and dynamic 1-click category filtering.
    """
    search_query = request.GET.get('q', '').strip()
    category_filter = request.GET.get('category', '').strip()

    tenants_qs = Tenant.objects.all()

    if category_filter and category_filter.lower() != 'all':
        tenants_qs = tenants_qs.filter(category__iexact=category_filter)

    if search_query:
        tenants_qs = tenants_qs.filter(
            Q(name__icontains=search_query) | Q(description__icontains=search_query) | Q(category__icontains=search_query)
        )

    tenants_qs = tenants_qs.order_by('-created_at')

    # Get user's active tenant memberships for quick lookup
    user_memberships_dict = {
        m.tenant_id: m.role
        for m in Membership.objects.filter(user=request.user)
    }

    tenants_data = []
    for t in tenants_qs:
        member_count = t.membership_set.count()
        posts_count = t.post_set.count()
        admin_member = Membership.objects.filter(tenant=t, role='ADMIN').select_related('user').first()
        admin_user = admin_member.user if admin_member else None
        user_role = user_memberships_dict.get(t.id)

        tenants_data.append({
            'tenant': t,
            'member_count': member_count,
            'posts_count': posts_count,
            'admin_user': admin_user,
            'is_member': t.id in user_memberships_dict,
            'user_role': user_role,
        })

    # Dynamic distinct categories currently in use
    all_categories = list(
        Tenant.objects.exclude(category='').values_list('category', flat=True).distinct().order_by('category')
    )

    return render(request, 'tenants/explore.html', {
        'tenants_data': tenants_data,
        'search_query': search_query,
        'category_filter': category_filter,
        'categories': all_categories,
    })


@login_required
def tenant_create(request):
    """
    Create a new community with smart auto-detection or custom categories,
    plus custom image avatar or emoji selection.
    """
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        custom_category = request.POST.get('custom_category', '').strip()
        category_choice = request.POST.get('category', '').strip()
        is_private = request.POST.get('is_private') == 'on'
        custom_slug = request.POST.get('slug', '').strip()
        avatar_emoji = request.POST.get('avatar_emoji', '').strip()
        avatar_url = request.POST.get('avatar_url', '').strip()

        if not name:
            return render(request, 'tenants/tenant_create.html', {
                'error': 'Community name is required.',
                'name': name,
                'description': description,
                'category': category_choice,
                'custom_category': custom_category,
                'avatar_url': avatar_url,
                'is_private': is_private,
            })

        # Category resolution: custom > selected > auto-detected
        if custom_category:
            final_category = custom_category
        elif category_choice and category_choice != 'AUTO':
            final_category = category_choice
        else:
            final_category = auto_detect_category(name, description)

        # Generate unique slug
        base_slug = slugify(custom_slug if custom_slug else name)
        if not base_slug:
            base_slug = 'community'

        slug = base_slug
        counter = 1
        while Tenant.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        # Create Tenant
        new_tenant = Tenant.objects.create(
            name=name,
            slug=slug,
            description=description,
            category=final_category,
            is_private=is_private,
            avatar_emoji=avatar_emoji,
            avatar_url=avatar_url,
        )

        # Assign Creator as ADMIN
        Membership.objects.create(
            user=request.user,
            tenant=new_tenant,
            role='ADMIN'
        )

        messages.success(
            request,
            f"Community '{new_tenant.name}' created in [{final_category}]! You are the Admin."
        )
        return redirect('post_list', tenant_id=new_tenant.id)

    # GET: fetch dynamic existing categories for suggestions
    existing_categories = list(
        Tenant.objects.exclude(category='').values_list('category', flat=True).distinct().order_by('category')
    )

    return render(request, 'tenants/tenant_create.html', {
        'existing_categories': existing_categories,
    })


@login_required
def tenant_join(request, tenant_id):
    """
    One-click join for public communities.
    """
    if request.method != 'POST':
        return redirect('explore')

    tenant = get_object_or_404(Tenant, id=tenant_id)

    if tenant.is_private:
        messages.error(
            request,
            f"'{tenant.name}' is a private community. You cannot join directly without an invitation."
        )
        return redirect('explore')

    membership = Membership.objects.filter(user=request.user, tenant=tenant).first()
    if membership:
        messages.info(request, f"You are already a member of {tenant.name}.")
    else:
        Membership.objects.create(user=request.user, tenant=tenant, role='VIEWER')
        messages.success(request, f"Welcome to {tenant.name}! You are now a member.")

    return redirect('post_list', tenant_id=tenant.id)


@login_required
def tenant_leave(request, tenant_id):
    """
    Leave a community.
    """
    if request.method != 'POST':
        return redirect('home')

    tenant = get_object_or_404(Tenant, id=tenant_id)
    membership = Membership.objects.filter(user=request.user, tenant=tenant).first()

    if not membership:
        messages.info(request, "You are not a member of this community.")
        return redirect('home')

    if membership.role == 'ADMIN':
        admin_count = Membership.objects.filter(tenant=tenant, role='ADMIN').count()
        if admin_count <= 1:
            messages.error(
                request,
                "You are the only Admin in this community. Assign another Admin before leaving."
            )
            return redirect('post_list', tenant_id=tenant.id)

    membership.delete()
    messages.success(request, f"You have left the {tenant.name} community.")
    return redirect('home')


@login_required
def tenant_chat_post(request, tenant_id):
    """
    Post a message to the Crew Chat board of the tenant.
    """
    if request.method != 'POST':
        return redirect('post_list', tenant_id=tenant_id)

    tenant = get_object_or_404(Tenant, id=tenant_id)
    membership = Membership.objects.filter(user=request.user, tenant=tenant).first()

    if tenant.is_private and not membership:
        messages.error(request, "Only members can post in this community's crew chat.")
        return redirect('explore')

    message_text = request.POST.get('message', '').strip()
    if message_text:
        ChatMessage.objects.create(
            tenant=tenant,
            author=request.user,
            message=message_text
        )
        messages.success(request, "Message posted to crew chat.")
    else:
        messages.error(request, "Chat message cannot be empty.")

    return redirect(f"/posts/{tenant.id}/#crew-chat")


@login_required
def tenant_members(request, tenant_id):
    """
    Community Members & Admin Control Dashboard.
    """
    tenant = get_object_or_404(Tenant, id=tenant_id)
    current_membership = Membership.objects.filter(user=request.user, tenant=tenant).first()

    if tenant.is_private and not current_membership:
        messages.error(request, "Access restricted for private community.")
        return redirect('explore')

    memberships = (
        Membership.objects
        .filter(tenant=tenant)
        .select_related('user')
        .order_by('role', 'user__username')
    )

    is_admin = current_membership and current_membership.role == 'ADMIN'

    return render(request, 'tenants/tenant_members.html', {
        'tenant': tenant,
        'memberships': memberships,
        'current_membership': current_membership,
        'is_admin': is_admin,
    })


@login_required
def tenant_member_role_update(request, tenant_id, membership_id):
    """
    Update member role (promote to EDITOR or demote to VIEWER).
    """
    if request.method != 'POST':
        return redirect('tenant_members', tenant_id=tenant_id)

    tenant = get_object_or_404(Tenant, id=tenant_id)
    current_membership = Membership.objects.filter(user=request.user, tenant=tenant).first()

    if not current_membership or current_membership.role != 'ADMIN':
        messages.error(request, "Only the Admin can modify member roles.")
        return redirect('tenant_members', tenant_id=tenant_id)

    target_membership = get_object_or_404(Membership, id=membership_id, tenant=tenant)
    new_role = request.POST.get('role')

    if new_role in ('EDITOR', 'VIEWER'):
        target_membership.role = new_role
        target_membership.save()
        messages.success(request, f"Updated {target_membership.user.username}'s role to {new_role}.")
    else:
        messages.error(request, "Invalid role specified.")

    return redirect('tenant_members', tenant_id=tenant_id)


@login_required
def tenant_member_transfer_admin(request, tenant_id, membership_id):
    """
    Transfer primary Admin role to another member.
    """
    if request.method != 'POST':
        return redirect('tenant_members', tenant_id=tenant_id)

    tenant = get_object_or_404(Tenant, id=tenant_id)
    current_membership = Membership.objects.filter(user=request.user, tenant=tenant).first()

    if not current_membership or current_membership.role != 'ADMIN':
        messages.error(request, "Only the current Admin can transfer Admin rights.")
        return redirect('tenant_members', tenant_id=tenant_id)

    target_membership = get_object_or_404(Membership, id=membership_id, tenant=tenant)

    if target_membership.user == request.user:
        messages.info(request, "You are already the Admin.")
        return redirect('tenant_members', tenant_id=tenant_id)

    target_membership.role = 'ADMIN'
    target_membership.save()

    current_membership.role = 'EDITOR'
    current_membership.save()

    messages.success(
        request,
        f"Admin rights successfully transferred to {target_membership.user.username}! You are now an Editor."
    )
    return redirect('tenant_members', tenant_id=tenant_id)


@login_required
def tenant_member_kick(request, tenant_id, membership_id):
    """
    Kick / remove a member from the community.
    """
    if request.method != 'POST':
        return redirect('tenant_members', tenant_id=tenant_id)

    tenant = get_object_or_404(Tenant, id=tenant_id)
    current_membership = Membership.objects.filter(user=request.user, tenant=tenant).first()

    if not current_membership or current_membership.role != 'ADMIN':
        messages.error(request, "Only the Admin can remove members.")
        return redirect('tenant_members', tenant_id=tenant_id)

    target_membership = get_object_or_404(Membership, id=membership_id, tenant=tenant)

    if target_membership.user == request.user:
        messages.error(request, "You cannot kick yourself. Use the Leave option instead.")
        return redirect('tenant_members', tenant_id=tenant_id)

    username = target_membership.user.username
    target_membership.delete()
    messages.success(request, f"User '{username}' was removed from {tenant.name}.")
    return redirect('tenant_members', tenant_id=tenant_id)
