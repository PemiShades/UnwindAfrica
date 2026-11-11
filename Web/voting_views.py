"""
Views for the Nominate to Unwind Voting System
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.db import transaction as db_transaction
from django.db.models import Q
from django.conf import settings
from django.utils.timezone import now
import requests
import json
import secrets
import logging
import hmac
import hashlib
from decimal import Decimal

from .models import VotingCampaign, Nominee, Vote, Transaction, RestCard, TokenWallet, TokenTransaction, FrozenRestPoints

logger = logging.getLogger(__name__)


def _paystack_charge_matches(data, reference, expected_amount):
    """Check the fields that bind a Paystack charge to its local records."""
    try:
        amount_kobo = int(data.get('amount') or 0)
    except (TypeError, ValueError):
        return False
    expected_kobo = int((Decimal(expected_amount) * 100).quantize(Decimal('1')))
    return (
        data.get('status') == 'success'
        and data.get('reference') == reference
        and data.get('currency') == 'NGN'
        and amount_kobo == expected_kobo
    )


@require_http_methods(["POST"])
def verify_rest_card(request):
    """API endpoint to verify Rest Card number or email and check for free vote eligibility"""
    try:
        data = json.loads(request.body)
        # Accept either card_number or email as input
        identifier = data.get('card_number', '').strip()
        
        if not identifier:
            return JsonResponse({
                'valid': False,
                'message': 'Please enter your Rest Card number or email address'
            })
        
        # Determine if input is email or card number
        is_email = '@' in identifier and '.' in identifier
        
        # Normalize card number input - remove dashes and spaces for flexible matching
        # Users can type: UA-0001-ABCD, UA 0001 ABCD, UA0001ABCD, or 0001ABCD
        if not is_email:
            # Remove all non-alphanumeric characters except letters
            normalized_input = ''.join(c for c in identifier.upper() if c.isalnum())
            # If it starts with UA, keep it, otherwise check if it's just the numeric part
            if normalized_input.startswith('UA'):
                search_value = normalized_input
            else:
                # User might just type the numeric part like 0001ABCD - search both patterns
                search_value = normalized_input
        else:
            search_value = identifier
        
        # Look up the Rest Card by card number or email
        if is_email:
            rest_card = RestCard.objects.filter(
                member_email__iexact=identifier,
                status='active'
            ).first()
        else:
            # Try exact match first, then try normalized match
            rest_card = RestCard.objects.filter(
                card_number__iexact=identifier,
                status='active'
            ).first()
            
            # If not found, try normalized search
            if not rest_card:
                # Get all active cards and find match manually (since we need to normalize stored values too)
                active_cards = RestCard.objects.filter(status='active')
                for card in active_cards:
                    if card.card_number:
                        # Normalize stored card number
                        stored_normalized = ''.join(c for c in card.card_number.upper() if c.isalnum())
                        if stored_normalized == search_value:
                            rest_card = card
                            break
        
        if not rest_card:
            # Check if they exist but are not active
            if is_email:
                exists_inactive = RestCard.objects.filter(member_email__iexact=identifier).exists()
            else:
                # For card number, check using normalized comparison
                active_cards = RestCard.objects.all()
                exists_inactive = False
                for card in active_cards:
                    if card.card_number:
                        stored_normalized = ''.join(c for c in card.card_number.upper() if c.isalnum())
                        if stored_normalized == search_value:
                            if card.status != 'active':
                                exists_inactive = True
                            break
            
            if exists_inactive:
                return JsonResponse({
                    'valid': False,
                    'message': 'Your Rest Card is not active. Please contact support or apply for a new card.'
                }, status=400)
            else:
                return JsonResponse({
                    'valid': False,
                    'message': 'No Rest Card found. Please check your details or apply for a Rest Card.'
                }, status=400)
        
        # Check if they have free votes remaining
        if rest_card.free_votes_remaining <= 0:
            return JsonResponse({
                'valid': False,
                'message': 'You have already used your free vote. You can still vote by paying ₦500 per vote.'
                ,
                'exhausted_free_vote': True,
                'member_name': rest_card.member_name,
                'card_number': rest_card.card_number
            })
        
        # Card is valid and has free votes
        return JsonResponse({
            'valid': True,
            'message': 'Card verified! You have 1 free vote available.',
            'free_votes': rest_card.free_votes_remaining,
            'member_name': rest_card.member_name,
            'card_number': rest_card.card_number
        })
        
    except Exception as e:
        print(f"Error verifying rest card: {e}")
        return JsonResponse({
            'valid': False,
            'message': 'Something went wrong. Please try again.'
        }, status=500)


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
    can_nominate = is_ongoing and (
        not campaign.nomination_deadline or current_time <= campaign.nomination_deadline
    )
    
    context = {
        'campaign': campaign,
        'nominees': nominees,
        'leaderboard': leaderboard,
        'vote_price': campaign.vote_price,
        'rest_points_per_vote': campaign.rest_points_per_vote,
        'is_ongoing': is_ongoing,  # Explicitly pass
        'can_nominate': can_nominate,
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
        rest_card_number = data.get('rest_card_number', '').strip()  # Rest Card number from checkout form
        
        # Validation
        if not ballot or not voter_name or not voter_email or not voter_phone:
            return JsonResponse({
                'success': False,
                'message': 'Missing required fields'
            }, status=400)
        
        # Check for free votes from Rest Card
        # Priority: 1. Look up by card number if provided, 2. Look up by email
        free_votes_available = 0
        rest_card = None
        try:
            # First, try to find by card number (if provided in checkout form)
            if rest_card_number:
                rest_card = RestCard.objects.filter(
                    card_number__iexact=rest_card_number,
                    status='active',
                    free_votes_remaining__gt=0
                ).first()
            
            # If not found by card number, try by email
            if not rest_card:
                rest_card = RestCard.objects.filter(
                    member_email__iexact=voter_email,
                    status='active',
                    free_votes_remaining__gt=0
                ).first()
            
            if rest_card:
                free_votes_available = rest_card.free_votes_remaining
        except Exception:
            pass  # If check fails, proceed without free votes
        
        # Process ballot and create votes
        votes_created = []
        total_amount = Decimal('0.00')
        free_votes_used = 0
        
        # Don't create votes yet - we'll do it after successful payment initialization
        ballot_items = []
        
        for item in ballot:
            nominee_id = item.get('nominee_id')
            vote_quantity = int(item.get('votes', 0))
            
            # Validate nominee_id
            if not nominee_id or nominee_id == 'undefined' or nominee_id == 'null':
                print(f"ERROR: Invalid nominee_id: {nominee_id}")
                continue
            
            try:
                nominee_id = int(nominee_id)
            except (ValueError, TypeError):
                print(f"ERROR: Could not convert nominee_id to int: {nominee_id}")
                continue
            
            if vote_quantity <= 0:
                continue
            
            nominee = get_object_or_404(Nominee, id=nominee_id)
            campaign = nominee.campaign
            
            # Calculate amount - apply free votes first
            votes_remaining = vote_quantity
            amount = Decimal('0.00')
            
            # Use free votes first
            if free_votes_available > 0 and free_votes_used < free_votes_available:
                free_votes_for_this_item = min(votes_remaining, free_votes_available - free_votes_used)
                free_votes_used += free_votes_for_this_item
                votes_remaining -= free_votes_for_this_item
            
            # Calculate paid amount for remaining votes
            if votes_remaining > 0:
                amount = campaign.vote_price * votes_remaining
            
            total_amount += amount
            
            ballot_items.append({
                'nominee': nominee,
                'vote_quantity': vote_quantity,
                'free_votes': vote_quantity - votes_remaining,
                'paid_votes': votes_remaining,
                'amount': amount
            })
        
        if not ballot_items:
            # Log the ballot for debugging
            print(f"DEBUG: Empty ballot_items. Original ballot: {ballot}")
            return JsonResponse({
                'success': False,
                'message': 'No valid votes in ballot. Please select at least one nominee and vote amount.'
            }, status=400)
        
        # Generate unique reference for the entire payment
        reference = f"NTU-{secrets.token_urlsafe(16)}"
        
        # Initialize Paystack payment (only if there are paid votes)
        paystack_secret = settings.PAYSTACK_SECRET_KEY
        
        # If total amount is 0 and we have free votes, skip Paystack entirely
        if total_amount == Decimal('0.00') and free_votes_used > 0:
            # Process free votes directly - no payment needed
            reference = f"NTU-FREE-{secrets.token_urlsafe(16)}"
            
            # Create votes and transactions
            created_votes = []
            created_transactions = []
            
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
                        amount=item['amount'],
                        payment_status='paid'  # Mark as paid since it's free
                    )
                    created_votes.append(vote)
                    
                    # Create transaction (marked as paid since it's free)
                    transaction = Transaction.objects.create(
                        vote=vote,
                        reference=reference,
                        authorization_url='',
                        access_code='',
                        amount=item['amount'],
                        status='success'  # Mark as success since it's free
                    )
                    created_transactions.append(transaction)
                    
                    # Update nominee vote count
                    nominee = item['nominee']
                    nominee.vote_count += item['vote_quantity']
                    nominee.save()
                    
                    # Update rest card points for this vote
                    if vote.rest_points_earned > 0:
                        update_rest_card_points(vote)
                
                # Decrement free votes on rest card
                if rest_card:
                    rest_card.free_votes_remaining = max(0, rest_card.free_votes_remaining - free_votes_used)
                    rest_card.save()
            
            # Return success response for free votes
            return JsonResponse({
                'success': True,
                'free_votes_used': free_votes_used,
                'free_votes_remaining': rest_card.free_votes_remaining if rest_card else 0,
                'total_amount': 0,
                'message': f'Your {free_votes_used} free vote(s) have been applied!',
                'thank_you_url': '/voting/payment/thank-you/',
                'free_votes_processed': True
            })
        
        # Regular paid payment flow
        if not paystack_secret:
            return JsonResponse({
                'success': False,
                'message': 'Payment gateway not configured. Please contact support.'
            }, status=500)
        
        # Convert to kobo (Paystack uses kobo for Naira)
        amount_in_kobo = int(total_amount * 100)
        
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
            verify=True,
            timeout=10
        )
        
        response_data = response.json()
        
        # Collect votes and transactions for processing
        created_votes = []
        created_transactions = []
        
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
                    created_votes.append(vote)
                    
                    # Create transaction for this vote
                    transaction = Transaction.objects.create(
                        vote=vote,
                        reference=reference,  # Same reference for all votes in this payment
                        authorization_url=response_data['data']['authorization_url'],
                        access_code=response_data['data']['access_code'],
                        amount=item['amount'],
                        status='pending',
                        paystack_response=response_data
                    )
                    created_transactions.append(transaction)
            
            # Return success response with free votes info
            response_payload = {
                'success': True,
                'authorization_url': response_data['data']['authorization_url'],
                'reference': reference,
                'free_votes_used': free_votes_used,
                'free_votes_remaining': rest_card.free_votes_remaining - free_votes_used if rest_card else 0,
                'total_amount': float(total_amount)
            }
            
            # If all votes are free (total_amount is 0), skip payment and process directly
            if total_amount == Decimal('0.00') and free_votes_used > 0:
                # Mark transactions as paid and process votes
                for trans in created_transactions:
                    trans.status = 'paid'
                    trans.payment_status = 'paid'
                    trans.save()
                    
                    # Update vote status
                    vote = trans.vote
                    vote.payment_status = 'paid'
                    vote.save()
                    
                    # Update nominee vote count
                    nominee = vote.nominee
                    nominee.vote_count += vote.vote_quantity
                    nominee.save()
                
                # Decrement free votes on rest card
                if rest_card:
                    rest_card.free_votes_remaining = max(0, rest_card.free_votes_remaining - free_votes_used)
                    rest_card.save()
                
                response_payload['free_votes_processed'] = True
                response_payload['message'] = f'Your {free_votes_used} free vote(s) have been applied!'
                # Add thank you URL for redirect
                response_payload['thank_you_url'] = '/voting/payment/thank-you/'
            
            return JsonResponse(response_payload)
        else:
            # Payment initialization failed - no cleanup needed since votes weren't created yet
            return JsonResponse({
                'success': False,
                'message': response_data.get('message', 'Payment initialization failed')
            }, status=400)
    
    except Exception:
        logger.exception('Unable to initialize voting payment')
        return JsonResponse({
            'success': False,
            'message': 'Unable to start payment. Please try again shortly.'
        }, status=500)


def update_rest_card_points(vote):
    """
    Store earned rest points - either directly to Rest Card (if user has one)
    or as "frozen" points (if user doesn't have a card yet).
    """
    email = vote.voter_email
    name = vote.voter_name
    phone = vote.voter_phone
    points = vote.rest_points_earned
    
    # Check if user already has an active Rest Card
    rest_card = RestCard.objects.filter(
        member_email__iexact=email,
        status='active'
    ).first()
    
    if rest_card:
        # User has a Rest Card - directly add points to their total
        rest_card.total_rest_points += points
        rest_card.save()
        return None, False  # Not frozen, directly credited
    
    # No Rest Card - store as frozen points for later claim
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
    """Verify a vote charge with Paystack before awarding votes or points."""
    try:
        transactions = Transaction.objects.filter(reference=reference).select_related(
            'vote__nominee__campaign'
        )
        if not transactions.exists():
            messages.error(request, 'Transaction not found')
            return redirect('voting_campaigns_list')

        paystack_secret = settings.PAYSTACK_SECRET_KEY
        if not paystack_secret:
            messages.error(request, 'Payment verification is temporarily unavailable.')
            return redirect('voting_campaigns_list')
        response = requests.get(
            f'https://api.paystack.co/transaction/verify/{reference}',
            headers={'Authorization': f'Bearer {paystack_secret}'},
            timeout=10,
        )
        response_data = response.json()
        expected_amount = sum((item.amount for item in transactions), Decimal('0'))
        data = response_data.get('data') or {}
        if not (response.ok and response_data.get('status')
                and _paystack_charge_matches(data, reference, expected_amount)):
            messages.error(request, 'Payment was not successful or could not be verified.')
            return redirect('voting_campaigns_list')

        with db_transaction.atomic():
            for transaction_row in transactions.select_for_update():
                if transaction_row.status == 'success':
                    continue
                transaction_row.status = 'success'
                transaction_row.paid_at = now()
                transaction_row.paystack_reference = data.get('reference', reference)
                transaction_row.paystack_response = response_data
                transaction_row.save(update_fields=[
                    'status', 'paid_at', 'paystack_reference', 'paystack_response',
                ])

                vote = transaction_row.vote
                vote.payment_status = 'paid'
                vote.save(update_fields=['payment_status'])
                nominee = Nominee.objects.select_for_update().get(pk=vote.nominee_id)
                nominee.vote_count += vote.vote_quantity
                nominee.save(update_fields=['vote_count'])
                update_rest_card_points(vote)
                update_token_wallet(vote)

        total_votes = sum(item.vote.vote_quantity for item in transactions)
        total_rest_points = sum((item.vote.rest_points_earned for item in transactions), Decimal('0'))
        total_tokens = total_votes * 100
        first_vote = transactions.first().vote
        request.session['vote_success'] = {
            'campaign_slug': first_vote.nominee.campaign.slug,
            'campaign_name': first_vote.nominee.campaign.name,
            'total_votes': total_votes,
            'total_rest_points': float(total_rest_points),
            'total_tokens': total_tokens,
            'rest_card_activated': False,
            'rest_card_number': None,
            'has_frozen_points': True,
            'frozen_points': float(total_rest_points),
        }
        messages.success(request, f'Your vote has been recorded. You voted {total_votes} times.')
        return redirect('voting_thank_you')
    except (requests.RequestException, ValueError):
        logger.exception('Unable to verify voting payment with Paystack')
        messages.error(request, 'Unable to reach the payment service. Please try again shortly.')
        return redirect('voting_campaigns_list')
    except Exception:
        logger.exception('Unable to process verified voting payment')
        messages.error(request, 'Unable to verify your payment right now. Please contact support if you were charged.')
        return redirect('voting_campaigns_list')


def paystack_webhook(request):
    """Verify signed Paystack events and reconcile vote/package payments once."""
    paystack_secret = settings.PAYSTACK_SECRET_KEY
    if not paystack_secret:
        return HttpResponse('Payment webhook is not configured', status=503)

    signature = request.headers.get('X-Paystack-Signature', '')
    expected_signature = hmac.new(
        paystack_secret.encode('utf-8'), request.body, hashlib.sha512
    ).hexdigest()
    if not signature or not hmac.compare_digest(signature, expected_signature):
        return HttpResponse('Invalid signature', status=400)

    try:
        payload = json.loads(request.body)
    except (TypeError, json.JSONDecodeError):
        return HttpResponse('Invalid payload', status=400)
    if payload.get('event') != 'charge.success':
        return HttpResponse('OK', status=200)

    data = payload.get('data') or {}
    reference = data.get('reference')
    if not reference:
        return HttpResponse('Missing reference', status=400)

    # The same Paystack webhook reconciles package deposits and installments.
    from .models import PackagePayment
    from .views import _confirm_package_payment, _send_package_dashboard_password
    package_payment = PackagePayment.objects.filter(
        Q(reference=reference) | Q(paystack_reference=reference)
    ).select_related('order').first()
    if package_payment:
        order, newly_confirmed = _confirm_package_payment(
            package_payment, payload, data
        )
        if not order:
            return HttpResponse('Payment details did not match the order', status=400)
        if newly_confirmed and package_payment.is_initial_deposit:
            _send_package_dashboard_password(order.customer_email, order.customer_name)
        return HttpResponse('OK', status=200)

    transactions = Transaction.objects.filter(reference=reference).select_related(
        'vote__nominee__campaign'
    )
    if not transactions.exists():
        # A valid event can arrive before the application stores its record.
        # Acknowledge it; the browser callback can still verify by reference.
        return HttpResponse('OK', status=200)
    expected_amount = sum((item.amount for item in transactions), Decimal('0'))
    if not _paystack_charge_matches(data, reference, expected_amount):
        return HttpResponse('Payment details did not match the vote', status=400)

    with db_transaction.atomic():
        for transaction_row in transactions.select_for_update():
            if transaction_row.status == 'success':
                continue
            transaction_row.status = 'success'
            transaction_row.paid_at = now()
            transaction_row.paystack_reference = reference
            transaction_row.paystack_response = payload
            transaction_row.save(update_fields=[
                'status', 'paid_at', 'paystack_reference', 'paystack_response',
            ])

            vote = transaction_row.vote
            vote.payment_status = 'paid'
            vote.save(update_fields=['payment_status'])
            nominee = Nominee.objects.select_for_update().get(pk=vote.nominee_id)
            nominee.vote_count += vote.vote_quantity
            nominee.save(update_fields=['vote_count'])
            update_rest_card_points(vote)
            update_token_wallet(vote)

    return HttpResponse('OK', status=200)


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
