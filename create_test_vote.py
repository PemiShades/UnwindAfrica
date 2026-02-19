from Web.models import VotingCampaign, Nominee, Vote

def create_test_vote():
    try:
        # Get first campaign and nominee
        campaign = VotingCampaign.objects.first()
        nominee = Nominee.objects.first()
        
        if not campaign or not nominee:
            print("ERROR: No campaigns or nominees found. Run setup_test_campaign.py first.")
            return None
            
        print(f"Creating test vote for campaign: {campaign.name}")
        print(f"Nominee: {nominee.name}")
        
        # Create test vote
        vote = Vote.objects.create(
            nominee=nominee,
            voter_name='Test User',
            voter_email='test@example.com',
            voter_phone='1234567890',
            vote_quantity=1,
            amount=1000,
            payment_status='pending'
        )
        
        print(f"SUCCESS: Created test vote with ID: {vote.id}")
        return vote
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        print(traceback.format_exc())
        return None

if __name__ == "__main__":
    create_test_vote()
