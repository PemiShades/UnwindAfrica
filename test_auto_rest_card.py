"""
Test Auto-Create Rest Card & Token Wallet Functionality
This tests that Rest Cards and Token Wallets are automatically created
when users vote for the first time.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.utils import timezone
from Web.models import VotingCampaign, Nominee, Vote, Transaction, RestCard, TokenWallet, TokenTransaction
from Web.voting_views import update_rest_card_points, update_token_wallet
from decimal import Decimal


def test_auto_create_rest_card():
    """Test that Rest Card is auto-created on first vote"""
    print("\n" + "="*60)
    print("TEST 1: Auto-Create Rest Card on First Vote")
    print("="*60)
    
    # Clean up test data
    RestCard.objects.filter(member_email='test@example.com').delete()
    Vote.objects.filter(voter_email='test@example.com').delete()
    
    # Create a test campaign
    campaign, _ = VotingCampaign.objects.get_or_create(
        name='Test Campaign',
        defaults={
            'slug': 'test-campaign',
            'description': 'Test',
            'vote_price': Decimal('500.00'),
            'rest_points_per_vote': Decimal('100.00'),
            'start_date': timezone.now(),
            'end_date': timezone.now() + timezone.timedelta(days=30),
            'is_active': True
        }
    )
    
    # Create a test nominee
    nominee, _ = Nominee.objects.get_or_create(
        campaign=campaign,
        name='Test Nominee',
        defaults={
            'story': 'Test story',
            'order': 1
        }
    )
    
    # Create a vote (simulating a user voting for the first time)
    vote = Vote.objects.create(
        nominee=nominee,
        voter_name='Test User',
        voter_email='test@example.com',
        voter_phone='08012345678',
        vote_quantity=5,
        amount=Decimal('2500.00')  # 5 votes × ₦500
    )
    
    print(f"✓ Vote created: {vote.vote_quantity} votes")
    print(f"  Rest Points Earned: ₦{vote.rest_points_earned}")
    
    # Call the auto-create function
    rest_card, created = update_rest_card_points(vote)
    
    # Verify Rest Card was created
    assert created == True, "Rest Card should be newly created"
    assert rest_card.member_email == 'test@example.com'
    assert rest_card.member_name == 'Test User'
    assert rest_card.status == 'waitlist'
    assert rest_card.total_rest_points == vote.rest_points_earned
    
    print(f"✓ Rest Card created automatically!")
    print(f"  Email: {rest_card.member_email}")
    print(f"  Status: {rest_card.status}")
    print(f"  Waitlist Position: #{rest_card.waitlist_position}")
    print(f"  Total Points: ₦{rest_card.total_rest_points}")
    
    print("\n✅ TEST PASSED: Rest Card auto-created successfully!")


def test_accumulate_points_existing_card():
    """Test that points accumulate on existing Rest Card"""
    print("\n" + "="*60)
    print("TEST 2: Accumulate Points on Existing Rest Card")
    print("="*60)
    
    # Get existing card from previous test
    rest_card = RestCard.objects.get(member_email='test@example.com')
    initial_points = rest_card.total_rest_points
    
    print(f"Initial Points: ₦{initial_points}")
    
    # Create another vote
    campaign = VotingCampaign.objects.get(slug='test-campaign')
    nominee = campaign.nominees.first()
    
    vote = Vote.objects.create(
        nominee=nominee,
        voter_name='Test User',
        voter_email='test@example.com',
        voter_phone='08012345678',
        vote_quantity=3,
        amount=Decimal('1500.00')  # 3 votes × ₦500
    )
    
    print(f"✓ New vote created: {vote.vote_quantity} votes")
    print(f"  Rest Points Earned: ₦{vote.rest_points_earned}")
    
    # Update Rest Card
    rest_card, created = update_rest_card_points(vote)
    
    # Verify points were added (not created new)
    assert created == False, "Should use existing Rest Card"
    assert rest_card.total_rest_points == initial_points + vote.rest_points_earned
    
    print(f"✓ Points added to existing card!")
    print(f"  Previous: ₦{initial_points}")
    print(f"  Added: ₦{vote.rest_points_earned}")
    print(f"  New Total: ₦{rest_card.total_rest_points}")
    
    print("\n✅ TEST PASSED: Points accumulated successfully!")


def test_auto_activate_at_1000():
    """Test that Rest Card auto-activates at ₦1,000 points"""
    print("\n" + "="*60)
    print("TEST 3: Auto-Activate Rest Card at ₦1,000")
    print("="*60)
    
    # Get existing card
    rest_card = RestCard.objects.get(member_email='test@example.com')
    current_points = rest_card.total_rest_points
    
    print(f"Current Points: ₦{current_points}")
    print(f"Status: {rest_card.status}")
    
    # Calculate votes needed to reach ₦1,000
    points_needed = Decimal('1000.00') - current_points
    votes_needed = int(points_needed / Decimal('100.00')) + 1  # +1 to ensure we go over
    
    print(f"Points needed for activation: ₦{points_needed}")
    print(f"Voting {votes_needed} times...")
    
    # Create vote that pushes over ₦1,000
    campaign = VotingCampaign.objects.get(slug='test-campaign')
    nominee = campaign.nominees.first()
    
    vote = Vote.objects.create(
        nominee=nominee,
        voter_name='Test User',
        voter_email='test@example.com',
        voter_phone='08012345678',
        vote_quantity=votes_needed,
        amount=Decimal('500.00') * votes_needed
    )
    
    print(f"✓ Vote created: {vote.vote_quantity} votes")
    print(f"  Rest Points Earned: ₦{vote.rest_points_earned}")
    
    # Update Rest Card
    rest_card, created = update_rest_card_points(vote)
    
    # Verify auto-activation
    print(f"\n✓ Rest Card updated!")
    print(f"  Total Points: ₦{rest_card.total_rest_points}")
    print(f"  Status: {rest_card.status}")
    print(f"  Card Number: {rest_card.card_number}")
    print(f"  Activated At: {rest_card.activated_at}")
    print(f"  Expires At: {rest_card.expires_at}")
    
    assert rest_card.total_rest_points >= Decimal('1000.00'), "Should have at least ₦1,000"
    assert rest_card.status == 'active', "Should be activated"
    assert rest_card.card_number is not None, "Should have card number"
    assert rest_card.activated_at is not None, "Should have activation date"
    assert rest_card.expires_at is not None, "Should have expiration date"
    
    print("\n✅ TEST PASSED: Rest Card auto-activated at ₦1,000!")


def test_auto_create_token_wallet():
    """Test that Token Wallet is auto-created on first vote"""
    print("\n" + "="*60)
    print("TEST 4: Auto-Create Token Wallet on First Vote")
    print("="*60)
    
    # Clean up test data
    TokenWallet.objects.filter(member_email='tokens@example.com').delete()
    Vote.objects.filter(voter_email='tokens@example.com').delete()
    
    # Create a vote
    campaign = VotingCampaign.objects.get(slug='test-campaign')
    nominee = campaign.nominees.first()
    
    vote = Vote.objects.create(
        nominee=nominee,
        voter_name='Token User',
        voter_email='tokens@example.com',
        voter_phone='08087654321',
        vote_quantity=5,
        amount=Decimal('2500.00')
    )
    
    print(f"✓ Vote created: {vote.vote_quantity} votes")
    
    # Call the auto-create function
    wallet, created = update_token_wallet(vote)
    
    # Verify Token Wallet was created
    assert created == True, "Token Wallet should be newly created"
    assert wallet.member_email == 'tokens@example.com'
    assert wallet.tokens_earned == vote.vote_quantity * 100
    
    # Verify transaction was logged
    transactions = TokenTransaction.objects.filter(wallet=wallet)
    assert transactions.count() == 1, "Should have 1 transaction"
    
    tx = transactions.first()
    assert tx.transaction_type == 'earn'
    assert tx.amount == vote.vote_quantity * 100
    
    print(f"✓ Token Wallet created automatically!")
    print(f"  Email: {wallet.member_email}")
    print(f"  Tokens Earned: {wallet.tokens_earned}")
    print(f"  Available: {wallet.available_tokens}")
    print(f"\n✓ Transaction logged:")
    print(f"  Type: {tx.transaction_type}")
    print(f"  Amount: {tx.amount}")
    print(f"  Description: {tx.description}")
    
    print("\n✅ TEST PASSED: Token Wallet auto-created successfully!")


def test_accumulate_tokens_existing_wallet():
    """Test that tokens accumulate on existing wallet"""
    print("\n" + "="*60)
    print("TEST 5: Accumulate Tokens on Existing Wallet")
    print("="*60)
    
    # Get existing wallet
    wallet = TokenWallet.objects.get(member_email='tokens@example.com')
    initial_tokens = wallet.tokens_earned
    
    print(f"Initial Tokens: {initial_tokens}")
    
    # Create another vote
    campaign = VotingCampaign.objects.get(slug='test-campaign')
    nominee = campaign.nominees.first()
    
    vote = Vote.objects.create(
        nominee=nominee,
        voter_name='Token User',
        voter_email='tokens@example.com',
        voter_phone='08087654321',
        vote_quantity=3,
        amount=Decimal('1500.00')
    )
    
    # Update wallet
    wallet, created = update_token_wallet(vote)
    
    # Verify tokens were added
    assert created == False, "Should use existing wallet"
    assert wallet.tokens_earned == initial_tokens + (vote.vote_quantity * 100)
    
    # Verify new transaction was logged
    transactions = TokenTransaction.objects.filter(wallet=wallet)
    assert transactions.count() == 2, "Should have 2 transactions now"
    
    print(f"✓ Tokens added to existing wallet!")
    print(f"  Previous: {initial_tokens}")
    print(f"  Added: {vote.vote_quantity * 100}")
    print(f"  New Total: {wallet.tokens_earned}")
    print(f"  Total Transactions: {transactions.count()}")
    
    print("\n✅ TEST PASSED: Tokens accumulated successfully!")


def run_all_tests():
    """Run all tests"""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*10 + "AUTO-CREATE REST CARD & TOKEN WALLET TESTS" + " "*10 + "║")
    print("╚" + "="*58 + "╝")
    
    try:
        test_auto_create_rest_card()
        test_accumulate_points_existing_card()
        test_auto_activate_at_1000()
        test_auto_create_token_wallet()
        test_accumulate_tokens_existing_wallet()
        
        print("\n" + "="*60)
        print("🎉 ALL TESTS PASSED! 🎉")
        print("="*60)
        print("\n✅ Rest Cards auto-create on first vote")
        print("✅ Rest Points accumulate automatically")
        print("✅ Cards auto-activate at ₦1,000")
        print("✅ Token Wallets auto-create on first vote")
        print("✅ Tokens accumulate automatically")
        print("\n" + "="*60)
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    run_all_tests()
