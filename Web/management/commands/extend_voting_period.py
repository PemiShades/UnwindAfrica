"""
Management command to extend the voting period for the current campaign.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from Web.models import VotingCampaign


class Command(BaseCommand):
    help = 'Extend the voting period by a specified number of days'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days to extend the voting period (default: 7)',
        )

    def handle(self, *args, **options):
        days = options['days']
        
        # Get the most recent active campaign
        campaign = VotingCampaign.objects.filter(is_active=True).order_by('-start_date').first()
        
        if not campaign:
            self.stdout.write(self.style.ERROR('No active campaign found.'))
            return

        old_end_date = campaign.end_date
        new_end_date = old_end_date + timedelta(days=days)
        
        campaign.end_date = new_end_date
        campaign.save()
        
        self.stdout.write(self.style.SUCCESS(f'Extended voting period by {days} days.'))
        self.stdout.write(f'  Campaign: {campaign.name}')
        self.stdout.write(f'  Old end date: {old_end_date.strftime("%B %d, %Y")}')
        self.stdout.write(f'  New end date: {new_end_date.strftime("%B %d, %Y")}')
