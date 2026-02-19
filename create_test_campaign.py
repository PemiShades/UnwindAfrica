#!/usr/bin/env python3
import django
import os
from datetime import datetime, timedelta
from Web.models import VotingCampaign

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Create a test campaign
campaign = VotingCampaign(
    name="Valentine's Edition 2026",
    description="Nominate someone special for an unforgettable Valentine's retreat.",
    start_date=datetime.now(),
    end_date=datetime.now() + timedelta(days=30),
    vote_price=500.00,
    rest_points_per_vote=100.00,
    is_active=True
)
campaign.save()
print('Test campaign created successfully!')
print('Campaign ID:', campaign.id)