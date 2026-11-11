import json
import zipfile
from io import BytesIO
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.core import mail
from django.urls import reverse

from Web.models import GroupGetawayPackage, PackageAddOn, PackageOrder, PackagePayment, Post


class CmsPackageActionsTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(
            username='cms-staff', password='test-password', email='staff@example.test', is_staff=True
        )
        self.client.force_login(self.staff)

    def post_json(self, url, payload):
        return self.client.post(url, data=json.dumps(payload), content_type='application/json')

    def test_package_create_edit_zero_values_and_delete(self):
        response = self.post_json(reverse('create_package'), {
            'name': 'Test Retreat', 'price_per_person': '185000',
            'instalment_charge_percent': '0', 'instalment_charge_flat': '0',
            'available_durations': '3,6,9,12', 'is_active': True,
        })
        self.assertEqual(response.status_code, 200, response.content)
        package_id = response.json()['package']['id']
        package = GroupGetawayPackage.objects.get(pk=package_id)
        self.assertEqual(package.price_per_person, 185000)

        response = self.post_json(reverse('edit_package', args=[package_id]), {
            'name': 'Test Retreat', 'price_per_person': '0',
            'instalment_charge_percent': '0', 'instalment_charge_flat': '0',
            'available_durations': '6,12', 'is_active': False,
        })
        self.assertEqual(response.status_code, 200, response.content)
        package.refresh_from_db()
        self.assertEqual(package.price_per_person, 0)
        self.assertEqual(package.available_durations, '6,12')
        self.assertFalse(package.is_active)

        response = self.client.post(reverse('delete_package', args=[package_id]))
        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(GroupGetawayPackage.objects.filter(pk=package_id).exists())

    def test_addon_create_edit_zero_values_and_delete(self):
        response = self.post_json(reverse('create_addon'), {
            'name': 'Wellness Session', 'price': '35000', 'regular_price': '40000', 'is_active': True,
        })
        self.assertEqual(response.status_code, 200, response.content)
        addon_id = response.json()['addon']['id']

        response = self.post_json(reverse('edit_addon', args=[addon_id]), {
            'name': 'Wellness Session', 'price': '0', 'regular_price': '0', 'is_active': False,
        })
        self.assertEqual(response.status_code, 200, response.content)
        addon = PackageAddOn.objects.get(pk=addon_id)
        self.assertEqual(addon.price, 0)
        self.assertEqual(addon.regular_price, 0)
        self.assertFalse(addon.is_active)

        response = self.client.post(reverse('delete_addon', args=[addon_id]))
        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(PackageAddOn.objects.filter(pk=addon_id).exists())

    def test_package_and_addon_editor_modals_render_in_cms(self):
        response = self.client.get(reverse('dashboard_home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="blogRichEditor"')
        self.assertContains(response, 'showPkgModal')
        self.assertContains(response, 'showAddonModal')
        self.assertContains(response, 'Export all data')

    def test_engagement_chart_returns_selected_month_window(self):
        response = self.client.get(reverse('engagement_data'), {'months': 3})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['labels']), 3)
        response = self.client.get(reverse('engagement_data'), {'months': 6})
        self.assertEqual(len(response.json()['counts']), 6)

    def test_complete_export_contains_web_model_csvs_and_excludes_credentials(self):
        response = self.client.get(reverse('export_all_dashboard_data'))
        self.assertEqual(response.status_code, 200)
        archive_bytes = b''.join(response.streaming_content)
        with zipfile.ZipFile(BytesIO(archive_bytes)) as archive:
            names = set(archive.namelist())
        self.assertIn('packageorder.csv', names)
        self.assertIn('packagepayment.csv', names)
        self.assertIn('votingcampaign.csv', names)
        self.assertIn('README.txt', names)
        self.assertNotIn('packagecustomercredential.csv', names)
        self.assertNotIn('mobileloginchallenge.csv', names)

    def test_non_staff_cannot_use_cms_json_actions_or_export(self):
        regular = get_user_model().objects.create_user(username='customer', password='test-password')
        self.client.force_login(regular)
        response = self.post_json(reverse('create_package'), {'name': 'Forbidden', 'price_per_person': '10'})
        self.assertEqual(response.status_code, 302)
        response = self.client.get(reverse('export_all_dashboard_data'))
        self.assertEqual(response.status_code, 302)

    def test_non_staff_cannot_publish_blog_content(self):
        regular = get_user_model().objects.create_user(username='reader', password='test-password')
        self.client.force_login(regular)
        response = self.client.post(reverse('blog_create'), {'title': 'Unauthorized story', 'action': 'publish'})
        self.assertEqual(response.status_code, 302)

    def test_staff_blog_publish_persists_metadata_and_fixed_author(self):
        image = Image.new('RGB', (2, 2), color='white')
        image_bytes = BytesIO()
        image.save(image_bytes, format='PNG')
        response = self.client.post(reverse('blog_create'), {
            'title': 'A considered story', 'category': 'Travel',
            'publication_date': '2026-11-10', 'tags': 'rest, Lagos',
            'design_template': 'field_notes', 'excerpt': 'A useful introduction.',
            'content': '<p>Thoughtful writing.</p>', 'action': 'publish',
            'thumbnail': SimpleUploadedFile('journal.png', image_bytes.getvalue(), content_type='image/png'),
        })
        self.assertEqual(response.status_code, 200, response.content)
        post = Post.objects.get(title='A considered story')
        self.assertEqual(post.author, 'Unwind Africa Admin')
        self.assertEqual(post.tags, 'rest, Lagos')
        self.assertEqual(post.design_template, 'field_notes')
        self.assertTrue(post.is_published)
        post.thumbnail.delete(save=False)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend', PACKAGE_PAYMENT_NOTIFY_EMAILS=[])
    def test_staff_can_retry_successful_payment_receipt_and_staff_email(self):
        package = GroupGetawayPackage.objects.create(name='Email Test Package', price_per_person=50000)
        order = PackageOrder.objects.create(
            customer_email='guest@example.test', customer_name='Guest Example', package=package,
            grand_total=50000, amount_paid=50000, outstanding_balance=0, status='completed',
        )
        payment = PackagePayment.objects.create(
            order=order, amount=50000, reference='cms-email-test', status='success',
        )
        response = self.client.post(reverse('retry_package_payment_emails', args=[payment.pk]))
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(len(mail.outbox), 2)
        payment.refresh_from_db()
        self.assertIsNotNone(payment.admin_confirmation_sent_at)
        self.assertIsNotNone(payment.customer_confirmation_sent_at)
        self.assertTrue(any('Congratulations' in message.subject for message in mail.outbox))
