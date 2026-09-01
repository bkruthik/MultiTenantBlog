from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone

from tenants.models import Tenant
from .models import Report


def _is_staff(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


@login_required
def report_user(request, username):
    """
    Report another user for a policy violation.
    """
    reported = get_object_or_404(User, username=username)

    if reported == request.user:
        messages.error(request, "You cannot report yourself.")
        return redirect('user_profile', username=username)

    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        description = request.POST.get('description', '').strip()

        if not reason:
            return render(request, 'reports/report_user.html', {
                'reported': reported,
                'reasons': Report.REASON_CHOICES,
                'error': 'Please select a reason for the report.',
                'form_description': description,
            })

        # Prevent duplicate pending report
        existing = Report.objects.filter(
            reporter=request.user,
            reported_user=reported,
            status='PENDING'
        ).exists()

        if existing:
            messages.warning(
                request,
                f"You already have a pending report against @{reported.username}. "
                "Our moderation team will review it soon."
            )
            return redirect('user_profile', username=username)

        Report.objects.create(
            reporter=request.user,
            reported_user=reported,
            reason=reason,
            description=description,
        )
        messages.success(
            request,
            f"Report against @{reported.username} submitted. "
            "Our moderation team will review it within 24 hours. Thank you for keeping the community safe."
        )
        return redirect('user_profile', username=username)

    return render(request, 'reports/report_user.html', {
        'reported': reported,
        'reasons': Report.REASON_CHOICES,
    })


@login_required
def report_community(request, tenant_id):
    """
    Report a community for a policy violation.
    """
    tenant = get_object_or_404(Tenant, id=tenant_id)

    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        description = request.POST.get('description', '').strip()

        if not reason:
            return render(request, 'reports/report_community.html', {
                'tenant': tenant,
                'reasons': Report.REASON_CHOICES,
                'error': 'Please select a reason for the report.',
                'form_description': description,
            })

        existing = Report.objects.filter(
            reporter=request.user,
            reported_community=tenant,
            status='PENDING'
        ).exists()

        if existing:
            messages.warning(
                request,
                f"You already have a pending report for '{tenant.name}'. Our team will review it shortly."
            )
            return redirect('post_list', tenant_id=tenant.id)

        Report.objects.create(
            reporter=request.user,
            reported_community=tenant,
            reason=reason,
            description=description,
        )
        messages.success(
            request,
            f"Report for community '{tenant.name}' submitted. Thank you for helping keep the platform safe."
        )
        return redirect('post_list', tenant_id=tenant.id)

    return render(request, 'reports/report_community.html', {
        'tenant': tenant,
        'reasons': Report.REASON_CHOICES,
    })


@login_required
@user_passes_test(_is_staff)
def reports_inbox(request):
    """
    Staff/Admin moderation inbox. View and act on all submitted reports.
    """
    status_filter = request.GET.get('status', 'PENDING')
    reports_qs = Report.objects.select_related(
        'reporter', 'reported_user', 'reported_community'
    ).all()

    if status_filter in ('PENDING', 'REVIEWED', 'DISMISSED'):
        reports_qs = reports_qs.filter(status=status_filter)

    return render(request, 'reports/inbox.html', {
        'reports': reports_qs,
        'status_filter': status_filter,
        'total_pending': Report.objects.filter(status='PENDING').count(),
        'statuses': [('PENDING', 'Pending'), ('REVIEWED', 'Reviewed'), ('DISMISSED', 'Dismissed')],
    })


@login_required
@user_passes_test(_is_staff)
def report_action(request, report_id):
    """
    Moderator takes action on a report: mark reviewed or dismissed.
    """
    if request.method != 'POST':
        return redirect('reports_inbox')

    report = get_object_or_404(Report, id=report_id)
    action = request.POST.get('action')
    admin_notes = request.POST.get('admin_notes', '').strip()

    if action in ('REVIEWED', 'DISMISSED'):
        report.status = action
        report.admin_notes = admin_notes
        report.reviewed_at = timezone.now()
        report.save()
        messages.success(request, f"Report #{report.id} marked as {action}.")

    return redirect('reports_inbox')
