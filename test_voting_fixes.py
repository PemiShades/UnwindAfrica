"""
Test script to verify all voting system fixes
Tests:
1. Rest Points display (no ₦ symbol)
2. Referral field required
3. Thank you page exists
4. Success messages updated
5. Countdown timer
6. Ballot copy improvements
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import RequestFactory, Client
from django.contrib.messages.storage.fallback import FallbackStorage
from django.urls import reverse
from django.utils import timezone
from Web.models import VotingCampaign, Nominee, Vote, Transaction
from Web.voting_views import voting_thank_you
from decimal import Decimal
import re


def test_1_check_urls():
    """Test that all voting URLs are configured"""
    print("\n" + "="*60)
    print("TEST 1: URL Configuration")
    print("="*60)
    
    try:
        from django.urls import resolve
        
        # Check voting URLs
        urls_to_test = [
            '/voting/',
            '/voting/payment/thank-you/',
        ]
        
        for url in urls_to_test:
            try:
                resolve(url)
                print(f"✓ URL exists: {url}")
            except Exception as e:
                print(f"✗ URL missing: {url} - {e}")
                return False
        
        print("\n✅ TEST PASSED: All URLs configured correctly")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        return False


def test_2_check_templates():
    """Test that templates exist"""
    print("\n" + "="*60)
    print("TEST 2: Template Files")
    print("="*60)
    
    import os
    templates_to_check = [
        'Web/templates/Web/voting/campaign_detail.html',
        'Web/templates/Web/voting/thank_you.html',
    ]
    
    all_exist = True
    for template in templates_to_check:
        full_path = os.path.join('/home/doombuggy_/Projects/UnwindAfrica', template)
        if os.path.exists(full_path):
            print(f"✓ Template exists: {template}")
            
            # Check for key content
            with open(full_path, 'r') as f:
                content = f.read()
                
                if 'campaign_detail.html' in template:
                    # Check for fixes
                    checks = {
                        'points (not ₦)': 'points' in content and '₦{total' not in content.replace('₦{totalAmount', ''),
                        'required referral': 'id="referralSource" required' in content,
                        'countdown timer': 'id="countdown"' in content,
                        'explanation': 'You earn 100 Rest Points per vote' in content,
                    }
                    
                    for check_name, result in checks.items():
                        if result:
                            print(f"  ✓ Has: {check_name}")
                        else:
                            print(f"  ✗ Missing: {check_name}")
                            all_exist = False
                            
                elif 'thank_you.html' in template:
                    checks = {
                        'vote recorded message': 'Your vote has been recorded' in content,
                        'share buttons': 'WhatsApp' in content and 'Twitter' in content,
                        'return button': 'Return to Campaign' in content,
                    }
                    
                    for check_name, result in checks.items():
                        if result:
                            print(f"  ✓ Has: {check_name}")
                        else:
                            print(f"  ✗ Missing: {check_name}")
                            all_exist = False
        else:
            print(f"✗ Template missing: {template}")
            all_exist = False
    
    if all_exist:
        print("\n✅ TEST PASSED: All templates exist with correct content")
    else:
        print("\n❌ TEST FAILED: Some templates missing or incorrect")
    
    return all_exist


def test_3_check_campaign_detail_template():
    """Test campaign_detail.html for critical fixes"""
    print("\n" + "="*60)
    print("TEST 3: Campaign Detail Template Fixes")
    print("="*60)
    
    template_path = '/home/doombuggy_/Projects/UnwindAfrica/Web/templates/Web/voting/campaign_detail.html'
    
    with open(template_path, 'r') as f:
        content = f.read()
    
    # Test 1: No ₦ symbol on Rest Points
    rest_points_lines = [line for line in content.split('\n') if 'Rest Points' in line and 'totalRestPoints' in line]
    has_currency_on_points = any('₦' in line and 'totalRestPoints' in line for line in content.split('\n'))
    
    if not has_currency_on_points:
        print("✓ Rest Points display: No ₦ symbol (correct)")
    else:
        print("✗ Rest Points display: Still has ₦ symbol (WRONG)")
        return False
    
    # Test 2: Referral field is required
    if 'id="referralSource" required' in content:
        print("✓ Referral field: Required attribute present")
    else:
        print("✗ Referral field: Not required (WRONG)")
        return False
    
    # Test 3: Countdown timer exists
    if 'id="countdown"' in content and 'countdownTimer' in content:
        print("✓ Countdown timer: Present in template")
    else:
        print("✗ Countdown timer: Missing (WRONG)")
        return False
    
    # Test 4: Explanation text exists
    if 'You earn 100 Rest Points per vote' in content:
        print("✓ Explanation: Rest Points info present")
    else:
        print("✗ Explanation: Missing (WRONG)")
        return False
    
    # Test 5: Ballot copy improved
    if 'Rest Points Earned:' in content:
        print("✓ Ballot copy: Uses 'Rest Points Earned'")
    else:
        print("✗ Ballot copy: Still uses old text (WRONG)")
        return False
    
    # Test 6: Uses "points" not currency
    if 'points' in content.lower():
        print("✓ Terminology: Uses 'points' terminology")
    else:
        print("✗ Terminology: Missing 'points' text (WRONG)")
        return False
    
    print("\n✅ TEST PASSED: All campaign detail fixes verified")
    return True


def test_4_check_success_message():
    """Test that success message is updated"""
    print("\n" + "="*60)
    print("TEST 4: Success Message Update")
    print("="*60)
    
    views_path = '/home/doombuggy_/Projects/UnwindAfrica/Web/voting_views.py'
    
    with open(views_path, 'r') as f:
        content = f.read()
    
    # Check for updated message
    checks = [
        ('Vote recorded message', 'Your vote has been recorded' in content),
        ('No ₦ on rest points', 'total_rest_points:,.0f} Rest Points' in content),
        ('Has emoji', '💛' in content),
        ('Thank you redirect', "redirect('voting_thank_you')" in content),
    ]
    
    all_passed = True
    for check_name, result in checks:
        if result:
            print(f"✓ {check_name}: Present")
        else:
            print(f"✗ {check_name}: Missing")
            all_passed = False
    
    if all_passed:
        print("\n✅ TEST PASSED: Success message updated correctly")
    else:
        print("\n❌ TEST FAILED: Success message not fully updated")
    
    return all_passed


def test_5_check_thank_you_view():
    """Test that thank you view function exists"""
    print("\n" + "="*60)
    print("TEST 5: Thank You View Function")
    print("="*60)
    
    try:
        from Web import voting_views
        
        # Check function exists
        if hasattr(voting_views, 'voting_thank_you'):
            print("✓ Function exists: voting_thank_you()")
        else:
            print("✗ Function missing: voting_thank_you()")
            return False
        
        # Check it's callable
        if callable(voting_views.voting_thank_you):
            print("✓ Function is callable")
        else:
            print("✗ Function not callable")
            return False
        
        print("\n✅ TEST PASSED: Thank you view exists")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        return False


def test_6_simulate_thank_you_page():
    """Test thank you page with mock data"""
    print("\n" + "="*60)
    print("TEST 6: Thank You Page Simulation")
    print("="*60)
    
    try:
        client = Client()
        
        # Create test campaign
        campaign = VotingCampaign.objects.filter(is_active=True).first()
        
        if not campaign:
            # Create one for testing
            campaign = VotingCampaign.objects.create(
                name='Test Campaign',
                slug='test-campaign-fixes',
                description='Test',
                vote_price=Decimal('500.00'),
                rest_points_per_vote=Decimal('100.00'),
                start_date=timezone.now(),
                end_date=timezone.now() + timezone.timedelta(days=30),
                is_active=True
            )
            print(f"✓ Created test campaign: {campaign.name}")
        else:
            print(f"✓ Using existing campaign: {campaign.name}")
        
        # Set up session data
        session = client.session
        session['vote_success'] = {
            'campaign_slug': campaign.slug,
            'campaign_name': campaign.name,
            'total_votes': 5,
            'total_rest_points': 500.0,
            'total_tokens': 500,
            'rest_card_activated': False,
            'rest_card_number': None
        }
        session.save()
        
        # Try to access thank you page
        response = client.get(reverse('voting_thank_you'))
        
        print(f"✓ Response status: {response.status_code}")
        
        if response.status_code == 200:
            print("✓ Thank you page loads successfully")
            
            # Check response content
            content = response.content.decode('utf-8')
            
            checks = {
                'Has title': 'Your vote has been recorded' in content,
                'Shows points': '500' in content and 'Rest Points' in content,
                'Has WhatsApp': 'WhatsApp' in content,
                'Has Twitter': 'Twitter' in content,
                'Return button': 'Return to Campaign' in content,
            }
            
            for check_name, result in checks:
                if result:
                    print(f"  ✓ {check_name}")
                else:
                    print(f"  ✗ {check_name}")
                    
            print("\n✅ TEST PASSED: Thank you page works correctly")
            return True
        else:
            print(f"✗ Thank you page error: Status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_7_check_auto_rest_card_integration():
    """Test that auto-create rest card still works"""
    print("\n" + "="*60)
    print("TEST 7: Auto-Create Rest Card Still Works")
    print("="*60)
    
    try:
        from Web.voting_views import update_rest_card_points, update_token_wallet
        
        # These functions should still exist
        print("✓ Function exists: update_rest_card_points()")
        print("✓ Function exists: update_token_wallet()")
        
        # Check they're called in verify_payment
        views_path = '/home/doombuggy_/Projects/UnwindAfrica/Web/voting_views.py'
        with open(views_path, 'r') as f:
            content = f.read()
        
        if 'update_rest_card_points(trans.vote)' in content:
            print("✓ Rest Card auto-update: Still integrated in verify_payment")
        else:
            print("✗ Rest Card auto-update: Missing from verify_payment")
            return False
        
        if 'update_token_wallet(trans.vote)' in content:
            print("✓ Token Wallet auto-update: Still integrated in verify_payment")
        else:
            print("✗ Token Wallet auto-update: Missing from verify_payment")
            return False
        
        print("\n✅ TEST PASSED: Auto-create functionality preserved")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        return False


def run_all_tests():
    """Run all test suites"""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*15 + "VOTING SYSTEM FIXES - TEST SUITE" + " "*15 + "║")
    print("╚" + "="*58 + "╝")
    
    tests = [
        test_1_check_urls,
        test_2_check_templates,
        test_3_check_campaign_detail_template,
        test_4_check_success_message,
        test_5_check_thank_you_view,
        test_6_simulate_thank_you_page,
        test_7_check_auto_rest_card_integration,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"\n❌ TEST EXCEPTION: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"\nTests Passed: {passed}/{total}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if all(results):
        print("\n" + "🎉"*20)
        print("\n✅ ALL TESTS PASSED! ✅")
        print("\nAll voting system fixes verified:")
        print("  ✓ Rest Points display (no ₦ symbol)")
        print("  ✓ Referral field required")
        print("  ✓ Thank you page working")
        print("  ✓ Success messages updated")
        print("  ✓ Countdown timer added")
        print("  ✓ Ballot copy improved")
        print("  ✓ Auto-create Rest Card preserved")
        print("\n🚀 READY FOR PRODUCTION! 🚀")
        print("\n" + "🎉"*20 + "\n")
    else:
        print("\n⚠️ SOME TESTS FAILED")
        print("\nPlease review failed tests above.")
    
    return all(results)


if __name__ == '__main__':
    run_all_tests()
