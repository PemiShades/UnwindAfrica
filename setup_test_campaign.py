"""
Setup script to create a complete voting campaign with nominees
This will create everything needed to test the voting system
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.utils import timezone
from django.core.files.base import ContentFile
from Web.models import VotingCampaign, Nominee
from decimal import Decimal
from datetime import timedelta


def create_test_campaign():
    """Create a complete test voting campaign with nominees"""
    
    print("\n" + "="*60)
    print("CREATING TEST VOTING CAMPAIGN")
    print("="*60)
    
    # 1. Create Campaign
    campaign_name = "Nominate to Unwind - December 2025"
    
    # Check if campaign exists
    campaign = VotingCampaign.objects.filter(slug='nominate-to-unwind-december-2025').first()
    
    if campaign:
        print(f"\nOK Campaign already exists: {campaign.name}")
        print(f"  Updating campaign...")
    else:
        print(f"\nOK Creating new campaign: {campaign_name}")
        campaign = VotingCampaign()
    
    # Set campaign details
    campaign.name = campaign_name
    campaign.slug = 'nominate-to-unwind-december-2025'
    campaign.description = "Vote for someone special who deserves a relaxing getaway! Your favorite nominee will win an all-expenses-paid Unwind Africa experience. Cast your votes now and help them win!"
    campaign.vote_price = Decimal('500.00')  # ₦500 per vote
    campaign.rest_points_per_vote = Decimal('100.00')  # 100 points per vote
    campaign.start_date = timezone.now() - timedelta(days=2)  # Started 2 days ago
    campaign.end_date = timezone.now() + timedelta(days=7)  # Ends in 7 days
    campaign.is_active = True
    campaign.save()
    
    print(f"  Campaign: {campaign.name}")
    print(f"  Vote Price: N{campaign.vote_price}")
    print(f"  Rest Points: {campaign.rest_points_per_vote} per vote")
    print(f"  Period: {campaign.start_date.date()} to {campaign.end_date.date()}")
    print(f"  Status: {'OK ACTIVE' if campaign.is_active else 'X Inactive'}")
    
    # 2. Create Nominees
    nominees_data = [
        {
            'name': 'Chioma Adeleke',
            'story': 'A dedicated healthcare worker who has been working tirelessly during the pandemic. She deserves a break to recharge and unwind after months of caring for others.',
            'instagram': 'chioma_a',
            'order': 1,
        },
        {
            'name': 'Tunde Okonkwo',
            'story': 'An inspiring teacher who goes above and beyond for his students. He uses his own money to buy supplies and stays after school to tutor struggling students. A true hero who needs some rest.',
            'instagram': 'mr_tunde',
            'order': 2,
        },
        {
            'name': 'Blessing Nwankwo',
            'story': 'A single mother of three who works two jobs to support her family while also volunteering at a local orphanage every weekend. She has the biggest heart and deserves this getaway.',
            'instagram': 'blessing_cares',
            'order': 3,
        },
        {
            'name': 'Ibrahim Mohammed',
            'story': 'A young entrepreneur who created a tech platform that helps small businesses in Nigeria go digital. Despite his success, he works 16-hour days and has never taken a vacation.',
            'instagram': 'ibrahim_tech',
            'order': 4,
        },
        {
            'name': 'Amara Obi',
            'story': 'A passionate environmental activist cleaning up Lagos beaches every weekend. She inspires her community to care for nature and deserves recognition for her selfless service.',
            'instagram': 'amara_green',
            'order': 5,
        },
        {
            'name': 'Emeka Nnamdi',
            'story': 'A firefighter who has saved countless lives and property. He works in dangerous conditions every day to keep our community safe and rarely gets the appreciation he deserves.',
            'instagram': 'brave_emeka',
            'order': 6,
        },
    ]
    
    print(f"\nOK Creating {len(nominees_data)} nominees...")
    
    created_count = 0
    updated_count = 0
    
    for data in nominees_data:
        nominee, created = Nominee.objects.get_or_create(
            campaign=campaign,
            name=data['name'],
            defaults={
                'story': data['story'],
                'instagram_handle': data['instagram'],
                'order': data['order'],
                'vote_count': 0,
            }
        )
        
        if not created:
            # Update existing
            nominee.story = data['story']
            nominee.instagram_handle = data['instagram']
            nominee.order = data['order']
            nominee.save()
            updated_count += 1
            print(f"  OK Updated: {nominee.name} (@{nominee.instagram_handle})")
        else:
            created_count += 1
            print(f"  OK Created: {nominee.name} (@{nominee.instagram_handle})")
    
    print(f"\nNominees: {created_count} created, {updated_count} updated")
    
    # 3. Add some initial votes to make it realistic
    print(f"\nOK Adding initial votes for realism...")
    
    nominees = campaign.nominees.all()
    if nominees.exists():
        # Give different nominees different vote counts
        vote_counts = [15, 23, 8, 12, 19, 5]
        for nominee, count in zip(nominees, vote_counts):
            nominee.vote_count = count
            nominee.save()
            print(f"  {nominee.name}: {count} votes")
    
    # 4. Summary
    print("\n" + "="*60)
    print("OK SETUP COMPLETE!")
    print("="*60)
    print(f"\nCampaign URL: http://localhost:8000/voting/{campaign.slug}/")
    print(f"\nTest Instructions:")
    print("1. Open the URL above in your browser")
    print("2. Browse the nominees with their stories")
    print("3. Add votes to your ballot")
    print("4. Check ballot shows 'points' not N symbol")
    print("5. Click 'Proceed to Payment'")
    print("6. Fill required 'Who told you about Unwind Africa?' field")
    print("7. View countdown timer")
    print("8. Complete test payment with Paystack")
    print("9. See thank you page with sharing options")
    
    print("\n" + "="*60)
    print("CAMPAIGN DETAILS")
    print("="*60)
    print(f"Name: {campaign.name}")
    print(f"Nominees: {campaign.nominees.count()}")
    print(f"Total Votes: {sum(n.vote_count for n in campaign.nominees.all())}")
    print(f"Vote Price: N{campaign.vote_price}")
    print(f"Rest Points: {campaign.rest_points_per_vote} per vote")
    print(f"Ends in: {(campaign.end_date - timezone.now()).days} days")
    print("="*60 + "\n")
    
    return campaign


def show_nominees(campaign):
    """Display all nominees"""
    print("\n" + "="*60)
    print("NOMINEES LIST")
    print("="*60)
    
    for nominee in campaign.nominees.all().order_by('order'):
        print(f"\n{nominee.order}. {nominee.name}")
        print(f"   Instagram: @{nominee.instagram_handle}")
        print(f"   Votes: {nominee.vote_count}")
        print(f"   Story: {nominee.story[:80]}...")


if __name__ == '__main__':
    try:
        campaign = create_test_campaign()
        show_nominees(campaign)
        
        print("\nSUCCESS! Open your browser and start testing:")
        print(f"\n   -> http://localhost:8000/voting/{campaign.slug}/\n")
        
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
