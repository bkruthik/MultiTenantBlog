"""
Permission helper functions for the posts application.

These simple functions centralize role-checking logic so it
doesn't need to be repeated throughout views.py.
"""

from memberships.models import Membership


def get_membership(user, tenant):
    """
    Return the user's Membership for the given tenant, or None
    if the user is not a member of that tenant.
    """
    return Membership.objects.filter(user=user, tenant=tenant).first()


def can_create_post(membership):
    """ADMIN and EDITOR roles can create posts. VIEWER cannot."""
    return membership is not None and membership.role in ('ADMIN', 'EDITOR')


def can_edit_post(membership):
    """ADMIN and EDITOR roles can edit posts. VIEWER cannot."""
    return membership is not None and membership.role in ('ADMIN', 'EDITOR')


def can_delete_post(membership):
    """Only ADMIN role can delete posts."""
    return membership is not None and membership.role == 'ADMIN'
