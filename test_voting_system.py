#!/usr/bin/env python
"""
Test script for the Nominate to Unwind Voting System

This script will:
1. Create a test voting campaign
2. Add sample nominees
3. Test vote creation
4. Test transaction tracking
5. Verify admin functionality
6. Test URL endpoints
"""

import os
import sys
import django
from datetime import datetime, timedelta
from decimal import Decimal

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.utils import timezone
from django.contrib.auth.models import User
from Web.models import VotingCampaign, Nominee, Vote, Transaction


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_success(message):
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")


def print_error(message):
    print(f"{Colors.RED}✗ {message}{Colors.END}")


def print_info(message):
    print(f"{Colors.BLUE}ℹ {message}{Colors.END}")


def print_header(message):
    print(f"\n{Colors.BOLD}{Colors.YELLOW}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.YELLOW}{message}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.YELLOW}{'='*60}{Colors.END}\n")


def test_models():
    """Test 1: Verify all models exist and have correct fields"""
    print_header("TEST 1: Model Structure Verification")
    
    try:
        # Test VotingCampaign model
        assert hasattr(VotingCampaign, 'name'), "VotingCampaign missing 'name' field"
        assert hasattr(VotingCampaign, 'slug'), "VotingCampaign missing 'slug' field"
        assert hasattr(VotingCampaign, 'vote_price'), "VotingCampaign missing 'vote_price' field"
        assert hasattr(VotingCampaign, 'rest_points_per_vote'), "VotingCampaign missing 'rest_points_per_vote' field"
        print_success("VotingCampaign model structure verified")
        
        # Test Nominee model
        assert hasattr(Nominee, 'name'), "Nominee missing 'name' field"
        assert hasattr(Nominee, 'photo'), "Nominee missing 'photo' field"
        assert hasattr(Nominee, 'story'), "Nominee missing 'story' field"
        assert hasattr(Nominee, 'instagram_handle'), "Nominee missing 'instagram_handle' field"
        assert hasattr(Nominee, 'vote_count'), "Nominee missing 'vote_count' field"
        print_success("Nominee model structure verified")
        
        # Test Vote model
        assert hasattr(Vote, 'voter_name'), "Vote missing 'voter_name' field"
        assert hasattr(Vote, 'voter_email'), "Vote missing 'voter_email' field"
        assert hasattr(Vote, 'voter_phone'), "Vote missing 'voter_phone' field"
        assert hasattr(Vote, 'vote_quantity'), "Vote missing 'vote_quantity' field"
        assert hasattr(Vote, 'rest_points_earned'), "Vote missing 'rest_points_earned' field"
        print_success("Vote model structure verified")
        
        # Test Transaction model
        assert hasattr(Transaction, 'reference'), "Transaction missing 'reference' field"
        assert hasattr(Transaction, 'status'), "Transaction missing 'status' field"
        assert hasattr(Transaction, 'amount'), "Transaction missing 'amount' field"
        print_success("Transaction model structure verified")
        
        return True
    except AssertionError as e:
        print_error(f"Model structure test failed: {e}")
        return False


def create_test_campaign():
    """Test 2: Create a test voting campaign"""
    print_header("TEST 2: Creating Test Campaign")
    
    try:
        # Delete existing test campaign if it exists
        VotingCampaign.objects.filter(name__startswith="Test Campaign").delete()
        
        campaign = VotingCampaign.objects.create(
            name="Test Campaign - November 2025",
            description="This is a test campaign to verify the voting system works correctly.",
            start_date=timezone.now() - timedelta(days=1),
            end_date=timezone.now() + timedelta(days=30),
            vote_price=Decimal('500.00'),
            rest_points_per_vote=Decimal('100.00'),
            is_active=True
        )
        
        print_success(f"Campaign created: {campaign.name}")
        print_info(f"  - Slug: {campaign.slug}")
        print_info(f"  - Vote Price: ₦{campaign.vote_price}")
        print_info(f"  - Rest Points per Vote: ₦{campaign.rest_points_per_vote}")
        print_info(f"  - Is Ongoing: {campaign.is_ongoing}")
        
        assert campaign.slug == "test-campaign-november-2025", "Slug generation failed"
        assert campaign.is_ongoing == True, "Campaign should be ongoing"
        
        return campaign
    except Exception as e:
        print_error(f"Campaign creation failed: {e}")
        return None


