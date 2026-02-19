import os
import sys
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from Web.models import VotingCampaign, Nominee

# Get the active campaign
campaign = VotingCampaign.objects.filter(is_active=True).first()

if campaign:
    print('Campaign:', campaign.name)
    nominees = Nominee.objects.filter(campaign=campaign)
    print(f'Nominees count: {nominees.count()}')
    
    for nominee in nominees:
        print(f'  - {nominee.name} (Number {nominee.number}, Votes {nominee.vote_count})')
else:
    print('No active campaign found')
