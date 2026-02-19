#!/usr/bin/env python
"""Script to create test rest cards for the dashboard."""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from Web.models import RestCard

def create_test_cards():
    """Create 5 test rest cards."""
    print("Creating test rest cards...")
    
    # Clear existing cards
    RestCard.objects.all().delete()
    print(f"Cleared {RestCard.objects.count()} existing cards")
    
    # Create test cards
    for i in range(5):
        card = RestCard.objects.create(
            member_name=f"Test User {i+1}",
            member_email=f"test{i+1}@example.com",
            member_phone=f"+234 123 456 789{i+1}",
            status='active' if i % 2 == 0 else 'suspended'
        )
        print(f"Created card: {card.id} - {card.member_name} ({card.status})")
    
    print(f"\nTotal cards created: {RestCard.objects.count()}")
    
    # Print all cards
    print("\nAll cards:")
    for card in RestCard.objects.all():
        print(f"{card.id}: {card.member_name} ({card.status}) - {card.card_number}")

if __name__ == "__main__":
    create_test_cards()