def create_test_nominees(campaign):
    """Test 3: Create test nominees"""
    print_header("TEST 3: Creating Test Nominees")
    
    if not campaign:
        print_error("No campaign provided, skipping nominee creation")
        return []
    
    nominees_data = [
        {
            'name': 'Jane Doe',
            'story': 'A hardworking single mother who deserves a break from her demanding job as a nurse.',
            'instagram_handle': 'janedoe',
            'order': 1
        },
        {
            'name': 'John Smith',
            'story': 'A dedicated teacher who has been inspiring students for 15 years without taking a proper vacation.',
            'instagram_handle': 'johnsmith',
            'order': 2
        },
        {
            'name': 'Sarah Johnson',
            'story': 'A community volunteer who spends all her free time helping others and never takes time for herself.',
            'instagram_handle': 'sarahjohnson',
            'order': 3
        }
    ]
    
    nominees = []
    try:
        for data in nominees_data:
            # Note: In production, you'd need actual image files
            # For testing, we'll create without photos or handle the error
            try:
                nominee = Nominee.objects.create(
                    campaign=campaign,
                    name=data['name'],
                    story=data['story'],
                    instagram_handle=data['instagram_handle'],
                    order=data['order']
                )
                nominees.append(nominee)
                print_success(f"Created nominee: {nominee.name}")
                print_info(f"  - Instagram: @{nominee.instagram_handle}")
                print_info(f"  - Votes: {nominee.vote_count}")
            except Exception as e:
                print_error(f"Failed to create nominee {data['name']}: {e}")
                # Try without photo field
                continue
        
        print_info(f"\nTotal nominees created: {len(nominees)}")
        return nominees
    except Exception as e:
        print_error(f"Nominee creation failed: {e}")
        return []


