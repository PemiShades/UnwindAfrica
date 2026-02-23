"""
Django management command to seed campaign for nominations.
Ensures a current campaign is available for the nomination page.

Usage: python manage.py seed_campaign
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from Web.models import VotingCampaign


class Command(BaseCommand):
    help = 'Seeds database with current Unwind Africa nomination campaign'

    def handle(self, *args, **options):
        # Check if active campaign already exists
        active_campaign = VotingCampaign.objects.filter(is_active=True).first()
        
        if active_campaign:
            self.stdout.write(
                self.style.WARNING(
                    f'Active campaign already exists: "{active_campaign.name}"'
                )
            )
            return

        # Campaign dates
        now = timezone.now()
        start_date = now
        end_date = now + timedelta(days=90)  # 3 months campaign

        # Create the campaign
        campaign = VotingCampaign.objects.create(
            name='Nominate to Unwind — Students & Youth Edition',
            tagline='Honour resilience. Recognise strength.',
            slug='nominate-to-unwind-students-youth',
            description="""We are opening nominations to honour students and young people who are navigating responsibility, pressure, leadership, and growth beyond their age.

This edition recognises resilience, quiet strength, and young individuals who continue to show up despite challenges.

Nominate someone today and help us celebrate the next generation of leaders.""",
            start_date=start_date,
            end_date=end_date,
            vote_price=500.00,
            rest_points_per_vote=100.00,
            is_active=True,
            # Prize details
            grand_prize='Cash Prize + Features & Opportunities',
            grand_prize_description='The winner receives a cash prize and will be featured across all Unwind Africa platforms with exclusive opportunities to collaborate.',
            second_prize='Featured Recognition',
            second_prize_description='Runner-up will receive recognition on all Unwind Africa platforms and special privileges.',
            third_prize='Certificate of Recognition',
            third_prize_description='Third-place nominee will receive an official Unwind Africa certificate.',
            prize_description="""Winners will be announced at our grand finale event. All selected nominees will receive recognition and prizes based on their voting performance.""",
        )

        self.stdout.write(
            self.style.SUCCESS(
                f'✓ Campaign created successfully: "{campaign.name}"'
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f'  Start Date: {campaign.start_date.strftime("%B %d, %Y")}'
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f'  End Date: {campaign.end_date.strftime("%B %d, %Y")}'
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f'  Status: Active'
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f'\nNomination page is now available at: /nominate/'
            )
        )
