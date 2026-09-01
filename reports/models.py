from django.db import models
from django.contrib.auth.models import User
from tenants.models import Tenant


class Report(models.Model):
    REASON_CHOICES = [
        ('SPAM', 'Spam or unwanted content'),
        ('HARASSMENT', 'Harassment or bullying'),
        ('INAPPROPRIATE', 'Inappropriate or offensive content'),
        ('MISINFORMATION', 'Misinformation or false information'),
        ('IMPERSONATION', 'Impersonating another person'),
        ('HATE_SPEECH', 'Hate speech or discrimination'),
        ('OTHER', 'Other'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending Review'),
        ('REVIEWED', 'Reviewed — Action Taken'),
        ('DISMISSED', 'Dismissed — No Violation Found'),
    ]

    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports_made')

    # Target: one of these will be set (user OR community)
    reported_user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name='reports_received'
    )
    reported_community = models.ForeignKey(
        Tenant, null=True, blank=True, on_delete=models.SET_NULL, related_name='reports_received'
    )

    reason = models.CharField(max_length=30, choices=REASON_CHOICES)
    description = models.TextField(blank=True, help_text='Optionally describe the violation in more detail.')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    admin_notes = models.TextField(blank=True, help_text='Internal notes for moderators.')
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        if self.reported_user:
            return f"Report on @{self.reported_user.username} by @{self.reporter.username} ({self.reason})"
        return f"Report on community '{self.reported_community}' by @{self.reporter.username} ({self.reason})"

    @property
    def target_label(self):
        if self.reported_user:
            return f"User @{self.reported_user.username}"
        if self.reported_community:
            return f"Community '{self.reported_community.name}'"
        return "Unknown"
