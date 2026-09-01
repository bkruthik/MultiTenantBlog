from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from tenants.models import Tenant
from reports.models import Report


class ReportSystemTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.reporter = User.objects.create_user(username='reporter_user', password='password123', email='rep@example.com')
        self.target_user = User.objects.create_user(username='spammer_user', password='password123', email='spam@example.com')
        self.staff_admin = User.objects.create_user(username='staff_mod', password='password123', email='staff@example.com', is_staff=True)

        self.community = Tenant.objects.create(
            name='Questionable Group',
            slug='questionable-group',
            category='GENERAL',
            is_private=False
        )

    def test_report_user_success(self):
        self.client.login(username='reporter_user', password='password123')
        url = reverse('report_user', args=[self.target_user.username])

        # GET form
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)

        # POST report
        res = self.client.post(url, {
            'reason': 'SPAM',
            'description': 'Posting spam links everywhere.'
        })
        self.assertRedirects(res, reverse('user_profile', args=[self.target_user.username]))

        report = Report.objects.filter(reporter=self.reporter, reported_user=self.target_user).first()
        self.assertIsNotNone(report)
        self.assertEqual(report.reason, 'SPAM')
        self.assertEqual(report.status, 'PENDING')

    def test_cannot_report_self(self):
        self.client.login(username='reporter_user', password='password123')
        url = reverse('report_user', args=[self.reporter.username])
        res = self.client.get(url)
        self.assertRedirects(res, reverse('user_profile', args=[self.reporter.username]))
        self.assertEqual(Report.objects.count(), 0)

    def test_report_community_success(self):
        self.client.login(username='reporter_user', password='password123')
        url = reverse('report_community', args=[self.community.id])

        # GET form
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)

        # POST report
        res = self.client.post(url, {
            'reason': 'INAPPROPRIATE',
            'description': 'Violates community guidelines.'
        })
        self.assertRedirects(res, reverse('post_list', args=[self.community.id]))

        report = Report.objects.filter(reporter=self.reporter, reported_community=self.community).first()
        self.assertIsNotNone(report)
        self.assertEqual(report.reason, 'INAPPROPRIATE')
        self.assertEqual(report.status, 'PENDING')

    def test_duplicate_pending_report_prevented(self):
        Report.objects.create(
            reporter=self.reporter,
            reported_user=self.target_user,
            reason='SPAM'
        )
        self.client.login(username='reporter_user', password='password123')
        url = reverse('report_user', args=[self.target_user.username])
        res = self.client.post(url, {'reason': 'HARASSMENT', 'description': 'More spam'})
        self.assertRedirects(res, reverse('user_profile', args=[self.target_user.username]))
        # Still only 1 report
        self.assertEqual(Report.objects.filter(reporter=self.reporter, reported_user=self.target_user).count(), 1)

    def test_moderation_inbox_requires_staff(self):
        # Regular user denied
        self.client.login(username='reporter_user', password='password123')
        res = self.client.get(reverse('reports_inbox'))
        self.assertEqual(res.status_code, 302)  # Redirects to login due to user_passes_test

        # Staff user allowed
        self.client.login(username='staff_mod', password='password123')
        res = self.client.get(reverse('reports_inbox'))
        self.assertEqual(res.status_code, 200)

    def test_moderator_can_review_and_dismiss_reports(self):
        report = Report.objects.create(
            reporter=self.reporter,
            reported_user=self.target_user,
            reason='SPAM'
        )
        self.client.login(username='staff_mod', password='password123')
        action_url = reverse('report_action', args=[report.id])

        # Mark REVIEWED
        res = self.client.post(action_url, {
            'action': 'REVIEWED',
            'admin_notes': 'User warned and spam removed.'
        })
        self.assertRedirects(res, reverse('reports_inbox'))

        report.refresh_from_db()
        self.assertEqual(report.status, 'REVIEWED')
        self.assertEqual(report.admin_notes, 'User warned and spam removed.')
        self.assertIsNotNone(report.reviewed_at)
