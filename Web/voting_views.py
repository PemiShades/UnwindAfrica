"""
Views for the Nominate to Unwind Voting System
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.db import transaction as db_transaction
from django.conf import settings
from django.utils.timezone import now
import requests
import json
import secrets
import traceback
from decimal import Decimal

from .models import VotingCampaign, Nominee, Vote, Transaction, RestCard, TokenWallet, TokenTransaction, FrozenRestPoints


def voting_campaigns_list(request):
    """List all active voting campaigns"""
    campaigns = VotingCampaign.objects.filter(is_active=True).order_by('-start_date')
    
    context = {
        'campaigns': campaigns,
        'ongoing_campaigns': [c for c in campaigns if c.is_ongoing]
    }
    return render(request, 'Web/voting/campaigns_list.html', context)


def voting_campaign_detail(request, slug):
    """Display voting page for a specific campaign"""
    campaign = get_object_or_404(VotingCampaign, slug=slug, is_active=True)
    nominees = campaign.nominees.all().order_by('order', '-vote_count')
    
    # Get search query
    search_query = request.GET.get('search', '').strip()
    
    # Get filter query (by vote count range)
    vote_filter = request.GET.get('filter', '')
    
    # Apply search filter
    if search_query:
        nominees = nominees.filter(name__icontains=search_query)
    
    # Apply vote count filters
    if vote_filter == 'top_rated':
        nominees = nominees.order_by('-vote_count')
    elif vote_filter == 'lowest':
        nominees = nominees.order_by('vote_count')
    elif vote_filter == 'newest':
        nominees = nominees.order_by('-created_at')
    elif vote_filter == 'oldest':
        nominees = nominees.order_by('created_at')
    else:
        nominees = nominees.order_by('order', '-vote_count')
    
    # Get leaderboard (top 3)
    leaderboard = campaign.nominees.all().order_by('-vote_count')[:3]
    
    # Determine if campaign is ongoing (use fresh query)
    from django.utils.timezone import now as get_now
    current_time = get_now()
    is_ongoing = campaign.is_active and campaign.start_date <= current_time <= campaign.end_date
    
    context = {
        'campaign': campaign,
        'nominees': nominees,
        'leaderboard': leaderboard,
        'vote_price': campaign.vote_price,
        'rest_points_per_vote': campaign.rest_points_per_vote,
        'is_ongoing': is_ongoing,  # Explicitly pass
        'search_query': search_query,
        'vote_filter': vote_filter,
    }
    return render(request, 'Web/voting/campaign_detail.html', context)


@require_http_methods(["POST"])
def initialize_payment(request):
    """Initialize Paystack payment for votes"""
    try:
        # Get form data
        data = json.loads(request.body)
        
        # Extract ballot (multiple nominees with vote counts)
        ballot = data.get('ballot', [])  # [{nominee_id: X, votes: Y}, ...]
        voter_name = data.get('voter_name', '').strip()
        voter_email = data.get('voter_email', '').strip()
        voter_phone = data.get('voter_phone', '').strip()
        referral_source = data.get('referral_source', '').strip()
        
        # Validation
        if not ballot or not voter_name or not voter_email or not voter_phone:
            return JsonResponse({
                'success': False,
                'message': 'Missing required fields'
            }, status=400)
        
        # Process ballot and create votes
        votes_created = []
        total_amount = Decimal('0.00')
        
        # Don't create votes yet - we'll do it after successful payment initialization
        ballot_items = []
        
        for item in ballot:
            nominee_id = item.get('nominee_id')
            vote_quantity = int(item.get('votes', 0))
            
            if vote_quantity <= 0:
                continue
            
            nominee = get_object_or_404(Nominee, id=nominee_id)
            campaign = nominee.campaign
            
            # Calculate amount
            amount = campaign.vote_price * vote_quantity
            total_amount += amount
            
            ballot_items.append({
                'nominee': nominee,
                'vote_quantity': vote_quantity,
                'amount': amount
            })
        
        if not ballot_items:
            return JsonResponse({
                'success': False,
                'message': 'No valid votes in ballot'
            }, status=400)
        
        # Generate unique reference for the entire payment
        reference = f"NTU-{secrets.token_urlsafe(16)}"
        
        # Initialize Paystack payment
        paystack_secret = settings.PAYSTACK_SECRET_KEY
        
        # print(f"DEBUG: PAYSTACK_SECRET_KEY present: {bool(paystack_secret)}")
        # print(f"DEBUG: PAYSTACK_SECRET_KEY value: {paystack_secret[:10]}..." if paystack_secret else "DEBUG: PAYSTACK_SECRET_KEY is empty")
        
        if not paystack_secret:
            return JsonResponse({
                'success': False,
                'message': 'Payment gateway not configured. Please contact support.'
            }, status=500)
        
        # Convert to kobo (Paystack uses kobo for Naira)
        amount_in_kobo = int(total_amount * 100)
        
        print(f"DEBUG: total_amount={total_amount}, amount_in_kobo={amount_in_kobo}")
        print(f"DEBUG: voter_email={voter_email}, voter_name={voter_name}")
        
        headers = {
            'Authorization': f'Bearer {paystack_secret}',
            'Content-Type': 'application/json',
        }
        
        
        payload = {
            'email': voter_email,
            'amount': amount_in_kobo,
            'reference': reference,
            'callback_url': request.build_absolute_uri(f'/voting/payment/verify/{reference}/'),
            'metadata': {
                'voter_name': voter_name,
                'voter_phone': voter_phone,
                'vote_count': sum(item['vote_quantity'] for item in ballot_items),
                'custom_fields': [
                    {
                        'display_name': 'Voter Name',
                        'variable_name': 'voter_name',
                        'value': voter_name
                    }
                ]
            }
        }
        
        response = requests.post(
            'https://api.paystack.co/transaction/initialize',
            headers=headers,
            json=payload,
            verify=False,  # Disable SSL verification for local testing (remove in production)
            timeout=10
        )
        
        print(f"DEBUG: Paystack response status: {response.status_code}")
        print(f"DEBUG: Paystack response body: {response.text[:500]}")
        
        response_data = response.json()
        
        if response.status_code == 200 and response_data.get('status'):
            # Now create votes and transactions atomically
            with db_transaction.atomic():
                for item in ballot_items:
                    # Create vote record
                    vote = Vote.objects.create(
                        nominee=item['nominee'],
                        voter_name=voter_name,
                        voter_email=voter_email,
                        voter_phone=voter_phone,
                        referral_source=referral_source,
                        vote_quantity=item['vote_quantity'],
                        amount=item['amount']
                    )
                    
                    # Create transaction for this vote
                    Transaction.objects.create(
                        vote=vote,
                        reference=reference,  # Same reference for all votes in this payment
                        authorization_url=response_data['data']['authorization_url'],
                        access_code=response_data['data']['access_code'],
                        amount=item['amount'],
                        status='pending',
                        paystack_response=response_data
                    )
            
            return JsonResponse({
                'success': True,
                'authorization_url': response_data['data']['authorization_url'],
                'reference': reference
            })
        else:
            # Payment initialization failed - no cleanup needed since votes weren't created yet
            return JsonResponse({
                'success': False,
                'message': response_data.get('message', 'Payment initialization failed')
            }, status=400)
    
    except Exception as e:
        # Print full traceback for debugging
        print("="*50)
        print("ERROR in initialize_payment:")
        print(traceback.format_exc())
        print("="*50)
        
        return JsonResponse({
            'success': False,
            'message': f'Error: {str(e)}'
        }, status=500)


def update_rest_card_points(vote):
    """
    Store earned rest points as "frozen" - these will be transferred to 
    the user's Rest Card when they apply and receive one.
    
    Users are NOT automatically added to waitlist anymore. They must apply
    for a Rest Card to claim their frozen points.
    """
    email = vote.voter_email
    name = vote.voter_name
    phone = vote.voter_phone
    points = vote.rest_points_earned
    
    # Create frozen points entry (NOT added to waitlist automatically)
    frozen_entry, created = FrozenRestPoints.objects.get_or_create(
        member_email=email,
        defaults={
            'member_name': name,
            'member_phone': phone,
            'frozen_points': 0,
            'vote': vote,
        }
    )
    
    # Add the new points to the frozen balance
    frozen_entry.frozen_points += points
    frozen_entry.vote = vote  # Update to latest vote
    frozen_entry.save()
    
    return frozen_entry, created


def update_token_wallet(vote):
    """
    Update Token Wallet with earned tokens.
    Called after successful payment verification.
    Tokens earned: 100 tokens per vote
    """
    email = vote.voter_email
    name = vote.voter_name
    tokens = vote.vote_quantity * 100  # 100 tokens per vote
    
    # Get or create wallet
    wallet, created = TokenWallet.objects.get_or_create(
        member_email=email,
        defaults={
            'member_name': name,
            'tokens_earned': 0,
            'tokens_used': 0
        }
    )
    
    # Add tokens
    wallet.tokens_earned += tokens
    wallet.save()
    
    # Log transaction
    TokenTransaction.objects.create(
        wallet=wallet,
        transaction_type='earn',
        amount=tokens,
        description=f"Voted {vote.vote_quantity} times for {vote.nominee.name}",
        reference_id=f"VOTE-{vote.id}"
    )
    
    return wallet, created


def verify_payment(request, reference):
    """Verify payment and update vote counts"""
    try:
        # Get all transactions with this reference
        transactions = Transaction.objects.filter(reference=reference)
        
        if not transactions.exists():
            messages.error(request, 'Transaction not found')
            return redirect('voting_campaigns_list')
        
        first_transaction = transactions.first()
        
        # Verify with Paystack
        paystack_secret = settings.PAYSTACK_SECRET_KEY
        headers = {
            'Authorization': f'Bearer {paystack_secret}',
        }
        
        response = requests.get(
            f'https://api.paystack.co/transaction/verify/{reference}',
            headers=headers,
            timeout=10
        )
        
        response_data = response.json()
        
        if response.status_code == 200 and response_data.get('status'):
            data = response_data['data']
            
            if data['status'] == 'success':
                # Update all transactions and vote counts
                with db_transaction.atomic():
                    for trans in transactions:
                        if trans.status != 'success':  # Only update if not already successful
                            trans.status = 'success'
                            trans.paid_at = now()
                            trans.paystack_reference = data.get('reference')
                            trans.paystack_response = response_data
                            trans.save()
                            
                            # Increment nominee vote count
                            nominee = trans.vote.nominee
                            nominee.vote_count += trans.vote.vote_quantity
                            nominee.save()
                            
                            # ✨ Auto-create/update Rest Card with earned points
                            update_rest_card_points(trans.vote)
                            
                            # ✨ Update Token Wallet with earned tokens
                            update_token_wallet(trans.vote)
                
                # Calculate totals for success message
                total_votes = sum(t.vote.vote_quantity for t in transactions)
                total_rest_points = sum(t.vote.rest_points_earned for t in transactions)
                total_tokens = total_votes * 100
                
                # Check if user has frozen points
                first_vote = transactions.first().vote
                frozen_points = FrozenRestPoints.objects.filter(member_email=first_vote.voter_email).first()
                
                # Build success message
                success_msg = f'Your vote has been recorded! 💛 You voted {total_votes} times.'
                success_msg += f' You earned {total_rest_points:,.0f} Rest Points (frozen)'
                success_msg += f' and {total_tokens:,.0f} Tokens!'
                
                # Show message about applying for rest card
                success_msg += ' 📋 Apply for a Rest Card to unlock your frozen points!'
                
                messages.success(request, success_msg)
                
                # Get campaign for redirect
                campaign = transactions.first().vote.nominee.campaign
                
                # Store data in session for thank you page
                request.session['vote_success'] = {
                    'campaign_slug': campaign.slug,
                    'campaign_name': campaign.name,
                    'total_votes': total_votes,
                    'total_rest_points': float(total_rest_points),
                    'total_tokens': total_tokens,
                    'rest_card_activated': False,  # No longer auto-activated
                    'rest_card_number': None,
                    'has_frozen_points': True,  # New: indicates user has frozen points
                    'frozen_points': float(total_rest_points),
                }
                
                # Redirect to thank you page
                return redirect('voting_thank_you')
            else:
                # Payment failed
                for trans in transactions:
                    trans.status = 'failed'
                    trans.save()
                
                messages.error(request, 'Payment was not successful. Please try again.')
                return redirect('voting_campaigns_list')
        else:
            messages.error(request, 'Unable to verify payment. Please contact support.')
            return redirect('voting_campaigns_list')
    
    except Exception as e:
        messages.error(request, f'Error verifying payment: {str(e)}')
        return redirect('voting_campaigns_list')


@csrf_exempt
@require_http_methods(["POST"])
def paystack_webhook(request):
    """Handle Paystack webhook for payment notifications"""
    try:
        # Verify webhook signature
        paystack_secret = settings.PAYSTACK_SECRET_KEY
        signature = request.headers.get('X-Paystack-Signature', '')
        
        import hmac
        import hashlib
        
        computed_signature = hmac.new(
            paystack_secret.encode('utf-8'),
            request.body,
            hashlib.sha512
        ).hexdigest()
        
        if signature != computed_signature:
            return HttpResponse('Invalid signature', status=400)
        
        # Process webhook
        payload = json.loads(request.body)
        event = payload.get('event')
        
        if event == 'charge.success':
            data = payload['data']
            reference = data['reference']
            
            # Update transactions
            transactions = Transaction.objects.filter(reference=reference)
            
            with db_transaction.atomic():
                for trans in transactions:
                    if trans.status != 'success':
                        trans.status = 'success'
                        trans.paid_at = now()
                        trans.paystack_reference = reference
                        trans.paystack_response = payload
                        trans.save()
                        
                        # Increment vote count
                        nominee = trans.vote.nominee
                        nominee.vote_count += trans.vote.vote_quantity
                        nominee.save()
                        
                        # ✨ Auto-create/update Rest Card with earned points
                        update_rest_card_points(trans.vote)
                        
                        # ✨ Update Token Wallet with earned tokens
                        update_token_wallet(trans.vote)
        
        return HttpResponse('OK', status=200)
    
    except Exception as e:
        return HttpResponse(f'Error: {str(e)}', status=500)


def voting_thank_you(request):
    """Thank you page after successful payment"""
    # Get data from session
    vote_data = request.session.get('vote_success')
    
    if not vote_data:
        # No session data, redirect to campaigns list
        messages.info(request, 'No recent vote found')
        return redirect('voting_campaigns_list')
    
    # Get campaign
    campaign = get_object_or_404(VotingCampaign, slug=vote_data['campaign_slug'])
    
    # Prepare share text
    share_text = f"I just voted in {vote_data['campaign_name']} on Unwind Africa! Join me in supporting your favorite nominee."
    campaign_url = request.build_absolute_uri(campaign.get_absolute_url())
    
    # Prepare rest card info
    rest_card = None
    if vote_data['rest_card_activated']:
        rest_card = RestCard.objects.filter(card_number=vote_data['rest_card_number']).first()
    
    context = {
        'campaign': campaign,
        'total_votes': vote_data['total_votes'],
        'total_rest_points': vote_data['total_rest_points'],
        'total_tokens': vote_data['total_tokens'],
        'rest_card_activated': vote_data['rest_card_activated'],
        'rest_card': rest_card,
        'share_text': share_text,
        'campaign_url': campaign_url,
    }
    
    # Clear session data after use
    if 'vote_success' in request.session:
        del request.session['vote_success']
    
    return render(request, 'Web/voting/thank_you.html', context)
