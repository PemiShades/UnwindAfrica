from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from Web.models import VotingCampaign, Nominee, Vote


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
            start_date='2024-01-01',
            end_date='2024-12-31',
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
        response = self.client.get(reverse('vote'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'Web/vote.html')

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
            start_date='2024-01-01',
            end_date='2024-12-31',
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

        form = VotingForm(data)
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


class VotingModelTests(TestCase):
    """Tests for voting models"""

    def setUp(self):
        """Set up test data"""
        # Create a test campaign
        self.campaign = VotingCampaign.objects.create(
            name='Test Campaign',
            tagline='Test tagline',
            description='Test description',
            start_date='2024-01-01',
            end_date='2024-12-31',
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
