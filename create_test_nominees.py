import os
import sys
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from Web.models import VotingCampaign, Nominee

def create_test_nominees():
    # Get the active campaign
    campaign = VotingCampaign.objects.filter(is_active=True).order_by('-start_date').first()
    
    if not campaign:
        print("No active campaign found. Please create a campaign first.")
        return
    
    # Create test nominees
    nominees_data = [
        {"name": "James & Sarah", "number": 1, "vote_count": 150},
        {"name": "Michael & Emily", "number": 2, "vote_count": 200},
        {"name": "David & Jessica", "number": 3, "vote_count": 180},
        {"name": "Christopher & Ashley", "number": 4, "vote_count": 120},
        {"name": "Matthew & Amanda", "number": 5, "vote_count": 175},
        {"name": "Daniel & Samantha", "number": 6, "vote_count": 190},
    ]
    
    created_count = 0
    for nominee_data in nominees_data:
        try:
            nominee, created = Nominee.objects.get_or_create(
                campaign=campaign,
                number=nominee_data["number"],
                defaults={
                    "name": nominee_data["name"],
                    "vote_count": nominee_data["vote_count"]
                }
            )
            
            if created:
                created_count += 1
                print(f"Created nominee: {nominee_data['name']} (Number {nominee_data['number']})")
            else:
                print(f"Nominee already exists: {nominee_data['name']} (Number {nominee_data['number']})")
        except Exception as e:
            print(f"Error creating nominee {nominee_data['name']}: {e}")
    
    print(f"\nSuccessfully created {created_count} test nominees.")
    print(f"Total nominees in campaign '{campaign.name}': {campaign.nominees.count()}")

if __name__ == "__main__":
    create_test_nominees()
