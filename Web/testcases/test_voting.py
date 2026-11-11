from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from django.test import override_settings
from django.core import signing
from datetime import timedelta
from decimal import Decimal
from io import BytesIO
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch
import json
from Web.models import VotingCampaign, Nominee, Vote
from Web.models import (
    Transaction, GroupGetawayPackage, PackageOrder, PackagePayment,
    PackageInstalment, GroupGetawayEarlyAccessOffer,
)


class VotingViewTests(TestCase):
    """Tests for voting views"""

    def setUp(self):
        """Set up test data"""
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )

        # Create a test campaign
        self.campaign = VotingCampaign.objects.create(
            name='Test Campaign',
            tagline='Test tagline',
            description='Test description',
            start_date=timezone.now() - timedelta(days=1),
            end_date=timezone.now() + timedelta(days=30),
            vote_price=100,
            is_active=True
        )

        # Create a test nominee
        self.nominee = Nominee.objects.create(
            name='Test Nominee',
            number='12345',
            story='Test story',
            campaign=self.campaign
        )

    def test_vote_view(self):
        """Test the vote view"""
        # Get the vote page
        response = self.client.get(reverse('voting_campaigns_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'Web/voting/campaigns_list.html')

    def test_payment_view(self):
        """Test the payment view"""
        # Create a test vote
        vote = Vote.objects.create(
            nominee=self.nominee,
            voter_name='Test Voter',
            voter_email='voter@example.com',
            voter_phone='1234567890',
            vote_quantity=1,
            amount=100
        )

        # Get the payment page
        response = self.client.get(reverse('payment', args=[vote.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'Web/payment.html')

    @override_settings(PAYSTACK_SECRET_KEY='sk_test_legacy_checkout')
    @patch('Web.views.requests.post')
    def test_payment_post_initializes_paystack_instead_of_marking_vote_paid(self, post):
        from types import SimpleNamespace

        vote = Vote.objects.create(
            nominee=self.nominee, voter_name='Test Voter',
            voter_email='voter@example.com', voter_phone='1234567890',
            vote_quantity=1, amount=100,
        )
        post.return_value = SimpleNamespace(
            ok=True,
            json=lambda: {'status': True, 'data': {
                'reference': 'VOTE-TEST-REF',
                'authorization_url': 'https://checkout.paystack.com/test',
                'access_code': 'test-access',
            }},
        )

        response = self.client.post(reverse('payment', args=[vote.id]), {
            'payment_method': 'paystack', 'email': vote.voter_email,
        })
        vote.refresh_from_db()
        transaction = Transaction.objects.get(vote=vote)
        self.assertRedirects(response, 'https://checkout.paystack.com/test', fetch_redirect_response=False)
        self.assertEqual(vote.payment_status, 'pending')
        self.assertEqual(transaction.status, 'pending')
        self.assertEqual(transaction.amount, Decimal('100'))

    def test_legacy_payment_cannot_mark_vote_paid_without_paystack(self):
        vote = Vote.objects.create(
            nominee=self.nominee, voter_name='Test Voter',
            voter_email='voter@example.com', voter_phone='1234567890',
            vote_quantity=1, amount=100,
        )
        response = self.client.post(reverse('payment', args=[vote.id]), {
            'payment_method': 'bank_transfer', 'email': vote.voter_email,
        })
        vote.refresh_from_db()
        self.assertEqual(vote.payment_status, 'pending')
        self.assertEqual(response.status_code, 302)

    def test_vote_confirmation_view(self):
        """Test the vote confirmation view"""
        # Create a test vote
        vote = Vote.objects.create(
            nominee=self.nominee,
            voter_name='Test Voter',
            voter_email='voter@example.com',
            voter_phone='1234567890',
            vote_quantity=1,
            amount=100,
            payment_status='paid'
        )

        # Get the confirmation page
        response = self.client.get(reverse('vote_confirmation', args=[vote.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'Web/vote_confirmation.html')


class VotingFormTests(TestCase):
    """Tests for voting forms"""

    def setUp(self):
        """Set up test data"""
        # Create a test campaign
        self.campaign = VotingCampaign.objects.create(
            name='Test Campaign',
            tagline='Test tagline',
            description='Test description',
            start_date=timezone.now() - timedelta(days=1),
            end_date=timezone.now() + timedelta(days=30),
            vote_price=100,
            is_active=True
        )

    def test_voting_form_valid(self):
        """Test that the voting form is valid with valid data"""
        from Web.forms import VotingForm

        data = {
            'NOMINEE_NUMBER': '12345',
            'COUPLE_NAME': 'Test Couple',
            'VOTER_NAME': 'Test Voter',
            'VOTER_PHONE': '1234567890',
            'NUMBER_OF_VOTES': 1
        }

        image = Image.new('RGB', (1, 1), color='white')
        image_bytes = BytesIO()
        image.save(image_bytes, format='PNG')
        proof = SimpleUploadedFile('proof.png', image_bytes.getvalue(), content_type='image/png')
        form = VotingForm(data, files={'PROOF_OF_PAYMENT': proof})
        self.assertTrue(form.is_valid())

    def test_voting_form_invalid(self):
        """Test that the voting form is invalid with invalid data"""
        from Web.forms import VotingForm

        data = {
            'NOMINEE_NUMBER': '',  # Empty nominee number
            'COUPLE_NAME': 'Test Couple',
            'VOTER_NAME': 'Test Voter',
            'VOTER_PHONE': '1234567890',
            'NUMBER_OF_VOTES': 1
        }

        form = VotingForm(data)
        self.assertFalse(form.is_valid())


class PaystackWebhookTests(TestCase):
    @override_settings(PAYSTACK_SECRET_KEY='sk_test_webhook_unit_test')
    def test_vote_charge_requires_exact_signed_payment_and_is_idempotent(self):
        import hashlib
        import hmac
        import json

        from django.test import RequestFactory
        from Web.voting_views import paystack_webhook

        campaign = VotingCampaign.objects.create(
            name='Webhook Campaign',
            tagline='Test',
            description='Test',
            start_date=timezone.now() - timedelta(days=1),
            end_date=timezone.now() + timedelta(days=30),
            vote_price=100,
            is_active=True,
        )
        nominee = Nominee.objects.create(
            name='Webhook Nominee', number='WEB-1', story='Test', campaign=campaign,
        )
        vote = Vote.objects.create(
            nominee=nominee, voter_name='Test Voter', voter_email='webhook@example.com',
            voter_phone='08000000000', vote_quantity=2, amount=200,
        )
        reference = 'WEBHOOK-TEST-REFERENCE'
        transaction = Transaction.objects.create(
            vote=vote, reference=reference, amount=200, status='pending',
        )
        payload = json.dumps({
            'event': 'charge.success',
            'data': {
                'status': 'success', 'reference': reference,
                'amount': 20000, 'currency': 'NGN',
            },
        }).encode()
        signature = hmac.new(
            b'sk_test_webhook_unit_test', payload, hashlib.sha512,
        ).hexdigest()
        factory = RequestFactory()

        wrong_amount = json.loads(payload)
        wrong_amount['data']['amount'] = 10000
        wrong_body = json.dumps(wrong_amount).encode()
        wrong_signature = hmac.new(
            b'sk_test_webhook_unit_test', wrong_body, hashlib.sha512,
        ).hexdigest()
        rejected = paystack_webhook(factory.post(
            '/voting/webhook/paystack/', wrong_body, content_type='application/json',
            HTTP_X_PAYSTACK_SIGNATURE=wrong_signature,
        ))
        self.assertEqual(rejected.status_code, 400)
        transaction.refresh_from_db()
        self.assertEqual(transaction.status, 'pending')
        self.assertEqual(nominee.vote_count, 0)

        request = factory.post(
            '/voting/webhook/paystack/', payload, content_type='application/json',
            HTTP_X_PAYSTACK_SIGNATURE=signature,
        )
        self.assertEqual(paystack_webhook(request).status_code, 200)
        self.assertEqual(paystack_webhook(request).status_code, 200)
        transaction.refresh_from_db()
        nominee.refresh_from_db()
        self.assertEqual(transaction.status, 'success')
        self.assertEqual(nominee.vote_count, 2)

    def test_package_payment_confirmation_is_idempotent_and_applies_early_access(self):
        from Web.views import _confirm_package_payment

        package = GroupGetawayPackage.objects.create(
            name='Webhook Package Escape', price_per_person=Decimal('70000'),
        )
        order = PackageOrder.objects.create(
            customer_email='package@example.com', customer_name='Package Member',
            package=package, package_price=Decimal('70000'), duration_months=3,
            subtotal=Decimal('70000'), instalment_charges=Decimal('3500'),
            grand_total=Decimal('73500'), monthly_contribution=Decimal('24500'),
            amount_paid=Decimal('0'), outstanding_balance=Decimal('73500'), status='pending',
        )
        for month in range(1, 4):
            PackageInstalment.objects.create(
                order=order, month_number=month, due_date=timezone.localdate(),
                main_amount_due=Decimal('24500'), total_due=Decimal('24500'),
                status='pending',
            )
        payment = PackagePayment.objects.create(
            order=order, amount=Decimal('24500'), reference='PACKAGE-WEBHOOK-1',
            paystack_reference='PACKAGE-WEBHOOK-1', is_initial_deposit=True, status='pending',
        )
        payload = {'data': {
            'status': 'success', 'reference': 'PACKAGE-WEBHOOK-1',
            'amount': 2450000, 'currency': 'NGN',
        }}

        confirmed_order, first_confirmation = _confirm_package_payment(
            payment, payload, payload['data'],
        )
        repeated_order, repeated_confirmation = _confirm_package_payment(
            payment, payload, payload['data'],
        )
        confirmed_order.refresh_from_db()
        self.assertTrue(first_confirmation)
        self.assertFalse(repeated_confirmation)
        self.assertEqual(confirmed_order.pk, repeated_order.pk)
        self.assertEqual(confirmed_order.amount_paid, Decimal('24500'))
        self.assertEqual(confirmed_order.early_access_discount, Decimal('3500.00'))
        self.assertEqual(confirmed_order.early_access_slot, 1)
        self.assertEqual(confirmed_order.outstanding_balance, Decimal('45500.00'))
        self.assertEqual(GroupGetawayEarlyAccessOffer.objects.get(pk=1).confirmed_count, 1)


class MobileDashboardApiTests(TestCase):
    def test_order_projection_returns_every_field_used_by_mobile_client(self):
        from Web.views import mobile_dashboard_api

        package = GroupGetawayPackage.objects.create(
            name='Dashboard Test Escape', price_per_person=Decimal('70000'),
        )
        PackageOrder.objects.create(
            customer_email='member@example.com', customer_name='Test Member',
            package=package, package_price=Decimal('70000'), grand_total=Decimal('73500'),
            amount_paid=Decimal('12000'), outstanding_balance=Decimal('61500'),
            monthly_contribution=Decimal('12250'), duration_months=6, status='active',
        )
        token = signing.TimestampSigner(salt='unwind.mobile.auth').sign('member@example.com')
        response = mobile_dashboard_api(RequestFactory().get(
            '/api/v1/dashboard/', HTTP_AUTHORIZATION=f'Bearer {token}',
        ))

        self.assertEqual(response.status_code, 200)
        order = json.loads(response.content)['orders'][0]
        self.assertEqual(order['package'], 'Dashboard Test Escape')
        self.assertEqual(order['amount_paid'], '12000.00')
        self.assertEqual(order['grand_total'], '73500.00')
        self.assertEqual(order['outstanding_balance'], '61500.00')
        self.assertEqual(order['status'], 'Active')


class VotingModelTests(TestCase):
    """Tests for voting models"""

    def setUp(self):
        """Set up test data"""
        # Create a test campaign
        self.campaign = VotingCampaign.objects.create(
            name='Test Campaign',
            tagline='Test tagline',
            description='Test description',
            start_date=timezone.now() - timedelta(days=1),
            end_date=timezone.now() + timedelta(days=30),
            vote_price=100,
            is_active=True
        )

    def test_campaign_creation(self):
        """Test that a campaign can be created"""
        self.assertEqual(VotingCampaign.objects.count(), 1)
        self.assertEqual(self.campaign.name, 'Test Campaign')
        self.assertTrue(self.campaign.is_active)

    def test_nominee_creation(self):
        """Test that a nominee can be created"""
        nominee = Nominee.objects.create(
            name='Test Nominee',
            number='12345',
            story='Test story',
            campaign=self.campaign
        )

        self.assertEqual(Nominee.objects.count(), 1)
        self.assertEqual(nominee.name, 'Test Nominee')
        self.assertEqual(nominee.campaign, self.campaign)

    def test_vote_creation(self):
        """Test that a vote can be created"""
        nominee = Nominee.objects.create(
            name='Test Nominee',
            number='12345',
            story='Test story',
            campaign=self.campaign
        )

        vote = Vote.objects.create(
            nominee=nominee,
            voter_name='Test Voter',
            voter_email='voter@example.com',
            voter_phone='1234567890',
            vote_quantity=1,
            amount=100,
            payment_status='pending'
        )

        self.assertEqual(Vote.objects.count(), 1)
        self.assertEqual(vote.nominee, nominee)
        self.assertEqual(vote.vote_quantity, 1)