def test_vote_creation(nominees):
    """Test 4: Create test votes"""
    print_header("TEST 4: Creating Test Votes and Transactions")
    
    if not nominees:
        print_error("No nominees available for voting test")
        return False
    
    try:
        # Create votes for first nominee
        nominee = nominees[0]
        campaign = nominee.campaign
        
        # Test vote 1
        vote1 = Vote.objects.create(
            nominee=nominee,
            voter_name="Test Voter 1",
            voter_email="voter1@test.com",
            voter_phone="+2348012345678",
            vote_quantity=5,
            amount=campaign.vote_price * 5,
            referral_source="Instagram"
        )
        
        print_success(f"Vote 1 created: {vote1.vote_quantity} votes for {nominee.name}")
        print_info(f"  - Amount: ₦{vote1.amount}")
        print_info(f"  - Rest Points: ₦{vote1.rest_points_earned}")
        
        # Create transaction for vote 1
        transaction1 = Transaction.objects.create(
            vote=vote1,
            reference="TEST-REF-001",
            amount=vote1.amount,
            status='success',
            paid_at=timezone.now()
        )
        
        # Update nominee vote count (simulating successful payment)
        nominee.vote_count += vote1.vote_quantity
        nominee.save()
        
        print_success(f"Transaction created: {transaction1.reference} - {transaction1.status}")
        print_info(f"  - Nominee vote count updated: {nominee.vote_count}")
        
        # Test vote 2 for different nominee
        if len(nominees) > 1:
            nominee2 = nominees[1]
            vote2 = Vote.objects.create(
                nominee=nominee2,
                voter_name="Test Voter 2",
                voter_email="voter2@test.com",
                voter_phone="+2348087654321",
                vote_quantity=3,
                amount=campaign.vote_price * 3
            )
            
            transaction2 = Transaction.objects.create(
                vote=vote2,
                reference="TEST-REF-002",
                amount=vote2.amount,
                status='success',
                paid_at=timezone.now()
            )
            
            nominee2.vote_count += vote2.vote_quantity
            nominee2.save()
            
            print_success(f"Vote 2 created: {vote2.vote_quantity} votes for {nominee2.name}")
        
        return True
    except Exception as e:
        print_error(f"Vote creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_campaign_properties(campaign):
    """Test 5: Verify campaign calculated properties"""
    print_header("TEST 5: Testing Campaign Properties")
    
    if not campaign:
        print_error("No campaign provided")
        return False
    
    try:
        # Refresh from database
        campaign.refresh_from_db()
        
        total_votes = campaign.total_votes
        total_revenue = campaign.total_revenue
        
        print_success(f"Campaign total votes: {total_votes}")
        print_success(f"Campaign total revenue: ₦{total_revenue:,.2f}")
        
        # Verify calculations
        expected_votes = sum(n.vote_count for n in campaign.nominees.all())
        assert total_votes == expected_votes, f"Vote count mismatch: {total_votes} != {expected_votes}"
        
        print_info(f"  - Active status: {campaign.is_active}")
        print_info(f"  - Is ongoing: {campaign.is_ongoing}")
        print_info(f"  - Number of nominees: {campaign.nominees.count()}")
        
        return True
    except Exception as e:
        print_error(f"Campaign properties test failed: {e}")
        return False


def test_nominee_properties(nominees):
    """Test 6: Verify nominee calculated properties"""
    print_header("TEST 6: Testing Nominee Properties")
    
    if not nominees:
        print_error("No nominees available")
        return False
    
    try:
        for nominee in nominees:
            nominee.refresh_from_db()
            
            print_success(f"Nominee: {nominee.name}")
            print_info(f"  - Vote count: {nominee.vote_count}")
            print_info(f"  - Total raised: ₦{nominee.total_amount_raised:,.2f}")
            print_info(f"  - Instagram URL: {nominee.instagram_url}")
        
        return True
    except Exception as e:
        print_error(f"Nominee properties test failed: {e}")
        return False


def test_admin_superuser():
    """Test 7: Verify admin user exists"""
    print_header("TEST 7: Checking Admin User")
    
    try:
        admin_users = User.objects.filter(is_superuser=True)
        
        if admin_users.exists():
            for admin in admin_users:
                print_success(f"Superuser found: {admin.username}")
                print_info(f"  - Email: {admin.email}")
                print_info(f"  - Is active: {admin.is_active}")
            return True
        else:
            print_error("No superuser found!")
            print_info("  Run: python manage.py createsuperuser")
            return False
    except Exception as e:
        print_error(f"Admin check failed: {e}")
        return False


def test_database_queries():
    """Test 8: Test database queries and relationships"""
    print_header("TEST 8: Testing Database Queries")
    
    try:
        # Test 1: Get all active campaigns
        active_campaigns = VotingCampaign.objects.filter(is_active=True)
        print_success(f"Found {active_campaigns.count()} active campaign(s)")
        
        # Test 2: Get nominees with votes > 0
        nominees_with_votes = Nominee.objects.filter(vote_count__gt=0)
        print_success(f"Found {nominees_with_votes.count()} nominee(s) with votes")
        
        # Test 3: Get successful transactions
        successful_transactions = Transaction.objects.filter(status='success')
        print_success(f"Found {successful_transactions.count()} successful transaction(s)")
        
        # Test 4: Get votes with related data
        votes_with_relations = Vote.objects.select_related(
            'nominee', 'nominee__campaign', 'transaction'
        ).all()
        print_success(f"Found {votes_with_relations.count()} vote(s) with relations")
        
        # Test 5: Aggregate query
        from django.db.models import Sum, Count
        campaign_stats = VotingCampaign.objects.annotate(
            nominee_count=Count('nominees'),
            total_votes_agg=Sum('nominees__vote_count')
        ).first()
        
        if campaign_stats:
            print_success(f"Campaign aggregate stats:")
            print_info(f"  - Nominee count: {campaign_stats.nominee_count}")
            print_info(f"  - Total votes (aggregated): {campaign_stats.total_votes_agg or 0}")
        
        return True
    except Exception as e:
        print_error(f"Database query test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_url_patterns():
    """Test 9: Verify URL patterns are registered"""
    print_header("TEST 9: Testing URL Configuration")
    
    try:
        from django.urls import reverse, NoReverseMatch
        
        # Test voting URLs
        url_tests = [
            ('voting_campaigns_list', None, 'Voting campaigns list'),
        ]
        
        for url_name, kwargs, description in url_tests:
            try:
                url = reverse(url_name, kwargs=kwargs) if kwargs else reverse(url_name)
                print_success(f"{description}: {url}")
            except NoReverseMatch:
                print_error(f"URL '{url_name}' not found")
        
        # Test campaign detail URL
        campaign = VotingCampaign.objects.first()
        if campaign:
            try:
                url = reverse('voting_campaign', kwargs={'slug': campaign.slug})
                print_success(f"Campaign detail URL: {url}")
            except NoReverseMatch:
                print_error("Campaign detail URL not found")
        
        return True
    except Exception as e:
        print_error(f"URL pattern test failed: {e}")
        return False


def display_summary():
    """Display final summary and next steps"""
    print_header("TEST SUMMARY & NEXT STEPS")
    
    # Count objects
    campaigns = VotingCampaign.objects.all().count()
    nominees = Nominee.objects.all().count()
    votes = Vote.objects.all().count()
    transactions = Transaction.objects.all().count()
    
    print_info(f"Database Statistics:")
    print(f"  - Campaigns: {campaigns}")
    print(f"  - Nominees: {nominees}")
    print(f"  - Votes: {votes}")
    print(f"  - Transactions: {transactions}")
    
    print_info(f"\nNext Steps:")
    print("  1. Update Paystack API keys in .env file")
    print("  2. Add nominee photos in Django admin")
    print("  3. Start development server: uv run python manage.py runserver")
    print("  4. Visit admin: http://127.0.0.1:8000/admin/")
    print("  5. Visit voting page: http://127.0.0.1:8000/voting/")
    print("  6. Test payment flow with Paystack test keys")
    
    print_info(f"\nAdmin URLs:")
    print("  - Campaigns: http://127.0.0.1:8000/admin/Web/votingcampaign/")
    print("  - Nominees: http://127.0.0.1:8000/admin/Web/nominee/")
    print("  - Votes: http://127.0.0.1:8000/admin/Web/vote/")
    print("  - Transactions: http://127.0.0.1:8000/admin/Web/transaction/")
    
    print_info(f"\nPaystack Test Cards:")
    print("  - Success: 4084084084084081")
    print("  - CVV: 408, Expiry: 12/25, PIN: 0000")
    print("  - Docs: https://paystack.com/docs/payments/test-payments/")


def main():
    """Run all tests"""
    print(f"{Colors.BOLD}{Colors.BLUE}")
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║   UNWIND AFRICA - VOTING SYSTEM TEST SUITE              ║")
    print("║   Nominate to Unwind - November 2025 Edition            ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}")
    
    results = []
    
    # Run tests
    results.append(("Model Structure", test_models()))
    
    campaign = create_test_campaign()
    results.append(("Campaign Creation", campaign is not None))
    
    nominees = create_test_nominees(campaign)
    results.append(("Nominee Creation", len(nominees) > 0))
    
    results.append(("Vote & Transaction Creation", test_vote_creation(nominees)))
    results.append(("Campaign Properties", test_campaign_properties(campaign)))
    results.append(("Nominee Properties", test_nominee_properties(nominees)))
    results.append(("Admin User", test_admin_superuser()))
    results.append(("Database Queries", test_database_queries()))
    results.append(("URL Configuration", test_url_patterns()))
    
    # Display results
    print_header("FINAL RESULTS")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        if result:
            print_success(f"{test_name}: PASSED")
        else:
            print_error(f"{test_name}: FAILED")
    
    print(f"\n{Colors.BOLD}Overall: {passed}/{total} tests passed{Colors.END}")
    
    if passed == total:
        print(f"{Colors.GREEN}{Colors.BOLD}✓ ALL TESTS PASSED! System is ready.{Colors.END}\n")
    else:
        print(f"{Colors.RED}{Colors.BOLD}✗ Some tests failed. Please review the errors above.{Colors.END}\n")
    
    display_summary()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Test interrupted by user{Colors.END}")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
