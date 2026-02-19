from django.core.management.base import BaseCommand
from datetime import datetime, timedelta
from Web.models import VotingCampaign

class Command(BaseCommand):
    help = 'Create a test voting campaign'

    def handle(self, *args, **options):
        # Calculate dates for the campaign (next 30 days)
        start_date = datetime.now()
        end_date = start_date + timedelta(days=30)

        # Create the campaign
        campaign = VotingCampaign.objects.create(
            name="Nominate to Unwind — February Edition",
            slug="february-edition",
            description="Give someone special the gift of relaxation this February. Nominate a couple or person for an unforgettable unwind experience.",
            tagline="Spread love and relaxation this February",
            start_date=start_date,
            end_date=end_date,
            vote_price=5000.00,
            rest_points_per_vote=100.00,
            grand_prize="Luxury Getaway",
            grand_prize_description="A romantic weekend getaway for two at a 5-star resort with spa treatments and fine dining.",
            second_prize="Spa Retreat",
            second_prize_description="Pampering spa day for two with massages, facials, and wellness treatments.",
            third_prize="Dinner & Movie",
            third_prize_description="Romantic dinner for two at a top restaurant followed by movie tickets.",
            prize_description="Exciting prizes await the lucky winners. Every nomination gives someone a chance to win these amazing rewards.",
            is_active=True
        )

        self.stdout.write(self.style.SUCCESS(f'Successfully created test campaign: {campaign.name}'))