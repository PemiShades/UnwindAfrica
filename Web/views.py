from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.utils import timezone
from django.utils.timezone import now
from django.db.models import Q, Count, Sum
from django.db.models.functions import TruncMonth
from django.views.decorators.http import require_POST
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt
from django.templatetags.static import static as static_url
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
import json
import logging
import requests
import secrets

from .models import Post, Event, BlogCategory
from .forms import PostForm, EventForm

logger = logging.getLogger(__name__)


PACKAGE_ARTWORK = {
    'classic': 'assets/packages/11d3b59cfc4cb172640087f3bb9404c8.jpg',
    'paradise': 'assets/packages/2148141989.jpg',
    'imperial': 'assets/packages/boat-cruize-3.jpeg',
    'family-break-beach-day': 'assets/home/packages/family-ties.jpg',
    'oasis': 'assets/packages/46001 1.jpg',
    'oakwood': 'assets/packages/47a0d81bb8958003bb72b7a1b94eadaa.jpg',
}


def _package_artwork_url(package):
    if package.flyer:
        return package.flyer.url
    artwork = PACKAGE_ARTWORK.get(package.slug, 'assets/packages/group-getaway.jpeg')
    return static_url(artwork)


def _paystack_charge_matches(data, reference, expected_amount):
    """Bind a successful Paystack response to the requested NGN charge."""
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


@require_GET
def mobile_packages_api(request):
    """Public, read-only getaway package feed for the React Native client."""
    from .models import GroupGetawayPackage
    rows = GroupGetawayPackage.objects.filter(is_active=True).order_by(
        'category', 'experience_duration', 'price_per_person'
    )
    return JsonResponse({
        'results': [{
            'id': package.pk,
            'name': package.name,
            'slug': package.slug,
            'category': package.category,
            'category_label': package.get_category_display(),
            'duration_label': package.get_experience_duration_display(),
            'pricing_basis': package.get_pricing_basis_display(),
            'price': str(package.price_per_person),
            'description': package.short_description or package.description,
            'inclusions': package.inclusions,
        } for package in rows],
    })


@require_GET
def mobile_voting_campaigns_api(request):
    """Read-only live campaign and nominee data for the native mobile client."""
    from .models import VotingCampaign
    campaigns = VotingCampaign.objects.filter(is_active=True).prefetch_related('nominees').order_by('-start_date')
    return JsonResponse({'results': [{
        'id': campaign.pk,
        'name': campaign.name,
        'slug': campaign.slug,
        'tagline': campaign.tagline,
        'description': campaign.description,
        'vote_price': str(campaign.vote_price),
        'start_date': campaign.start_date.isoformat(),
        'end_date': campaign.end_date.isoformat(),
        'total_votes': campaign.total_votes,
        'nominees': [{
            'id': nominee.pk,
            'name': nominee.name,
            'number': nominee.number,
            'story': nominee.story,
            'vote_count': nominee.vote_count,
            'photo': request.build_absolute_uri(nominee.photo.url) if nominee.photo else '',
        } for nominee in campaign.nominees.all()],
    } for campaign in campaigns]})


@csrf_exempt
@require_POST
def mobile_request_login_code(request):
    """Send a one-time code to an existing Unwind Africa member."""
    from django.contrib.auth.hashers import make_password
    from django.core.cache import cache
    from django.core.mail import send_mail
    from django.http import JsonResponse
    from django.utils import timezone
    from .models import (
        CommunityMember, FrozenRestPoints, MobileLoginChallenge,
        PackageOrder, RestCard, TokenWallet, Vote,
    )

    try:
        data = json.loads(request.body or '{}')
    except (TypeError, json.JSONDecodeError):
        return JsonResponse({'success': False, 'error': 'Invalid request.'}, status=400)
    email = str(data.get('email', '')).strip().lower()
    if not email or '@' not in email:
        return JsonResponse({'success': False, 'error': 'Enter a valid email address.'}, status=400)

    known_member = (
        CommunityMember.objects.filter(email__iexact=email).exists()
        or RestCard.objects.filter(member_email__iexact=email).exists()
        or FrozenRestPoints.objects.filter(member_email__iexact=email).exists()
        or TokenWallet.objects.filter(member_email__iexact=email).exists()
        or Vote.objects.filter(voter_email__iexact=email).exists()
        or PackageOrder.objects.filter(customer_email__iexact=email).exists()
    )
    if not known_member:
        return JsonResponse({'success': False, 'error': 'This email is not connected to an Unwind Africa account.'}, status=404)

    throttle_key = 'mobile-login-code:' + email
    if not cache.add(throttle_key, '1', timeout=60):
        return JsonResponse({'success': False, 'error': 'Please wait a minute before requesting another code.'}, status=429)

    now_value = timezone.now()
    challenge = MobileLoginChallenge.objects.filter(email=email).first()
    if challenge and not challenge.is_used and challenge.updated_at > now_value - timedelta(seconds=60):
        return JsonResponse({'success': False, 'error': 'Please wait a minute before requesting another code.'}, status=429)

    code = f'{secrets.randbelow(1_000_000):06d}'
    MobileLoginChallenge.objects.update_or_create(
        email=email,
        defaults={
            'code_hash': make_password(code),
            'expires_at': now_value + timedelta(minutes=10),
            'attempts': 0,
            'is_used': False,
        },
    )
    try:
        send_mail(
            'Your Unwind Africa sign-in code',
            f'Your sign-in code is {code}. It expires in 10 minutes. If you did not request this, you can ignore this email.',
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
    except Exception:
        logger.exception('Unable to send mobile sign-in code')
        MobileLoginChallenge.objects.filter(email=email).update(is_used=True)
        return JsonResponse({'success': False, 'error': 'We could not deliver your code. Please try again shortly.'}, status=503)
    return JsonResponse({'success': True})


@csrf_exempt
@require_POST
def mobile_verify_login_code(request):
    """Exchange an email code for a signed, expiring bearer token."""
    from django.contrib.auth.hashers import check_password
    from django.core import signing
    from django.http import JsonResponse
    from django.utils import timezone
    from .models import MobileLoginChallenge

    try:
        data = json.loads(request.body or '{}')
    except (TypeError, json.JSONDecodeError):
        return JsonResponse({'success': False, 'error': 'Invalid request.'}, status=400)
    email = str(data.get('email', '')).strip().lower()
    code = str(data.get('code', '')).strip()
    challenge = MobileLoginChallenge.objects.filter(email=email, is_used=False).first()
    if not challenge or challenge.expires_at <= timezone.now() or challenge.attempts >= 5:
        return JsonResponse({'success': False, 'error': 'Code expired. Request a new one.'}, status=400)

    challenge.attempts += 1
    challenge.save(update_fields=['attempts', 'updated_at'])
    if len(code) != 6 or not code.isdigit() or not check_password(code, challenge.code_hash):
        return JsonResponse({'success': False, 'error': 'Invalid verification code.'}, status=400)

    challenge.is_used = True
    challenge.save(update_fields=['is_used', 'updated_at'])
    signer = signing.TimestampSigner(salt='unwind.mobile.auth')
    token = signer.sign(email)
    return JsonResponse({'success': True, 'token': token, 'expires_in': 2592000})


@require_GET
def mobile_dashboard_api(request):
    """Return only the signed-in member's getaway orders and savings totals."""
    from django.core import signing
    from django.db.models import Sum
    from django.http import JsonResponse
    from .models import CommunityMember, FrozenRestPoints, PackageOrder, RestCard, TokenWallet, Vote

    authorization = request.headers.get('Authorization', '')
    if not authorization.startswith('Bearer '):
        return JsonResponse({'error': 'Sign-in required.'}, status=401)
    signer = signing.TimestampSigner(salt='unwind.mobile.auth')
    try:
        email = signer.unsign(authorization[7:].strip(), max_age=2592000)
    except signing.BadSignature:
        return JsonResponse({'error': 'Your sign-in has expired. Please sign in again.'}, status=401)

    orders = list(
        PackageOrder.objects.filter(customer_email__iexact=email)
        .select_related('package')
        .only(
            'id', 'customer_name', 'package__name', 'grand_total',
            'amount_paid', 'outstanding_balance', 'status',
        )
    )
    target = sum((order.grand_total for order in orders), Decimal('0'))
    saved = sum((min(order.amount_paid, order.grand_total) for order in orders), Decimal('0'))
    remaining = sum((order.outstanding_balance for order in orders), Decimal('0'))
    progress = float((saved / target * 100) if target else 0)
    rest_card = RestCard.objects.filter(member_email__iexact=email).first()
    frozen_points = FrozenRestPoints.objects.filter(
        member_email__iexact=email, points_claimed=False
    ).aggregate(total=Sum('frozen_points'))['total'] or Decimal('0')
    reward_wallet = TokenWallet.objects.filter(member_email__iexact=email).first()
    member_name = (rest_card.member_name if rest_card else '') or (
        reward_wallet.member_name if reward_wallet else ''
    ) or next(
        (order.customer_name for order in orders if order.customer_name), ''
    )
    latest_vote = Vote.objects.filter(voter_email__iexact=email).order_by('-created_at').first()
    community_member = CommunityMember.objects.filter(email__iexact=email).first()
    if not member_name:
        member_name = latest_vote.voter_name if latest_vote else (community_member.name if community_member else '')
    member_phone = (rest_card.member_phone if rest_card else '') or (
        community_member.phone if community_member else ''
    ) or (latest_vote.voter_phone if latest_vote else '')
    vote_history = Vote.objects.filter(voter_email__iexact=email).select_related(
        'nominee__campaign'
    ).order_by('-created_at')[:10]
    return JsonResponse({
        'email': email,
        'name': member_name,
        'phone': member_phone,
        'total_saved': str(saved),
        'total_target': str(target),
        'total_remaining': str(remaining),
        'overall_progress': round(progress),
        'rest_points': str(rest_card.total_rest_points if rest_card else Decimal('0')),
        'frozen_points': str(frozen_points),
        'reward_tokens': str(reward_wallet.available_tokens if reward_wallet else Decimal('0')),
        'vote_history': [{
            'id': vote.pk,
            'nominee': vote.nominee.name,
            'campaign': vote.nominee.campaign.name,
            'votes': vote.vote_quantity,
            'status': vote.get_payment_status_display(),
            'points_earned': str(vote.rest_points_earned),
        } for vote in vote_history],
        'orders': [{
            'id': order.pk,
            'package': order.package.name,
            'status': order.get_status_display(),
            'amount_paid': str(order.amount_paid),
            'grand_total': str(order.grand_total),
            'outstanding_balance': str(order.outstanding_balance),
            'progress': round(float(order.payment_progress)),
        } for order in orders],
    })


@csrf_exempt
@require_POST
def mobile_initialize_vote_api(request):
    """Authenticate a mobile member and safely pass a valid ballot to the existing Paystack flow."""
    from django.core import signing
    from django.http import JsonResponse
    from django.utils import timezone
    from .models import Nominee

    authorization = request.headers.get('Authorization', '')
    if not authorization.startswith('Bearer '):
        return JsonResponse({'success': False, 'message': 'Sign in before voting.'}, status=401)
    try:
        email = signing.TimestampSigner(salt='unwind.mobile.auth').unsign(
            authorization[7:].strip(), max_age=2592000
        )
        data = json.loads(request.body or '{}')
    except (signing.BadSignature, TypeError, json.JSONDecodeError):
        return JsonResponse({'success': False, 'message': 'Your session has expired. Sign in again.'}, status=401)

    if str(data.get('voter_email', '')).strip().lower() != email.lower():
        return JsonResponse({'success': False, 'message': 'The voter email must match your signed-in account.'}, status=403)
    ballot = data.get('ballot')
    if not isinstance(ballot, list) or not ballot or len(ballot) > 20:
        return JsonResponse({'success': False, 'message': 'Choose a nominee and enter a valid vote quantity.'}, status=400)
    nominee_ids = []
    for item in ballot:
        try:
            nominee_id = int(item.get('nominee_id'))
            quantity = int(item.get('votes'))
        except (AttributeError, TypeError, ValueError):
            return JsonResponse({'success': False, 'message': 'Invalid ballot.'}, status=400)
        if quantity < 1 or quantity > 100:
            return JsonResponse({'success': False, 'message': 'Vote quantities must be between 1 and 100.'}, status=400)
        nominee_ids.append(nominee_id)

    nominees = list(Nominee.objects.filter(pk__in=nominee_ids).select_related('campaign'))
    now_value = timezone.now()
    if len(nominees) != len(set(nominee_ids)) or any(
        not nominee.campaign.is_active
        or nominee.campaign.start_date > now_value
        or nominee.campaign.end_date < now_value
        for nominee in nominees
    ):
        return JsonResponse({'success': False, 'message': 'This voting campaign is not accepting votes.'}, status=400)

    # This existing initializer owns pricing, Rest Card free votes, and Paystack transaction creation.
    from . import voting_views
    return voting_views.initialize_payment(request)


def home(request):
    from .models import VotingCampaign, Nominee, GroupGetawayPackage
    from django.utils.timezone import now as get_now
    from django.db.models import Count
    
    # Get active campaigns
    current_time = get_now()
    active_campaigns = VotingCampaign.objects.filter(
        is_active=True, 
        start_date__lte=current_time,
        end_date__gte=current_time
    ).order_by('-start_date')
    
    # Get the latest campaign
    latest_campaign = VotingCampaign.objects.filter(is_active=True).order_by('-start_date').first()
    
    # Calculate additional campaign data
    total_nominations = 0
    days_remaining = 0
    top_nominees = []
    
    if latest_campaign:
        total_nominations = Nominee.objects.filter(campaign=latest_campaign).count()
        
        # Calculate days remaining
        from datetime import date
        if latest_campaign.end_date:
            today = date.today()
            end_date = latest_campaign.end_date.date() if hasattr(latest_campaign.end_date, 'date') else latest_campaign.end_date
            delta = end_date - today
            days_remaining = max(0, delta.days)
    
    # Get top nominees across all active campaigns (top 15 by votes)
    if active_campaigns:
        campaign_ids = [c.id for c in active_campaigns]
        top_nominees = Nominee.objects.filter(
            campaign_id__in=campaign_ids
        ).order_by('-vote_count')[:15]
    else:
        # Fallback to latest campaign if no active ones
        if latest_campaign:
            top_nominees = Nominee.objects.filter(campaign=latest_campaign).order_by('-vote_count')[:15]

    package_starts = []
    seen_categories = set()
    for package in GroupGetawayPackage.objects.filter(is_active=True).only(
        'name', 'slug', 'category', 'pricing_basis', 'price_per_person'
    ).order_by('category', 'price_per_person', 'name'):
        if package.category not in seen_categories:
            package_starts.append(package)
            seen_categories.add(package.category)
    
    return render(request, 'Web/home.html', {
        'campaign': active_campaigns.first() if active_campaigns else None,
        'total_nominations': total_nominations,
        'days_remaining': days_remaining,
        'top_nominees': top_nominees,
        'active_campaigns': active_campaigns,
        'package_starts': package_starts,
    })


def explore(request):
    """Explore page showing all website sections"""
    # Get latest blog posts
    from .models import Post
    latest_posts = Post.objects.filter(is_published=True).order_by('-created_at')[:3]
    
    # Get upcoming events
    from .models import Event
    upcoming_events = Event.objects.filter(date__gte=timezone.now()).order_by('date')[:3]
    
    # Get active voting campaigns
    from .models import VotingCampaign
    active_campaigns = VotingCampaign.objects.filter(is_active=True).order_by('-start_date')[:2]
    
    return render(request, 'Web/explore.html', {
        'latest_posts': latest_posts,
        'upcoming_events': upcoming_events,
        'active_campaigns': active_campaigns,
    })


def rest_card_signup(request):
    """Rest Card Early Sign-up page"""
    from .models import RestCard
    
    if request.method == 'POST':
        try:
            # Debug: print all POST data
            print("DEBUG: POST data received:", dict(request.POST))
            
            # Get form data
            email = request.POST.get('email', '').strip()
            name = request.POST.get('name', '').strip()
            phone = request.POST.get('phone', '').strip()
            
            print(f"DEBUG: email={email}, name={name}, phone={phone}")
            
            if not email or not name or not phone:
                return JsonResponse({
                    'success': False,
                    'message': 'Please fill in all required fields'
                }, status=400)
            
            # Check if already exists
            try:
                rest_card, created = RestCard.objects.get_or_create(
                    member_email=email,
                    defaults={
                        'member_name': name,
                        'member_phone': phone,
                        'status': 'waitlist'
                    }
                )
                
                print(f"DEBUG: RestCard created={created}, card={rest_card}")
            except Exception as db_error:
                print(f"DEBUG: Database error: {db_error}")
                return JsonResponse({
                    'success': False,
                    'message': f'Database error: {str(db_error)}'
                }, status=500)
            
            if not created:
                # Update existing record
                rest_card.member_name = name
                rest_card.member_phone = phone
                rest_card.save()
            else:
                # New rest card registration gets 1 free vote
                # (free_votes_remaining is already set to 1 by default in the model)
                pass
            
            # Send confirmation email
            try:
                from django.core.mail import send_mail
                from django.conf import settings
                import logging
                logger = logging.getLogger(__name__)
                
                subject = 'Rest Card Sign-up Confirmation - Unwind Africa'
                message = f"""Dear {name},

Thank you for signing up for the Unwind Africa Rest Card!

We've received your application and you're now on our waitlist. We'll be in touch soon with updates about your Rest Card.

Your Details:
- Name: {name}
- Email: {email}
- Phone: {phone}

What happens next?
We'll review your application and send you updates about your Rest Card status.

Best regards,
The Unwind Africa Team
Phone: +234 806 206 7832
Email: info@unwindafrica.com"""
                
                logger.info(f"Attempting to send email to {email}")
                logger.info(f"Email settings - HOST: {settings.EMAIL_HOST}, USER: {settings.EMAIL_HOST_USER}")
                
                result = send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False  # Changed to False to see actual errors
                )
                logger.info(f"Email send result: {result}")
            except Exception as email_err:
                # Log email error but don't fail the signup
                import traceback
                logger.error(f"Email sending error: {email_err}")
                logger.error(f"Full traceback: {traceback.format_exc()}")
            
            # Include free vote info in response
            free_vote_message = ''
            if created:
                free_vote_message = ' You also have 1 free vote to use in the current voting campaign!'
            
            return JsonResponse({
                'success': True,
                'message': f'Thank you for signing up! We will contact you soon with updates about your Rest Card.{free_vote_message}',
                'waitlist_position': getattr(rest_card, 'waitlist_position', None),
                'free_votes_remaining': rest_card.free_votes_remaining
            })
        
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error processing rest card signup: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': 'Something went wrong. Please try again.'
            }, status=500)
    
    return render(request, 'Web/rest_card_signup.html', {})


def about(request):
    return render(request, 'Web/about.html', context={})


def raising_readers(request):
    from .models import Book
    books = Book.objects.all().order_by('-created_at')
    return render(request, 'Web/raising_readers.html', context={'books': books})


def packages(request):
    from .models import GroupGetawayPackage, PackageAddOn
    packages_qs = GroupGetawayPackage.objects.filter(is_active=True).order_by('category', 'experience_duration', 'price_per_person')
    for package in packages_qs:
        package.card_image_url = _package_artwork_url(package)
    addons_qs = PackageAddOn.objects.filter(is_active=True).order_by('name')
    return render(request, 'Web/packages.html', context={
        'packages': packages_qs,
        'addons': addons_qs,
    })


def add_months(d, n):
    y = d.year + (d.month - 1 + n) // 12
    m = (d.month - 1 + n) % 12 + 1
    return d.replace(year=y, month=m)


def package_detail(request, slug):
    """Group Getaway package page with Pay Outright / Start Your Savings Plan options."""
    from .models import GroupGetawayPackage, PackageAddOn
    package = get_object_or_404(GroupGetawayPackage, slug=slug, is_active=True)
    addons = PackageAddOn.objects.filter(is_active=True).order_by('name')
    doctor_addon = PackageAddOn.objects.filter(name__icontains='doctor', is_active=True).first()
    transport_addon = PackageAddOn.objects.filter(name__icontains='transport', is_active=True).first()
    durations = package.durations or [3, 6, 9, 12]
    default_party_size = package.included_adults + package.included_children if package.pricing_basis == 'family' else (2 if package.pricing_basis == 'couple' else 1)
    package_total = package.price_per_person * (default_party_size if package.pricing_basis == 'person' else 1)
    plans = {}
    for duration in durations:
        plans[duration] = package.calculate_plan(duration, package_total=package_total)
    plan_options = [{
        'duration': duration,
        'monthly_contribution': plans[duration]['monthly_contribution'],
        'monthly_display': f"{plans[duration]['monthly_contribution']:,.0f}",
    } for duration in durations]
    context = {
        'package': package,
        'package_image_url': _package_artwork_url(package),
        'addons': addons,
        'doctor_addon': doctor_addon,
        'addon_price': doctor_addon.price if doctor_addon else Decimal('35000'),
        'transport_price': transport_addon.price if transport_addon else Decimal('20000'),
        'durations': durations,
        'plans': plans,
        'plan_options': plan_options,
        'default_party_size': default_party_size,
        'package_total': package_total,
        'checkout_error': request.GET.get('registration_error'),
        'plan_mode_label': 'savings plan' if request.GET.get('mode') == 'plan' else 'payment',
    }
    return render(request, 'Web/package_detail.html', context)


@require_POST
def package_checkout(request, slug):
    """Create the booking and securely collect its first deposit through Paystack."""
    from .models import (GroupGetawayPackage, PackageAddOn, PackageOrder, PackageInstalment,
                         PackagePayment, CommunityMember, RestCard, FrozenRestPoints,
                         TokenWallet, Vote)
    package = get_object_or_404(GroupGetawayPackage, slug=slug, is_active=True)

    customer_email = request.POST.get('customer_email', '').strip().lower()
    customer_name = request.POST.get('customer_name', '').strip()
    try:
        duration = int(request.POST.get('duration_months', 1) or 1)
    except (TypeError, ValueError):
        duration = 0
    outright = request.POST.get('outright') == '1'
    my_doctor = request.POST.get('my_doctor') == 'on'
    transportation = request.POST.get('transportation') == 'on'
    pickup_location = request.POST.get('transportation_pickup_location', '').strip()
    try:
        party_size = int(request.POST.get('party_size', 1) or 1)
        initial_deposit = Decimal(request.POST.get('initial_deposit', '0') or '0').quantize(Decimal('0.01'))
    except (ValueError, TypeError, ArithmeticError):
        party_size, initial_deposit = 0, Decimal('0')

    if not customer_email:
        return redirect(f"/packages/{package.slug}/?registration_error=email")

    # Launch registration is for people already known through the community, Rest Card, or voting.
    is_known_member = (
        CommunityMember.objects.filter(email__iexact=customer_email).exists()
        or RestCard.objects.filter(member_email__iexact=customer_email).exists()
        or FrozenRestPoints.objects.filter(member_email__iexact=customer_email).exists()
        or TokenWallet.objects.filter(member_email__iexact=customer_email).exists()
        or Vote.objects.filter(voter_email__iexact=customer_email).exists()
        or PackageOrder.objects.filter(customer_email__iexact=customer_email).exists()
    )
    if not is_known_member:
        return redirect(f"/packages/{package.slug}/?registration_error=member")

    if package.pricing_basis == 'person':
        if party_size < 1 or party_size > 20:
            return redirect(f"/packages/{package.slug}/?registration_error=party")
        unit_count = party_size
        transport_headcount = party_size
    elif package.pricing_basis == 'couple':
        unit_count = 1
        transport_headcount = 2
        party_size = 2
    else:
        unit_count = 1
        transport_headcount = package.included_adults + package.included_children
        party_size = transport_headcount

    if duration not in package.durations and not outright:
        return redirect(f"/packages/{package.slug}/?registration_error=plan")
    if outright:
        duration = 1
    if transportation and not pickup_location:
        return redirect(f"/packages/{package.slug}/?registration_error=pickup")

    package_total = package.price_per_person * unit_count
    addon_total = Decimal('0')
    if my_doctor:
        addon = PackageAddOn.objects.filter(name__icontains='doctor', is_active=True).first()
        addon_total += addon.price if addon else Decimal('35000')
    transport_unit_price = PackageAddOn.objects.filter(name__icontains='transport', is_active=True).values_list('price', flat=True).first() or Decimal('20000')
    transportation_total = transport_unit_price * transport_headcount if transportation else Decimal('0')
    addon_total += transportation_total

    plan = package.calculate_plan(duration, addon_total=addon_total, package_total=package_total)
    if initial_deposit <= 0:
        return redirect(f"/packages/{package.slug}/?registration_error=deposit")
    if initial_deposit > plan['grand_total']:
        return redirect(f"/packages/{package.slug}/?registration_error=deposit")

    # A zero charge rate is used until the business provides approved installment fees.
    start_date = date.today()
    schedule = []
    monthly = plan['monthly_contribution']
    for i in range(1, duration + 1):
        due = add_months(start_date, i - 1)
        main_due = plan['grand_total'] - (monthly * (duration - 1)) if i == duration else monthly
        schedule.append({
            'month_number': i,
            'due_date': due,
            'main_amount_due': main_due,
            'rest_forward_portion': Decimal('0'),
            'total_due': main_due,
        })

    order = PackageOrder.objects.create(
        customer_email=customer_email,
        customer_name=customer_name,
        package=package,
        package_price=package_total,
        duration_months=duration,
        my_doctor_selected=my_doctor,
        my_doctor_price=(addon.price if my_doctor and addon else Decimal('35000') if my_doctor else Decimal('0')),
        transportation_selected=transportation,
        transportation_price=transportation_total,
        transportation_pickup_location=pickup_location,
        party_size=party_size,
        rest_forward_selected=False,
        rest_forward_total=Decimal('0'),
        rest_forward_monthly=Decimal('0'),
        rest_forward_balance=Decimal('0'),
        subtotal=plan['subtotal'],
        instalment_charges=plan['instalment_charges'],
        grand_total=plan['grand_total'],
        monthly_contribution=plan['monthly_contribution'],
        amount_paid=Decimal('0'),
        outstanding_balance=plan['grand_total'],
        status='pending',
    )

    for item in schedule:
        PackageInstalment.objects.create(
            order=order,
            month_number=item['month_number'],
            due_date=item['due_date'],
            main_amount_due=item['main_amount_due'],
            rest_forward_portion=item['rest_forward_portion'],
            total_due=item['total_due'],
            amount_paid=Decimal('0'),
            status='pending',
        )

    if not settings.PAYSTACK_SECRET_KEY:
        return redirect(f"/packages/{package.slug}/?registration_error=payment")
    reference = f"GG-{secrets.token_urlsafe(18)}"
    payment = PackagePayment.objects.create(
        order=order, amount=initial_deposit, reference=reference,
        is_initial_deposit=True, status='pending',
    )
    payload = {
        'email': customer_email,
        'amount': int(initial_deposit * 100),
        'reference': reference,
        'callback_url': request.build_absolute_uri(f'/dashboard/packages/verify/{reference}/'),
        'metadata': {
            'order_id': order.id,
            'customer_name': customer_name,
            'package_name': package.name,
            'initial_deposit': True,
        },
    }
    try:
        response = requests.post(
            'https://api.paystack.co/transaction/initialize',
            headers={'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}', 'Content-Type': 'application/json'},
            json=payload,
            timeout=15,
        )
        response_data = response.json()
        if response.ok and response_data.get('status'):
            paystack_data = response_data['data']
            payment.paystack_reference = paystack_data.get('reference', reference)
            payment.authorization_url = paystack_data.get('authorization_url', '')
            payment.paystack_response = response_data
            payment.save(update_fields=['paystack_reference', 'authorization_url', 'paystack_response'])
            return redirect(payment.authorization_url)
        payment.status = 'failed'
        payment.paystack_response = response_data
        payment.save(update_fields=['status', 'paystack_response'])
        return redirect(f"/packages/{package.slug}/?registration_error=payment")
    except (requests.RequestException, ValueError) as exc:
        logger.exception('Unable to initialize Group Getaway initial deposit')
        payment.status = 'failed'
        payment.paystack_response = {'error': str(exc)}
        payment.save(update_fields=['status', 'paystack_response'])
        return redirect(f"/packages/{package.slug}/?registration_error=payment")


def package_order(request, order_id):
    """Authenticated order detail with payment schedule and history."""
    from .models import PackageOrder, PackageInstalment, PackagePayment, GroupGetawayPackage
    email = request.session.get('dashboard_user_email')
    if not email:
        return redirect('user_dashboard_login')
    order = get_object_or_404(PackageOrder, id=order_id, customer_email__iexact=email)
    instalments = order.instalments.all()
    payments = order.payments.all()

    context = {
        'order': order,
        'instalments': instalments,
        'payments': payments,
        'upgrade_packages': GroupGetawayPackage.objects.filter(
            category=order.package.category, is_active=True,
            price_per_person__gt=order.package.price_per_person,
        ).exclude(pk=order.package_id).order_by('price_per_person'),
        'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY,
    }
    return render(request, 'Web/package_order.html', context)


@require_POST
def package_upgrade(request, order_id):
    """Upgrade an existing getaway booking and add the price difference to its balance."""
    from .models import PackageOrder, GroupGetawayPackage, PackageInstalment
    from django.db import transaction
    from django.contrib import messages

    email = request.session.get('dashboard_user_email')
    if not email:
        return redirect('user_dashboard_login')
    order = get_object_or_404(PackageOrder, pk=order_id, customer_email__iexact=email)
    target = get_object_or_404(GroupGetawayPackage, slug=request.POST.get('package_slug'), is_active=True)
    if target.category != order.package.category or target.pricing_basis != order.package.pricing_basis:
        messages.error(request, 'Choose an available upgrade in the same experience category.')
        return redirect('package_order', order_id=order.id)

    target_units = order.party_size if target.pricing_basis == 'person' else 1
    new_package_total = target.price_per_person * target_units
    if new_package_total <= order.package_price:
        messages.error(request, 'Choose an experience with a higher starting price to upgrade.')
        return redirect('package_order', order_id=order.id)

    discount = (new_package_total * Decimal('0.05')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) if order.early_access_slot else Decimal('0')
    discounted_package_total = new_package_total - discount
    addon_total = order.my_doctor_price + order.transportation_price
    plan = target.calculate_plan(
        max(1, order.duration_months), addon_total=addon_total,
        package_total=discounted_package_total,
    )

    with transaction.atomic():
        order = PackageOrder.objects.select_for_update().get(pk=order.pk)
        paid_instalments = list(order.instalments.filter(status='paid').order_by('month_number'))
        order.package = target
        order.package_price = new_package_total
        order.early_access_discount = discount
        order.subtotal = plan['subtotal']
        order.instalment_charges = plan['instalment_charges']
        order.grand_total = plan['grand_total']
        order.monthly_contribution = plan['monthly_contribution']
        order.outstanding_balance = max(Decimal('0'), order.grand_total - order.amount_paid)
        order.overpayment_credit = max(Decimal('0'), order.amount_paid - order.grand_total)
        order.status = 'completed' if order.outstanding_balance <= 0 else 'active'
        order.save()

        order.instalments.exclude(status='paid').delete()
        paid_months = {row.month_number for row in paid_instalments}
        open_months = [month for month in range(1, max(1, order.duration_months) + 1) if month not in paid_months]
        if not open_months and order.outstanding_balance > 0:
            open_months = [max(paid_months or {0}) + 1]
        remaining = order.outstanding_balance
        count = len(open_months)
        if count:
            monthly = (remaining / count).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            for index, month in enumerate(open_months):
                due = remaining if index == count - 1 else min(monthly, remaining)
                remaining -= due
                PackageInstalment.objects.create(
                    order=order,
                    month_number=month,
                    due_date=add_months(date.today(), max(0, month - 1)),
                    main_amount_due=due,
                    total_due=due,
                    rest_forward_portion=Decimal('0'),
                )

    messages.success(request, f'Your booking is now upgraded to {target.name}. Pay the updated balance to complete it.')
    return redirect('package_order', order_id=order.id)


def api_calculate_plan(request):
    """AJAX endpoint: compute plan breakdown for duration/add-ons."""
    from .models import GroupGetawayPackage, PackageAddOn
    from decimal import Decimal, ROUND_HALF_UP
    slug = request.GET.get('slug')
    raw_durations = request.GET.get('durations')
    try:
        durations = ([int(value) for value in raw_durations.split(',') if value.strip()]
                     if raw_durations else [int(request.GET.get('duration', 1) or 1)])
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'error': 'Choose a valid payment duration.'}, status=400)
    durations = list(dict.fromkeys(durations))
    if not durations or len(durations) > 12 or any(value < 1 or value > 36 for value in durations):
        return JsonResponse({'ok': False, 'error': 'Choose valid payment durations.'}, status=400)
    my_doctor = request.GET.get('my_doctor') == 'true'
    transportation = request.GET.get('transportation') == 'true'
    rest_forward = request.GET.get('rest_forward') == 'true'
    try:
        party_size = max(1, min(20, int(request.GET.get('party_size', '1'))))
    except (TypeError, ValueError):
        party_size = 1

    package = get_object_or_404(GroupGetawayPackage, slug=slug, is_active=True)
    allowed_durations = package.durations
    if any(value not in allowed_durations and value != 1 for value in durations):
        return JsonResponse({'ok': False, 'error': 'Choose an available payment duration.'}, status=400)
    if package.pricing_basis == 'person':
        unit_count, headcount = party_size, party_size
    elif package.pricing_basis == 'couple':
        unit_count, headcount = 1, 2
    else:
        unit_count, headcount = 1, package.included_adults + package.included_children
    package_total = package.price_per_person * unit_count

    addon_total = Decimal('0')
    addon_rows = PackageAddOn.objects.filter(is_active=True).filter(
        Q(name__icontains='doctor') | Q(name__icontains='transport')
    ).values_list('name', 'price')
    addon_price = next((price for name, price in addon_rows if 'doctor' in name.lower()), None) or Decimal('35000')
    transport_price = next((price for name, price in addon_rows if 'transport' in name.lower()), None) or Decimal('20000')
    if my_doctor:
        addon_total += addon_price
    if transportation:
        addon_total += transport_price * headcount

    plans = []
    for duration in durations:
        plan = package.calculate_plan(duration, addon_total=addon_total, rest_forward=rest_forward, package_total=package_total)
        plan['addon_price'] = addon_price
        plan['transport_price'] = transport_price
        plans.append({k: str(v) for k, v in plan.items()})
    return JsonResponse({'ok': True, 'plan': plans[0], 'plans': plans})


def custom_404(request, exception):
    return render(request, '404.html', status=404)


# ==================== LEGAL PAGES (Paystack requires these) ====================
def privacy_policy(request):
    return render(request, 'Web/privacy_policy.html')


def terms(request):
    return render(request, 'Web/terms.html')


def refund_policy(request):
    return render(request, 'Web/refund_policy.html')


def faq(request):
    return render(request, 'Web/faq.html')

# -----------------------------
# BLOG
# -----------------------------

def blog_list(request):
    posts = Post.objects.filter(is_published=True).order_by('-is_featured', '-created_at')
    return render(request, 'Web/blog_list.html', {'posts': posts, 'now': now()})


def blog_detail(request, slug):
    """Full post page by default; if ?modal=1 return only the modal fragment."""
    post = get_object_or_404(Post, slug=slug, is_published=True)
    from .blog_content import clean_blog_html
    post.rendered_content = clean_blog_html(post.content)
    post.journal_tags = [tag.strip() for tag in post.tags.split(',') if tag.strip()]
    if request.GET.get('modal') == '1':
        # Return just the modal contents (popup)
        return render(request, 'Web/partials/post_modal.html', {
            'post': post,
        })
    related = Post.objects.filter(is_published=True).exclude(id=post.id).order_by('-created_at')[:2]
    return render(request, 'Web/blog_detail.html', {
        'post': post,
        'related': related,
    })


def blog_category(request, slug):
    """Optional: list posts by BlogCategory (uses BlogCategory.name vs Post.category CharField)."""
    category = get_object_or_404(BlogCategory, slug=slug)
    posts = Post.objects.filter(
        is_published=True,
        category=category.name
    ).order_by('-created_at')
    return render(request, 'Web/blog_category.html', {
        'category': category,
        'posts': posts,
    })


# -----------------------------
# EVENTS
# -----------------------------

def event_list(request):
    """Upcoming first; show past separately for archives."""
    today = timezone.now().date()
    events = Event.objects.filter(date__gte=today).order_by('date')
    past_events = Event.objects.filter(date__lt=today).order_by('-date')
    return render(request, 'Web/event_list.html', {
        'events': events,
        'past_events': past_events,
        'today': today,
    })

def unwind_thrive(request):
    return render(request, 'Web/unwind-thrive.html', context={})


def event_detail(request, slug):
    """
    Full event page by default; if ?modal=1 return only the modal fragment
    (so clicking a card can open a popup with the flier and details).
    """
    event = get_object_or_404(Event, slug=slug)
    if request.GET.get('modal') == '1':
        return render(request, 'Web/partials/event_modal.html', {
            'event': event,
        })
    return render(request, 'Web/event_detail.html', {
        'event': event,
    })


def contact(request):
    return render(request, 'Web/contact.html', {})


def test(request):
    return render(request, 'Web/tss.html', {})

# Web/views.py
from django.http import JsonResponse
from django.core.mail import send_mail
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt, csrf_protect

@require_POST
@csrf_protect
def quote_request(request):
    name = request.POST.get("name","").strip()
    email = request.POST.get("email","").strip()
    phone = request.POST.get("phone","").strip()
    package = request.POST.get("package","").strip()
    dates = request.POST.get("dates","").strip()
    group_size = request.POST.get("group_size","").strip()
    notes = request.POST.get("notes","").strip()
    page = request.POST.get("page","").strip()
    utm = request.POST.get("utm","").strip()

    if not name or not email or not package:
        return JsonResponse({"ok": False, "error": "Name, email and package are required."}, status=400)

    # (Optional) Persist to DB if you have a Quote model
    # Quote.objects.create(...)

    # (Optional) Email notification to your team
    subject = f"[Quote] {package} — {name}"
    body = (
        f"Name: {name}\nEmail: {email}\nPhone: {phone}\n"
        f"Package: {package}\nDates: {dates}\nGroup size: {group_size}\n"
        f"Notes:\n{notes}\n\n"
        f"Page: {page}\nReferrer: {utm}\n"
    )
    from django.conf import settings
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, ["info@unwindafrica.com"], fail_silently=True)
    except Exception:
        pass

    return JsonResponse({"ok": True})


@require_POST
@csrf_protect
def card_request(request):
    """Handle Rest Card request form - add to waitlist and send emails"""
    from .models import RestCard
    
    name = request.POST.get("name","").strip()
    email = request.POST.get("email","").strip()
    phone = request.POST.get("phone","").strip()
    message = request.POST.get("message","").strip()

    if not name or not email or not phone:
        return JsonResponse({"success": False, "error": "Name, email and phone are required."}, status=400)

    # Check if already on waitlist
    if RestCard.objects.filter(member_email=email).exists():
        return JsonResponse({"success": False, "error": "This email is already on the waitlist."}, status=400)

    # Check if waitlist is full
    waitlist_count = RestCard.objects.filter(status='waitlist').count()
    if waitlist_count >= 1000:
        return JsonResponse({"success": False, "error": "Waitlist is currently full. Check back soon!"}, status=400)

    # Create waitlist entry
    try:
        card = RestCard.objects.create(
            member_name=name,
            member_email=email,
            member_phone=phone,
            status='waitlist'
        )

        # Send email to clientservicesunwindafrica@gmail.com
        subject_admin = f"New Rest Card Request from {name}"
        body_admin = (
            f"New Rest Card Request:\n\n"
            f"Name: {name}\nEmail: {email}\nPhone: {phone}\n"
            f"Message: {message}\n"
            f"Waitlist Position: #{card.waitlist_position}\n"
        )
        from django.conf import settings
        send_mail(subject_admin, body_admin, settings.DEFAULT_FROM_EMAIL, ["clientservicesunwindafrica@gmail.com"], fail_silently=False)

        # Send confirmation email to user
        subject_user = "Thank you for your Rest Card request!"
        body_user = (
            f"Dear {name},\n\n"
            f"Thank you for requesting a Rest Card from Unwind Africa!\n\n"
            f"We have received your request and added you to our waitlist.\n"
            f"Your position on the waitlist is: #{card.waitlist_position}\n\n"
            f"We will contact you as soon as more spots become available.\n\n"
            f"Best regards,\n"
            f"The Unwind Africa Team\n"
            f"Phone: +234 806 206 7832\n"
            f"Email: info@unwindafrica.com"
        )
        send_mail(subject_user, body_user, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)

    except Exception as e:
        print(f"Error processing card request: {e}")
        return JsonResponse({"success": False, "error": "Failed to process request. Please try again."}, status=500)

    return JsonResponse({"success": True, "message": f"Thank you for your request! You are #{card.waitlist_position} on the waitlist."})


# ===================== COMMUNITY & REST CARD VIEWS =====================

def community_stats(request):
    """Display community statistics from Google Form data"""
    from .models import CommunityMember
    from django.db.models import Count
    
    total_members = CommunityMember.objects.count()
    
    # Gender breakdown
    gender_stats = CommunityMember.objects.values('gender').annotate(count=Count('gender'))
    
    # Location breakdown (top 10)
    location_stats = CommunityMember.objects.values('location').annotate(
        count=Count('location')).order_by('-count')[:10]
    
    context = {
        'total_members': total_members,
        'gender_stats': gender_stats,
        'location_stats': location_stats,
    }
    
    # Return JSON for AJAX requests
    if request.GET.get('json') == '1':
        gender_data = {item['gender']: item['count'] for item in gender_stats if item['gender']}
        location_data = {item['location']: item['count'] for item in location_stats if item['location']}
        return JsonResponse({
            'total_members': total_members,
            'gender': gender_data,
            'locations': location_data
        })
    
    return render(request, 'Web/community/stats.html', context)


def rest_card_info(request):
    """Rest Card information page"""
    from .models import RestCard
    waitlist_count = RestCard.objects.filter(status='waitlist').count()
    spots_remaining = max(0, 1000 - waitlist_count)
    return render(request, 'Web/community/rest_card.html', {
        'waitlist_count': waitlist_count,
        'spots_remaining': spots_remaining,
    })


@require_POST
@csrf_protect
def rest_card_waitlist_join(request):
    """Join the Rest Card waitlist"""
    from .models import RestCard
    
    name = request.POST.get('name', '').strip()
    email = request.POST.get('email', '').strip()
    phone = request.POST.get('phone', '').strip()
    
    if not name or not email or not phone:
        return JsonResponse({
            'ok': False,
            'error': 'Name, email, and phone are required.'
        }, status=400)
    
    # Check if waitlist is full
    waitlist_count = RestCard.objects.filter(status='waitlist').count()
    if waitlist_count >= 1000:
        return JsonResponse({
            'ok': False,
            'error': 'Waitlist is currently full. Check back soon!'
        }, status=400)
    
    # Check if already exists
    if RestCard.objects.filter(member_email=email).exists():
        return JsonResponse({
            'ok': False,
            'error': 'This email is already on the waitlist.'
        }, status=400)
    
    # Create waitlist entry
    card = RestCard.objects.create(
        member_name=name,
        member_email=email,
        member_phone=phone,
        status='waitlist'
    )
    
    return JsonResponse({
        'ok': True,
        'position': card.waitlist_position,
        'message': f'Success! You are #{card.waitlist_position} on the waitlist.'
    })


def rest_card_status(request):
    """Check Rest Card status"""
    email = request.GET.get('email', '').strip()
    
    if not email:
        return render(request, 'Web/community/card_status.html', {'card': None})
    
    from .models import RestCard
    
    try:
        card = RestCard.objects.get(member_email=email)
        return render(request, 'Web/community/card_status.html', {'card': card})
    except RestCard.DoesNotExist:
        return render(request, 'Web/community/card_status.html', {
            'card': None,
            'error': 'No Rest Card found for this email.'
        })


def token_wallet_view(request):
    """View token wallet (requires email lookup for now)"""
    email = request.GET.get('email', '').strip()
    
    if not email:
        return render(request, 'Web/community/token_wallet.html', {'wallet': None})
    
    from .models import TokenWallet
    
    try:
        wallet = TokenWallet.objects.prefetch_related('transactions').get(member_email=email)
        recent_transactions = wallet.transactions.all()[:10]
        return render(request, 'Web/community/token_wallet.html', {
            'wallet': wallet,
            'recent_transactions': recent_transactions
        })
    except TokenWallet.DoesNotExist:
        return render(request, 'Web/community/token_wallet.html', {
            'wallet': None,
            'error': 'No wallet found for this email.'
        })


def unwind_and_win(request):
    """Unwind & Win rewards page"""
    return render(request, 'Web/community/unwind_and_win.html', {})


def vote(request):
    """Voting page for users - displays nominees with search and filter"""
    from .models import VotingCampaign, Nominee
    from django.utils.timezone import now as get_now
    
    # Get active campaign
    campaign = VotingCampaign.objects.filter(is_active=True).order_by('-start_date').first()
    
    if not campaign:
        return render(request, 'Web/vote.html', {'campaign': None, 'error': 'No active campaign'})
    
    # Get all nominees for the campaign
    nominees = Nominee.objects.filter(campaign=campaign).order_by('number')
    
    # Get leaderboard (top 3)
    leaderboard = nominees.order_by('-vote_count')[:3]
    
    # Determine if campaign is ongoing
    current_time = get_now()
    is_ongoing = campaign.is_active and campaign.start_date <= current_time <= campaign.end_date
    
    context = {
        'campaign': campaign,
        'nominees': nominees,
        'leaderboard': leaderboard,
        'vote_price': campaign.vote_price,
        'rest_points_per_vote': campaign.rest_points_per_vote,
        'is_ongoing': is_ongoing,
        'is_test_mode': False,  # Use real Paystack
    }
    
    return render(request, 'Web/vote.html', context)


def payment(request, vote_id):
    """Start a server-verified Paystack charge for a legacy vote record."""
    from .models import Vote, Transaction
    from django.contrib import messages

    vote = get_object_or_404(Vote, id=vote_id)
    if vote.payment_status == 'paid':
        return redirect('vote_confirmation', vote_id=vote.id)

    if request.method == 'POST':
        if request.POST.get('payment_method') != 'paystack':
            messages.error(request, 'Choose Paystack to continue with this payment.')
            return redirect('payment', vote_id=vote.id)
        payment_email = request.POST.get('email', vote.voter_email).strip().lower()
        try:
            from django.core.validators import validate_email
            from django.core.exceptions import ValidationError
            validate_email(payment_email)
        except ValidationError:
            messages.error(request, 'Add a valid email address before starting payment.')
            return redirect('payment', vote_id=vote.id)
        if vote.amount <= 0:
            messages.error(request, 'This vote does not have a valid payment amount.')
            return redirect('payment', vote_id=vote.id)
        if not settings.PAYSTACK_SECRET_KEY:
            messages.error(request, 'Online payment is temporarily unavailable.')
            return redirect('payment', vote_id=vote.id)

        if payment_email != vote.voter_email:
            vote.voter_email = payment_email
            vote.save(update_fields=['voter_email'])

        reference = f"VOTE-{secrets.token_urlsafe(18)}"
        payment, _ = Transaction.objects.get_or_create(
            vote=vote,
            defaults={'reference': reference, 'amount': vote.amount, 'status': 'pending'},
        )
        if payment.status == 'success':
            vote.payment_status = 'paid'
            vote.save(update_fields=['payment_status'])
            return redirect('vote_confirmation', vote_id=vote.id)
        payment.reference = reference
        payment.amount = vote.amount
        payment.status = 'pending'
        payment.authorization_url = ''
        payment.access_code = ''
        payment.paystack_response = None
        payment.save(update_fields=[
            'reference', 'amount', 'status', 'authorization_url',
            'access_code', 'paystack_response', 'updated_at',
        ])

        payload = {
            'email': vote.voter_email,
            'amount': int(vote.amount * 100),
            'reference': reference,
            'callback_url': request.build_absolute_uri(
                f'/voting/payment/verify/{reference}/'
            ),
            'metadata': {
                'vote_id': vote.pk,
                'nominee': vote.nominee.name,
                'vote_quantity': vote.vote_quantity,
            },
        }
        try:
            response = requests.post(
                'https://api.paystack.co/transaction/initialize',
                headers={
                    'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
                    'Content-Type': 'application/json',
                },
                json=payload,
                timeout=15,
            )
            response_data = response.json()
            provider_data = response_data.get('data') or {}
            authorization_url = provider_data.get('authorization_url', '')
            if response.ok and response_data.get('status') and authorization_url:
                payment.paystack_reference = provider_data.get('reference', reference)
                payment.authorization_url = authorization_url
                payment.access_code = provider_data.get('access_code', '')
                payment.paystack_response = response_data
                payment.save(update_fields=[
                    'paystack_reference', 'authorization_url', 'access_code',
                    'paystack_response', 'updated_at',
                ])
                return redirect(authorization_url)

            payment.status = 'failed'
            payment.paystack_response = response_data
            payment.save(update_fields=['status', 'paystack_response', 'updated_at'])
            messages.error(request, 'Paystack could not start this payment. Please try again.')
        except (requests.RequestException, ValueError):
            logger.exception('Unable to initialize legacy vote payment')
            payment.status = 'failed'
            payment.paystack_response = {'error': 'Paystack initialization failed'}
            payment.save(update_fields=['status', 'paystack_response', 'updated_at'])
            messages.error(request, 'Unable to reach Paystack. Please try again shortly.')
        return redirect('payment', vote_id=vote.id)

    context = {
        'vote': vote,
        'campaign': vote.nominee.campaign,
        'payment_email': vote.voter_email,
    }
    return render(request, 'Web/payment.html', context)


def vote_confirmation(request, vote_id):
    """Vote confirmation page"""
    from .models import Vote
    
    vote = get_object_or_404(Vote, id=vote_id)
    
    context = {
        'vote': vote,
        'campaign': vote.nominee.campaign
    }
    
    return render(request, 'Web/vote_confirmation.html', context)


def nominate(request):
    """Accept nominations only while a campaign is accepting entries."""
    from .models import VotingCampaign
    from .forms import NominationForm
    from django.utils import timezone
    
    current_time = timezone.now()
    campaigns = VotingCampaign.objects.filter(
        is_active=True,
        start_date__lte=current_time,
        end_date__gte=current_time,
    ).order_by('-start_date')
    campaign = next(
        (item for item in campaigns if not item.nomination_deadline or item.nomination_deadline >= current_time),
        None,
    )
    
    if not campaign:
        return render(request, 'Web/nominate.html', {
            'campaign': None,
            'error': 'There are no active nomination campaigns right now. Please check back when the next campaign opens.',
        })
    
    if request.method == 'POST':
        form = NominationForm(request.POST, request.FILES)
        if form.is_valid():
            # Save nomination
            nominee = form.save(campaign)
            
            return redirect('nomination_confirmation', nominee_id=nominee.id)
    else:
        form = NominationForm()
    
    context = {
        'campaign': campaign,
        'form': form
    }
    
    return render(request, 'Web/nominate.html', context)


def nomination_confirmation(request, nominee_id):
    """Nomination confirmation page"""
    from .models import Nominee
    
    nominee = get_object_or_404(Nominee, id=nominee_id)
    
    context = {
        'nominee': nominee,
        'campaign': nominee.campaign
    }
    
    return render(request, 'Web/nomination_confirmation.html', context)


def my_rest_card(request):
    """User's Rest Card view (requires email + OTP authentication)"""
    # For now, we'll use email lookup - in production, this should use OTP
    email = request.GET.get('email', '').strip()
    
    if not email:
        return render(request, 'Web/community/my_rest_card.html', {'card': None})
    
    from .models import RestCard, TokenWallet
    
    try:
        card = RestCard.objects.get(member_email=email)
        
        # Get token wallet
        try:
            wallet = TokenWallet.objects.get(member_email=email)
        except TokenWallet.DoesNotExist:
            wallet = None
            
        context = {
            'card': card,
            'wallet': wallet
        }
        
        return render(request, 'Web/community/my_rest_card.html', context)
        
    except RestCard.DoesNotExist:
        return render(request, 'Web/community/my_rest_card.html', {
            'card': None,
            'error': 'No Rest Card found for this email.'
        })


def generate_rest_card(request, card_id):
    """Generate a digital Rest Card as PNG image"""
    from django.http import HttpResponse
    from io import BytesIO
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return HttpResponse("PIL library not available", status=500)
    
    from .models import RestCard, TokenWallet
    
    try:
        card = RestCard.objects.get(id=card_id)
        
        # Get token wallet
        try:
            wallet = TokenWallet.objects.get(member_email=card.member_email)
        except TokenWallet.DoesNotExist:
            wallet = None
            
        # Create card image
        width, height = 800, 500
        image = Image.new('RGB', (width, height), color='#ffffff')
        draw = ImageDraw.Draw(image)
        
        # Card background
        draw.rectangle([0, 0, width, height], fill='#ffffff')
        draw.rectangle([10, 10, width-10, height-10], fill='#f8f9fa', width=2)
        
         # Card header
        draw.rectangle([10, 10, width-10, 100], fill='#667eea')
        
        # Add card details
        # ... (rest of the card generation code would be here)
        
        # Save image to buffer
        buffer = BytesIO()
        image.save(buffer, format='PNG')
        buffer.seek(0)
        
        return HttpResponse(buffer, content_type='image/png')
        
    except RestCard.DoesNotExist:
        return HttpResponse("Rest Card not found", status=404)
    except Exception as e:
        return HttpResponse(f"Error generating card: {str(e)}", status=500)


# Add the view functions for EdBritish Trial
from django.views.decorators.csrf import csrf_protect
from django.core.mail import send_mail
from django.conf import settings


def edbritish_trial(request):
    """Display the EdBritish trial class registration page"""
    return render(request, 'Web/edbritish_trial.html', {})


@csrf_protect
def edbritish_trial_registration(request):
    """Handle the EdBritish trial class registration form submission"""
    from django.http import JsonResponse
    
    if request.method == 'POST':
        try:
            # Get form data
            parent_name = request.POST.get('parent_name', '').strip()
            parent_email = request.POST.get('parent_email', '').strip()
            parent_phone = request.POST.get('parent_phone', '').strip()
            country = request.POST.get('country', '').strip()
            child_name = request.POST.get('child_name', '').strip()
            child_age = request.POST.get('child_age', '').strip()
            subject = request.POST.get('subject', '').strip()
            
            # Validate required fields
            if not all([parent_name, parent_email, parent_phone, country, child_name, child_age, subject]):
                return JsonResponse({'success': False, 'error': 'All fields are required'})
            
            # Save to database
            from .models import EdBritishTrialRegistration
            registration = EdBritishTrialRegistration.objects.create(
                parent_name=parent_name,
                parent_email=parent_email,
                parent_phone=parent_phone,
                country=country,
                child_name=child_name,
                child_age=int(child_age),
                subject=subject
            )
            
            # Prepare email content
            email_subject = f"New Trial Class Registration - {child_name} (EdBritish Consult × Unwind Africa)"
            
            email_message = f"""
New Trial Class Registration
============================

PARENT/GUARDIAN INFORMATION:
- Full Name: {parent_name}
- Email Address: {parent_email}
- Phone Number: {parent_phone}
- Country of Residence: {country}

CHILD INFORMATION:
- Child's Name: {child_name}
- Child's Age: {child_age} years old
- Subject of Interest: {subject}

---
This registration was submitted through the Unwind Africa website partnership with EdBritish Consult.
"""
            
            # Send email notification
            try:
                send_mail(
                    email_subject,
                    email_message,
                    settings.DEFAULT_FROM_EMAIL,
                    ['unwindafrica24@gmail.com', 'info@unwindafrica.com'],
                    fail_silently=False,
                )
            except Exception as e:
                # Log error but don't fail the submission
                print(f"Email sending error: {e}")
            
            # Also send confirmation email to parent (HTML)
            try:
                from django.core.mail import EmailMultiAlternatives
                from django.template.loader import render_to_string
                
                confirmation_subject = "Registration Confirmed - EdBritish Consult × Unwind Africa Trial Class"
                
                # HTML email content
                html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Registration Confirmed</title>
</head>
<body style="margin: 0; padding: 0; font-family: 'Helvetica Neue', Arial, sans-serif; background-color: #f5f7fa; color: #333333;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f5f7fa; padding: 40px 20px;">
        <tr>
            <td align="center">
                <table width="100%" cellpadding="0" cellspacing="0" style="max-width: 600px; background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.08);">
                    <!-- Header -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #00B2FF 0%, #00C2FF 100%); padding: 40px 40px 30px; text-align: center;">
                            <h1 style="margin: 0; color: #ffffff; font-size: 28px; font-weight: 700;">Registration Confirmed!</h1>
                            <p style="margin: 10px 0 0; color: rgba(255,255,255,0.9); font-size: 16px;">EdBritish Consult × Unwind Africa</p>
                        </td>
                    </tr>
                    
                    <!-- Content -->
                    <tr>
                        <td style="padding: 40px;">
                            <p style="margin: 0 0 20px; font-size: 16px; line-height: 1.6;">
                                Dear <strong>{parent_name}</strong>,
                            </p>
                            <p style="margin: 0 0 20px; font-size: 16px; line-height: 1.6;">
                                Thank you for registering your child, <strong>{child_name}</strong>, for the free trial class! We're excited to offer this learning opportunity to diaspora children.
                            </p>
                            
                            <!-- Registration Details Box -->
                            <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f5f7fa; border-radius: 12px; margin: 30px 0;">
                                <tr>
                                    <td style="padding: 25px;">
                                        <h3 style="margin: 0 0 20px; font-size: 16px; color: #0A0B10; text-transform: uppercase; letter-spacing: 1px;">Registration Details</h3>
                                        <table width="100%" cellpadding="0" cellspacing="0">
                                            <tr>
                                                <td style="padding: 8px 0; border-bottom: 1px solid #eef0f6;">
                                                    <span style="color: #666; font-size: 14px;">Child's Name</span><br>
                                                    <strong style="font-size: 16px; color: #0A0B10;">{child_name}</strong>
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 8px 0; border-bottom: 1px solid #eef0f6;">
                                                    <span style="color: #666; font-size: 14px;">Age</span><br>
                                                    <strong style="font-size: 16px; color: #0A0B10;">{child_age} years old</strong>
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 8px 0; border-bottom: 1px solid #eef0f6;">
                                                    <span style="color: #666; font-size: 14px;">Subject of Interest</span><br>
                                                    <strong style="font-size: 16px; color: #00B2FF;">{subject}</strong>
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 8px 0;">
                                                    <span style="color: #666; font-size: 14px;">Country</span><br>
                                                    <strong style="font-size: 16px; color: #0A0B10;">{country}</strong>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            
                            <!-- What's Next -->
                            <div style="background-color: #E8F8FF; border-left: 4px solid #00B2FF; padding: 20px; border-radius: 0 12px 12px 0; margin: 30px 0;">
                                <h4 style="margin: 0 0 10px; font-size: 16px; color: #0A0B10;">📋 What's Next?</h4>
                                <p style="margin: 0; font-size: 14px; color: #333; line-height: 1.6;">
                                    Further information on how to access the trial class will be sent to your email shortly. Please keep an eye on your inbox for detailed instructions.
                                </p>
                            </div>
                            
                            <p style="margin: 30px 0 0; font-size: 14px; color: #666; line-height: 1.6;">
                                This opportunity is brought to you by <strong>Unwind Africa</strong> in partnership with <strong>EdBritish Consult</strong>.
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #0A0B10; padding: 30px 40px; text-align: center;">
                            <p style="margin: 0; color: #ffffff; font-size: 18px; font-weight: 700;">Unwind Africa</p>
                            <p style="margin: 10px 0 0; color: rgba(255,255,255,0.6); font-size: 12px;">
                                Premium Wellness Experiences Across Africa<br>
                                <a href="https://unwindafrica.com" style="color: #00B2FF; text-decoration: none;">unwindafrica.com</a>
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""
                
                # Plain text version
                text_content = f"""
Dear {parent_name},

Thank you for registering your child, {child_name}, for the free trial class!

REGISTRATION DETAILS:
- Child's Name: {child_name}
- Age: {child_age} years old
- Subject of Interest: {subject}
- Country: {country}

WHAT'S NEXT:
Further information on how to access the trial class will be sent to your email shortly.

This opportunity is brought to you by Unwind Africa in partnership with EdBritish Consult.

Best regards,
Unwind Africa Team
"""
                
                msg = EmailMultiAlternatives(
                    confirmation_subject,
                    text_content,
                    settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@unwindafrica.com',
                    [parent_email]
                )
                msg.attach_alternative(html_content, "text/html")
                msg.send(fail_silently=False)
            except Exception as e:
                print(f"Confirmation email error: {e}")
            
            return JsonResponse({'success': True})
            
        except Exception as e:
            print(f"Registration error: {e}")
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


def generate_rest_card(request, card_id):
    """Generate a digital Rest Card as PNG image"""
    from django.http import HttpResponse
    from io import BytesIO
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return HttpResponse("PIL library not available", status=500)
    
    from .models import RestCard, TokenWallet
    
    try:
        card = RestCard.objects.get(id=card_id)
        
        # Get token wallet
        try:
            wallet = TokenWallet.objects.get(member_email=card.member_email)
        except TokenWallet.DoesNotExist:
            wallet = None
            
        # Create card image
        width, height = 800, 500
        image = Image.new('RGB', (width, height), color='#ffffff')
        draw = ImageDraw.Draw(image)
        
        # Card background
        draw.rectangle([0, 0, width, height], fill='#ffffff')
        draw.rectangle([10, 10, width-10, height-10], fill='#f8f9fa', width=2)
        
        # Card header
        draw.rectangle([10, 10, width-10, 100], fill='#667eea')
        try:
            draw.text((width//2, 55), 'UNWIND AFRICA', fill='#ffffff', font=ImageFont.truetype('arial.ttf', 36), anchor='mm')
            draw.text((width//2, 80), 'REST CARD', fill='#ffffff', font=ImageFont.truetype('arial.ttf', 18), anchor='mm')
            
            # Card details
            y_offset = 120
            draw.text((20, y_offset), 'Member Name:', fill='#000000', font=ImageFont.truetype('arial.ttf', 14))
            draw.text((200, y_offset), card.member_name, fill='#000000', font=ImageFont.truetype('arial.ttf', 16))
            
            y_offset += 40
            draw.text((20, y_offset), 'Rest Card ID:', fill='#000000', font=ImageFont.truetype('arial.ttf', 14))
            draw.text((200, y_offset), card.card_number, fill='#000000', font=ImageFont.truetype('arial.ttf', 16))
            
            y_offset += 40
            draw.text((20, y_offset), 'Status:', fill='#000000', font=ImageFont.truetype('arial.ttf', 14))
            status_text = card.status.title()
            status_color = '#28a745' if card.status == 'active' else '#ffc107' if card.status == 'pending' else '#dc3545'
            draw.text((200, y_offset), status_text, fill=status_color, font=ImageFont.truetype('arial.ttf', 16))
            
            y_offset += 40
            draw.text((20, y_offset), 'Tokens Earned:', fill='#000000', font=ImageFont.truetype('arial.ttf', 14))
            tokens = wallet.tokens_earned if wallet else 0
            draw.text((200, y_offset), str(tokens), fill='#000000', font=ImageFont.truetype('arial.ttf', 16))
            
            y_offset += 40
            draw.text((20, y_offset), 'Issue Date:', fill='#000000', font=ImageFont.truetype('arial.ttf', 14))
            issue_date = card.activated_at.strftime('%B %d, %Y') if card.activated_at else '-'
            draw.text((200, y_offset), issue_date, fill='#000000', font=ImageFont.truetype('arial.ttf', 16))
        except IOError:
            # If arial.ttf not found, use default font
            draw.text((width//2, 55), 'UNWIND AFRICA', fill='#ffffff', font=ImageFont.load_default(), anchor='mm')
            draw.text((width//2, 80), 'REST CARD', fill='#ffffff', font=ImageFont.load_default(), anchor='mm')
            
            y_offset = 120
            draw.text((20, y_offset), 'Member Name:', fill='#000000', font=ImageFont.load_default())
            draw.text((200, y_offset), card.member_name, fill='#000000', font=ImageFont.load_default())
            
            y_offset += 40
            draw.text((20, y_offset), 'Rest Card ID:', fill='#000000', font=ImageFont.load_default())
            draw.text((200, y_offset), card.card_number, fill='#000000', font=ImageFont.load_default())
            
            y_offset += 40
            draw.text((20, y_offset), 'Status:', fill='#000000', font=ImageFont.load_default())
            status_text = card.status.title()
            status_color = '#28a745' if card.status == 'active' else '#ffc107' if card.status == 'pending' else '#dc3545'
            draw.text((200, y_offset), status_text, fill=status_color, font=ImageFont.load_default())
            
            y_offset += 40
            draw.text((20, y_offset), 'Tokens Earned:', fill='#000000', font=ImageFont.load_default())
            tokens = wallet.tokens_earned if wallet else 0
            draw.text((200, y_offset), str(tokens), fill='#000000', font=ImageFont.load_default())
            
            y_offset += 40
            draw.text((20, y_offset), 'Issue Date:', fill='#000000', font=ImageFont.load_default())
            issue_date = card.activated_at.strftime('%B %d, %Y') if card.activated_at else '-'
            draw.text((200, y_offset), issue_date, fill='#000000', font=ImageFont.load_default())
        
        # Save image to buffer
        buffer = BytesIO()
        image.save(buffer, format='PNG')
        buffer.seek(0)
        
        return HttpResponse(buffer, content_type='image/png')
        
    except RestCard.DoesNotExist:
        return HttpResponse("Rest Card not found", status=404)
    except Exception as e:
        return HttpResponse(f"Error generating card: {str(e)}", status=500)


# ============================================
# USER DASHBOARD VIEWS
# ============================================
import secrets
import random
from django.core.mail import send_mail
from django.conf import settings


def user_dashboard_login(request):
    """
    User dashboard login - request OTP to be sent to email
    """
    from django.http import JsonResponse
    
    if request.method == 'POST':
        import json
        try:
            data = json.loads(request.body)
            email = data.get('email', '').strip().lower()
            
            if not email:
                return JsonResponse({'success': False, 'error': 'Email is required'})
            
            # Check if user has any records (RestCard, FrozenPoints, or TokenWallet)
            from .models import (RestCard, FrozenRestPoints, TokenWallet, Vote,
                                 CommunityMember, PackageOrder, PackageCustomerCredential)

            password = data.get('password')
            if password:
                from django.contrib.auth.hashers import check_password
                credential = PackageCustomerCredential.objects.filter(email=email).first()
                if not credential or not check_password(password, credential.password_hash):
                    return JsonResponse({'success': False, 'error': 'Email or password is incorrect.'}, status=401)
                request.session['dashboard_authenticated'] = True
                request.session['dashboard_user_email'] = email
                return JsonResponse({'success': True})
            
            has_rest_card = RestCard.objects.filter(member_email=email).exists()
            has_frozen_points = FrozenRestPoints.objects.filter(member_email=email, frozen_points__gt=0).exists()
            has_token_wallet = TokenWallet.objects.filter(member_email=email).exists()
            has_existing_form = CommunityMember.objects.filter(email__iexact=email).exists()
            has_voted = Vote.objects.filter(voter_email__iexact=email).exists()
            has_package_order = PackageOrder.objects.filter(customer_email__iexact=email).exists()
            
            if not (has_rest_card or has_frozen_points or has_token_wallet or has_existing_form or has_voted or has_package_order):
                return JsonResponse({
                    'success': False, 
                    'error': 'No account found for this email. Vote in our campaigns or join our waitlist to get started!'
                })
            
            # Generate OTP
            otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            
            # Store OTP in session (for demo - in production use Redis or DB)
            request.session['dashboard_otp'] = otp
            request.session['dashboard_email'] = email
            request.session['dashboard_otp_expires'] = str(timezone.now() + timezone.timedelta(minutes=10))
            
            # Send OTP email
            try:
                send_mail(
                    'Your Unwind Africa Dashboard Login Code',
                    f'Your verification code is: {otp}\n\nThis code expires in 10 minutes.\n\nIf you did not request this, please ignore this email.',
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=True,
                )
            except Exception as e:
                print(f"OTP email error: {e}")
            
            return JsonResponse({'success': True, 'message': 'OTP sent to your email'})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


def user_dashboard_verify_otp(request):
    """
    Verify OTP and log user into dashboard
    """
    from django.http import JsonResponse
    from django.utils import timezone
    
    if request.method == 'POST':
        import json
        try:
            data = json.loads(request.body)
            otp = data.get('otp', '').strip()
            email = data.get('email', '').strip().lower()
            
            # Get stored OTP
            stored_otp = request.session.get('dashboard_otp')
            stored_email = request.session.get('dashboard_email')
            expires_str = request.session.get('dashboard_otp_expires')
            
            if not stored_otp or not expires_str:
                return JsonResponse({'success': False, 'error': 'Session expired. Please request a new code.'})
            
            # Check expiration
            expires = timezone.datetime.fromisoformat(expires_str.replace('Z', '+00:00'))
            if timezone.now() > expires:
                # Clear session
                request.session.flush()
                return JsonResponse({'success': False, 'error': 'Code expired. Please request a new one.'})
            
            # Verify OTP and email match
            if otp != stored_otp or email != stored_email:
                return JsonResponse({'success': False, 'error': 'Invalid verification code.'})
            
            # OTP verified - set dashboard session
            request.session['dashboard_authenticated'] = True
            request.session['dashboard_user_email'] = email
            
            # Clear OTP from session
            del request.session['dashboard_otp']
            del request.session['dashboard_email']
            del request.session['dashboard_otp_expires']
            
            return JsonResponse({'success': True})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


def user_dashboard(request):
    """
    Main user dashboard - shows rest points, frozen points, token wallet
    Requires email authentication via session
    """
    from .models import RestCard, FrozenRestPoints, TokenWallet, Vote, PackageOrder
    from django.db.models import Count
    from django.utils import timezone
    from datetime import timedelta
    import math
    
    # Check authentication
    email = request.session.get('dashboard_user_email')
    if not email:
        return render(request, 'Web/community/user_dashboard_login.html', {})

    def add_months(d, n):
        y = d.year + (d.month - 1 + n) // 12
        m = (d.month - 1 + n) % 12 + 1
        return d.replace(year=y, month=m)

    # Get user data
    try:
        rest_card = RestCard.objects.filter(member_email=email).first()
    except RestCard.DoesNotExist:
        rest_card = None
    
    # Get frozen points total
    frozen_entries = FrozenRestPoints.objects.filter(member_email=email)
    total_frozen_points = sum(entry.frozen_points for entry in frozen_entries)
    
    # Get token wallet
    try:
        token_wallet = TokenWallet.objects.get(member_email=email)
    except TokenWallet.DoesNotExist:
        token_wallet = None
    
    # Get recent votes
    recent_votes = Vote.objects.filter(voter_email=email).order_by('-created_at')[:10]

    # Package orders for this customer
    from .models import PackageInstalment
    package_orders = PackageOrder.objects.filter(customer_email=email).order_by('-created_at')

    # Package installments for this customer
    total_target = sum(o.grand_total for o in package_orders)
    total_saved = sum(min(o.amount_paid, o.grand_total) for o in package_orders)
    total_remaining = sum(o.outstanding_balance for o in package_orders)
    total_credit = sum(o.overpayment_credit for o in package_orders)
    overall_progress = 0
    if total_target > 0:
        overall_progress = min(100, (total_saved / total_target) * 100)
    
    # ==== Daily Action Engine ====
    # Calculate voting streak
    today = timezone.now().date()
    votes_by_user = Vote.objects.filter(voter_email=email).order_by('-created_at')
    
    streak = 0
    check_date = today
    has_voted_today = False
    
    if votes_by_user.exists():
        last_vote = votes_by_user.first()
        if last_vote.created_at.date() == today:
            has_voted_today = True
        # Count consecutive days
        for i in range(365):
            day_check = today - timedelta(days=i)
            day_votes = votes_by_user.filter(created_at__date=day_check)
            if day_votes.exists():
                streak += 1
            elif i > 0:
                break
    
    # Free vote availability
    free_votes_available = 0
    if rest_card:
        free_votes_available = rest_card.free_votes_remaining or 0
    
    # Next free vote countdown (24 hours from last vote)
    next_vote_time = None
    if not has_voted_today and votes_by_user.exists():
        last_vote = votes_by_user.first()
        next_vote_time = last_vote.created_at + timedelta(hours=24)
    
    # ==== Referral System ====
    # Count user's referrals (votes that came from this user)
    referral_count = Vote.objects.filter(referral_source__icontains=email).count()
    
    # Generate unique referral code
    import hashlib
    referral_code = hashlib.md5(email.encode()).hexdigest()[:8].upper()
    referral_link = f"{request.scheme}://{request.get_host()}/rest-card/signup/?ref={referral_code}"
    
    # ==== Points System ====
    total_points = 0
    if rest_card:
        total_points = rest_card.total_rest_points or 0
    
    # Next reward threshold (every 500 points)
    next_reward_at = math.ceil(total_points / 500) * 500 if total_points > 0 else 500
    points_to_next_reward = next_reward_at - total_points
    progress_to_next = (total_points / next_reward_at * 100) if next_reward_at > 0 else 0
    
    # Points breakdown
    points_from_votes = Vote.objects.filter(voter_email=email).aggregate(
        total=Count('id')
    )['total'] or 0
    
    # ==== Task System ====
    # Daily tasks
    daily_tasks = []
    
    # Task 1: Use free vote
    if free_votes_available > 0:
        daily_tasks.append({
            'id': 'free_vote',
            'title': 'Use your free vote',
            'description': f'You have {free_votes_available} free vote(s) available',
            'points': 50,
            'completed': False,
            'action_url': '/voting/',
            'action_label': 'Vote Now'
        })
    else:
        daily_tasks.append({
            'id': 'free_vote',
            'title': 'Use your free vote',
            'description': 'No free votes available',
            'points': 50,
            'completed': has_voted_today,
            'action_url': '/voting/',
            'action_label': 'Vote Now'
        })
    
    # Task 2: Invite a friend (if no referrals yet)
    if referral_count == 0:
        daily_tasks.append({
            'id': 'invite_friend',
            'title': 'Invite a friend',
            'description': 'Share your referral link to earn bonus points',
            'points': 100,
            'completed': False,
            'action_url': '#referral-section',
            'action_label': 'Invite'
        })
    
    # Task 3: Nominate someone
    daily_tasks.append({
        'id': 'nominate',
        'title': 'Nominate someone',
        'description': 'Nominate a deserving person for recognition',
        'points': 75,
        'completed': False,
        'action_url': '/nominate/',
        'action_label': 'Nominate'
    })
    
    # Completed daily tasks count
    completed_tasks = sum(1 for t in daily_tasks if t['completed'])
    
    # ==== Rewards Marketplace ====
    # Predefined rewards based on points
    rewards = [
        {'threshold': 500, 'name': '10% Discount', 'description': 'Get 10% off any event', 'icon': 'tag'},
        {'threshold': 1000, 'name': 'Free Entry', 'description': 'Free entry to select events', 'icon': 'ticket'},
        {'threshold': 2500, 'name': 'Wellness Session', 'description': '1-hour wellness consultation', 'icon': 'spa'},
        {'threshold': 5000, 'name': 'VIP Experience', 'description': 'VIP access to any event', 'icon': 'star'},
        {'threshold': 10000, 'name': 'Retreat Package', 'description': 'Full weekend retreat experience', 'icon': 'umbrella-beach'},
    ]
    
    # ==== Leaderboard / Social Proof ====
    # Top voters this week
    week_start = today - timedelta(days=today.weekday())
    top_voters = Vote.objects.filter(
        created_at__date__gte=week_start
    ).values('voter_email').annotate(
        vote_count=Count('id')
    ).order_by('-vote_count')[:5]
    
    # User's ranking
    user_rank = None
    for i, voter in enumerate(top_voters, 1):
        if voter['voter_email'] == email:
            user_rank = i
            break
    
    # ==== Member Tiers ====
    member_tier = 'Bronze'
    if rest_card:
        points = rest_card.total_rest_points or 0
        if points >= 5000:
            member_tier = 'Gold'
        elif points >= 2500:
            member_tier = 'Silver'
    
    # ==== Activity Feed ====
    # Build activity feed from recent votes
    activity_feed = []
    for vote in recent_votes:
        activity_feed.append({
            'type': 'vote',
            'message': f"Voted for {vote.nominee.name}",
            'points': vote.rest_points_earned or 0,
            'date': vote.created_at
        })
    
    # Add frozen points claims
    for entry in frozen_entries.filter(points_claimed=True):
        activity_feed.append({
            'type': 'claim',
            'message': f"Claimed {entry.frozen_points} frozen points",
            'points': entry.frozen_points,
            'date': entry.claimed_at
        })
    
    # Sort by date descending
    activity_feed.sort(key=lambda x: x['date'], reverse=True)
    activity_feed = activity_feed[:10]
    
    # ==== Chart-ready data ====
    # Monthly points earned (last 6 months)
    from django.db.models.functions import TruncMonth
    six_months_ago = today - timedelta(days=180)
    votes_by_month = (
        Vote.objects.filter(voter_email=email, created_at__date__gte=six_months_ago)
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(points=Sum('rest_points_earned'), count=Count('id'))
        .order_by('month')
    )
    chart_labels = []
    chart_points = []
    chart_votes = []
    month_map = {}
    for v in votes_by_month:
        key = v['month'].strftime('%b %Y')
        month_map[key] = {'points': float(v['points'] or 0), 'count': v['count']}
    # Ensure last 6 months appear
    for i in range(5, -1, -1):
        m = add_months(today.replace(day=1), -i)
        key = m.strftime('%b %Y')
        chart_labels.append(key)
        data = month_map.get(key, {'points': 0, 'count': 0})
        chart_points.append(data['points'])
        chart_votes.append(data['count'])

    # Package spending breakdown
    package_spending = [
        {'name': o.package.name, 'total': float(o.grand_total), 'paid': float(o.amount_paid)}
        for o in package_orders
    ]

    # Rest card tier progression
    tier_thresholds = {'Bronze': 0, 'Silver': 2500, 'Gold': 5000}
    current_tier_points = total_points
    tier_progress = 0
    tier_label = member_tier
    if member_tier == 'Gold':
        tier_progress = 100
    elif member_tier == 'Silver':
        tier_progress = min(100, (current_tier_points / 5000) * 100)
    elif member_tier == 'Bronze':
        tier_progress = min(100, (current_tier_points / 2500) * 100)

    context = {
        'email': email,
        'rest_card': rest_card,
        'frozen_points': total_frozen_points,
        'frozen_entries': frozen_entries,
        'token_wallet': token_wallet,
        'recent_votes': recent_votes,
        'package_orders': package_orders,
        'total_target': total_target,
        'total_saved': total_saved,
        'total_remaining': total_remaining,
        'total_credit': total_credit,
        'overall_progress': overall_progress,
        'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY,

        # Daily Action Engine
        'has_voted_today': has_voted_today,
        'voting_streak': streak,
        'free_votes_available': free_votes_available,
        'next_vote_time': next_vote_time,

        # Referral System
        'referral_count': referral_count,
        'referral_code': referral_code,
        'referral_link': referral_link,

        # Points System
        'total_points': total_points,
        'next_reward_at': next_reward_at,
        'points_to_next_reward': points_to_next_reward,
        'progress_to_next': progress_to_next,
        'points_from_votes': points_from_votes,

        # Task System
        'daily_tasks': daily_tasks,
        'completed_tasks': completed_tasks,
        'total_tasks': len(daily_tasks),

        # Rewards
        'rewards': rewards,

        # Leaderboard
        'top_voters': top_voters,
        'user_rank': user_rank,

        # Member Tier
        'member_tier': member_tier,
        'tier_progress': tier_progress,
        'tier_thresholds': tier_thresholds,

        # Activity Feed
        'activity_feed': activity_feed,

        # Charts
        'chart_labels': chart_labels,
        'chart_points': chart_points,
        'chart_votes': chart_votes,
        'package_spending': package_spending,
        'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY,
    }

    return render(request, 'Web/community/user_dashboard.html', context)


def user_dashboard_logout(request):
    """Log out from user dashboard"""
    if 'dashboard_user_email' in request.session:
        del request.session['dashboard_user_email']
    if 'dashboard_authenticated' in request.session:
        del request.session['dashboard_authenticated']
    return redirect('home')


# ============================================
# PACKAGE INSTALLMENT PAYMENTS (PAYSTACK)
# ============================================
@require_POST
def initialize_installment_payment(request, order_id):
    """
    Initialize Paystack payment for a package installment.
    Creates a pending PackagePayment record, returns authorization URL.
    """
    from .models import PackageOrder, PackagePayment
    from django.http import JsonResponse

    email = request.session.get('dashboard_user_email')
    if not email:
        return JsonResponse({'success': False, 'error': 'Not authenticated'}, status=401)

    try:
        import json
        data = json.loads(request.body)
        amount = data.get('amount')

        try:
            amount = Decimal(str(amount))
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'error': 'Invalid amount'}, status=400)

        if amount <= 0:
            return JsonResponse({'success': False, 'error': 'Amount must be greater than zero'}, status=400)

        order = get_object_or_404(PackageOrder, id=order_id, customer_email=email)

        if order.status == 'completed':
            return JsonResponse({'success': False, 'error': 'This order is already completed'}, status=400)
        if amount > order.outstanding_balance:
            return JsonResponse({'success': False, 'error': 'Payment cannot exceed the outstanding balance.'}, status=400)

        # Generate unique reference
        import secrets
        reference = f"INST-{secrets.token_urlsafe(16)}"

        # Convert to kobo (Paystack uses kobo for Naira)
        amount_in_kobo = int(amount * 100)

        paystack_secret = settings.PAYSTACK_SECRET_KEY
        if not paystack_secret:
            return JsonResponse({
                'success': False,
                'message': 'Payment gateway not configured. Please contact support.'
            }, status=500)

        # Create pending payment record
        payment = PackagePayment.objects.create(
            order=order,
            amount=amount,
            reference=reference,
            status='pending',
        )

        # Initialize Paystack payment
        headers = {
            'Authorization': f'Bearer {paystack_secret}',
            'Content-Type': 'application/json',
        }

        payload = {
            'email': email,
            'amount': amount_in_kobo,
            'reference': reference,
            'callback_url': request.build_absolute_uri(
                f'/dashboard/packages/verify/{reference}/'
            ),
            'metadata': {
                'customer_email': email,
                'customer_name': order.customer_name,
                'order_id': order.id,
                'package_name': order.package.name,
                'custom_fields': [
                    {
                        'display_name': 'Package',
                        'variable_name': 'package_name',
                        'value': order.package.name
                    },
                    {
                        'display_name': 'Order',
                        'variable_name': 'order_id',
                        'value': str(order.id)
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

        if response.status_code == 200 and response_data.get('status'):
            data = response_data['data']
            payment.paystack_reference = data.get('reference', '')
            payment.authorization_url = data.get('authorization_url', '')
            payment.paystack_response = response_data
            payment.save()
            _send_package_payment_notifications(payment, order, started=True)

            return JsonResponse({
                'success': True,
                'authorization_url': data.get('authorization_url'),
                'reference': reference,
                'amount': float(amount),
                'access_code': data.get('access_code', ''),
                'message': 'Payment initialized successfully',
            })
        else:
            payment.status = 'failed'
            payment.paystack_response = response_data
            payment.save()
            return JsonResponse({
                'success': False,
                'message': response_data.get('message', 'Payment initialization failed')
            }, status=400)

    except Exception as e:
        import traceback
        print("=" * 50)
        print("ERROR in initialize_installment_payment:")
        print(traceback.format_exc())
        print("=" * 50)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def _package_payment_admin_recipients():
    """Resolve explicit notification addresses and active staff inboxes."""
    from django.contrib.auth import get_user_model

    recipients = set(getattr(settings, 'PACKAGE_PAYMENT_NOTIFY_EMAILS', []))
    recipients.update(email for _name, email in getattr(settings, 'ADMINS', []) if email)
    User = get_user_model()
    recipients.update(
        User.objects.filter(is_active=True, is_staff=True)
        .exclude(email='').values_list('email', flat=True)
    )
    return sorted(recipients)


def _send_package_payment_notifications(payment, order, *, started=False):
    """Send retryable, idempotent email updates after Paystack events."""
    from django.utils.timezone import now

    recipients = _package_payment_admin_recipients()
    package_name = order.package.name
    reference = payment.paystack_reference or payment.reference
    amount = f'₦{payment.amount:,.0f}'

    if started and not payment.started_email_sent_at and recipients:
        subject = f'Package payment started: {package_name}'
        body = (
            'A customer has started a package payment.\n\n'
            f'Customer: {order.customer_name or "Not provided"}\n'
            f'Email: {order.customer_email}\n'
            f'Package: {package_name}\n'
            f'Order: #{order.pk}\n'
            f'Attempt amount: {amount}\n'
            f'Reference: {reference}\n'
            'State: Awaiting Paystack verification\n\n'
            'Review the package payment ledger in the Unwind Africa developer dashboard.'
        )
        try:
            if send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, recipients, fail_silently=False):
                payment.started_email_sent_at = now()
                payment.save(update_fields=['started_email_sent_at'])
        except Exception:
            logger.exception('Could not email staff about started package payment %s', reference)

    if payment.status != 'success':
        return

    if not payment.admin_confirmation_sent_at and recipients:
        subject = f'Package payment confirmed: {package_name}'
        body = (
            'Paystack has verified a package payment.\n\n'
            f'Customer: {order.customer_name or "Not provided"}\n'
            f'Email: {order.customer_email}\n'
            f'Package: {package_name}\n'
            f'Order: #{order.pk}\n'
            f'Payment received: {amount}\n'
            f'Order paid to date: ₦{order.amount_paid:,.0f}\n'
            f'Balance remaining: ₦{order.outstanding_balance:,.0f}\n'
            f'Order state: {order.get_status_display()}\n'
            f'Paystack reference: {reference}\n\n'
            'This payment was verified server-side before the order balance was updated.'
        )
        try:
            if send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, recipients, fail_silently=False):
                payment.admin_confirmation_sent_at = now()
                payment.save(update_fields=['admin_confirmation_sent_at'])
        except Exception:
            logger.exception('Could not email staff about confirmed package payment %s', reference)

    if not payment.customer_confirmation_sent_at and order.customer_email:
        completed = order.status == 'completed'
        subject = (
            f'Congratulations — your {package_name} getaway is fully paid'
            if completed else f'Payment received for your {package_name} getaway'
        )
        greeting = order.customer_name or 'there'
        completion_line = (
            'Congratulations, your getaway is fully paid and confirmed.'
            if completed else
            f'Your remaining balance is ₦{order.outstanding_balance:,.0f}. You can continue your payment plan from your Unwind Africa dashboard.'
        )
        body = (
            f'Hello {greeting},\n\n'
            f'We have confirmed your payment of {amount} for {package_name}.\n'
            f'Paid to date: ₦{order.amount_paid:,.0f}\n'
            f'Package balance: ₦{order.outstanding_balance:,.0f}\n\n'
            f'{completion_line}\n\n'
            f'Payment reference: {reference}\n'
            'Thank you for choosing Unwind Africa. We look forward to welcoming you.\n\n'
            'Unwind Africa Guest Experience Team'
        )
        try:
            if send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [order.customer_email], fail_silently=False):
                payment.customer_confirmation_sent_at = now()
                payment.save(update_fields=['customer_confirmation_sent_at'])
        except Exception:
            logger.exception('Could not email customer about confirmed package payment %s', reference)


def _confirm_package_payment(payment, response_data, paystack_data):
    """Apply one verified Paystack charge once, under row locks."""
    from .models import PackageOrder, PackagePayment, GroupGetawayEarlyAccessOffer
    from django.db import transaction as db_transaction
    from django.utils.timezone import now

    reference = payment.paystack_reference or payment.reference
    try:
        amount_kobo = int(paystack_data.get('amount') or 0)
    except (TypeError, ValueError):
        return None, False
    if not (
        paystack_data.get('status') == 'success'
        and paystack_data.get('reference') == reference
        and paystack_data.get('currency') == 'NGN'
        and amount_kobo == int(payment.amount * 100)
    ):
        return None, False

    with db_transaction.atomic():
        locked_payment = PackagePayment.objects.select_for_update().get(pk=payment.pk)
        order = PackageOrder.objects.select_for_update().get(pk=locked_payment.order_id)
        if locked_payment.status == 'success':
            return order, False

        locked_payment.status = 'success'
        locked_payment.paystack_reference = paystack_data.get('reference', reference)
        locked_payment.paystack_response = response_data
        locked_payment.paid_at = now()
        locked_payment.save(update_fields=[
            'status', 'paystack_reference', 'paystack_response', 'paid_at',
        ])

        if locked_payment.is_initial_deposit and not order.early_access_confirmed_at:
            offer, _ = GroupGetawayEarlyAccessOffer.objects.get_or_create(
                pk=1, defaults={'name': 'group-getaway-launch', 'capacity': 20, 'confirmed_count': 0}
            )
            offer = GroupGetawayEarlyAccessOffer.objects.select_for_update().get(pk=offer.pk)
            if offer.confirmed_count < offer.capacity:
                offer.confirmed_count += 1
                offer.save(update_fields=['confirmed_count'])
                order.early_access_slot = offer.confirmed_count
                order.early_access_confirmed_at = now()
                order.early_access_discount = (
                    order.package_price * Decimal('0.05')
                ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                order.grand_total = max(
                    Decimal('0'), order.grand_total - order.early_access_discount
                )

        order.amount_paid += locked_payment.amount
        order.outstanding_balance = max(
            Decimal('0'), order.grand_total - order.amount_paid
        )
        order.overpayment_credit = max(
            Decimal('0'), order.amount_paid - order.grand_total
        )
        order.status = 'completed' if order.outstanding_balance <= 0 else 'active'
        order.save()

        if locked_payment.is_initial_deposit and order.early_access_discount:
            instalments = list(
                order.instalments.select_for_update().order_by('month_number')
            )
            monthly_due = (
                order.grand_total / max(1, order.duration_months)
            ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            scheduled = Decimal('0')
            for index, instalment in enumerate(instalments):
                due = (
                    order.grand_total - scheduled
                    if index == len(instalments) - 1 else monthly_due
                )
                scheduled += due
                instalment.main_amount_due = due
                instalment.total_due = due
                instalment.save(update_fields=['main_amount_due', 'total_due'])

        remaining = locked_payment.amount
        for instalment in order.instalments.select_for_update().filter(
            status='pending'
        ).order_by('month_number'):
            if remaining <= 0:
                break
            due = max(Decimal('0'), instalment.total_due - instalment.amount_paid)
            applied = min(remaining, due)
            instalment.amount_paid += applied
            remaining -= applied
            if instalment.amount_paid >= instalment.total_due:
                instalment.status = 'paid'
                instalment.paid_at = now()
            instalment.save(update_fields=['amount_paid', 'status', 'paid_at'])

    return order, True


def verify_installment_payment(request, reference):
    """
    Verify Paystack payment for a package installment.
    Updates payment status and order amount_paid / outstanding_balance.
    """
    from .models import PackageOrder, PackagePayment, GroupGetawayEarlyAccessOffer
    from django.contrib import messages
    from django.db import transaction as db_transaction
    from django.utils.timezone import now

    ajax_request = 'application/json' in request.headers.get('Accept', '')
    try:
        payment = get_object_or_404(PackagePayment, reference=reference)
        email = request.session.get('dashboard_user_email')
        if not payment.is_initial_deposit and email != payment.order.customer_email:
            if ajax_request:
                return JsonResponse({'success': False, 'message': 'Please sign in to verify this payment.'}, status=401)
            return redirect('user_dashboard_login')

        if payment.status == 'success':
            if payment.is_initial_deposit:
                request.session['dashboard_user_email'] = payment.order.customer_email
                request.session['dashboard_authenticated'] = True
            _send_package_payment_notifications(payment, payment.order)
            if ajax_request:
                return JsonResponse({'success': True, 'already_verified': True})
            return redirect('user_dashboard')

        if not settings.PAYSTACK_SECRET_KEY:
            if ajax_request:
                return JsonResponse({'success': False, 'message': 'Payment verification is unavailable.'}, status=503)
            messages.error(request, 'Payment verification is temporarily unavailable.')
            return redirect('user_dashboard')
        response = requests.get(
            f'https://api.paystack.co/transaction/verify/{reference}',
            headers={'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}'},
            timeout=15,
        )
        response_data = response.json()
        paystack_data = response_data.get('data') or {}
        is_paid = (
            response.ok and response_data.get('status')
            and _paystack_charge_matches(
                paystack_data,
                payment.paystack_reference or payment.reference,
                payment.amount,
            )
        )
        if not is_paid:
            if paystack_data.get('status') in ('failed', 'abandoned'):
                payment.status = 'failed'
                payment.paystack_response = response_data
                payment.save(update_fields=['status', 'paystack_response'])
            if ajax_request:
                return JsonResponse({'success': False, 'message': 'Payment could not be confirmed.'}, status=400)
            messages.error(request, 'Payment could not be confirmed. Please try again or contact support.')
            return redirect('user_dashboard')

        order, _newly_confirmed = _confirm_package_payment(
            payment, response_data, paystack_data
        )
        if not order:
            if ajax_request:
                return JsonResponse({'success': False, 'message': 'Payment details did not match this order.'}, status=400)
            messages.error(request, 'Payment could not be confirmed. Please contact support if you were charged.')
            return redirect('user_dashboard')

        if payment.is_initial_deposit:
            request.session['dashboard_user_email'] = order.customer_email
            request.session['dashboard_authenticated'] = True
            _send_package_dashboard_password(order.customer_email, order.customer_name)
        payment.refresh_from_db()
        _send_package_payment_notifications(payment, order)
        if ajax_request:
            return JsonResponse({
                'success': True,
                'discount': str(order.early_access_discount),
                'early_access_slot': order.early_access_slot,
            })
        messages.success(request, f'₦{payment.amount:,.0f} payment confirmed for {order.package.name}.')
        return redirect('user_dashboard')
    except (requests.RequestException, ValueError):
        logger.exception('Unable to verify package payment with Paystack')
        if ajax_request:
            return JsonResponse({'success': False, 'message': 'Unable to reach the payment gateway.'}, status=502)
        messages.error(request, 'Unable to reach the payment gateway. Please try again shortly.')
        return redirect('user_dashboard')


def _send_package_dashboard_password(email, customer_name=''):
    """Issue a one-time dashboard password after the first deposit is verified."""
    from .models import PackageCustomerCredential
    from django.contrib.auth.hashers import make_password
    from django.utils.timezone import now

    if PackageCustomerCredential.objects.filter(email__iexact=email).exists():
        return
    temporary_password = secrets.token_urlsafe(10)
    credential = PackageCustomerCredential.objects.create(
        email=email,
        password_hash=make_password(temporary_password),
        password_sent_at=now(),
    )
    try:
        send_mail(
            'Your Unwind Africa getaway dashboard access',
            f"Hello {customer_name or 'there'},\n\nYour initial deposit is confirmed. You can access your getaway dashboard at {settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'https://unwindafrica.com/dashboard/'}\n\nEmail: {email}\nTemporary password: {temporary_password}\n\nYou can also request a one-time verification code on the dashboard login page. Keep these details private.\n\nUnwind Africa",
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
    except Exception:
        logger.exception('Unable to send package dashboard credentials to %s', email)
        # Retain the credential so the customer can still use OTP or be assisted by support.
    return credential


def claim_frozen_points(request):
    """
    Transfer frozen points to user's Rest Card when they apply
    """
    from django.http import JsonResponse
    from django.db import transaction
    from .models import RestCard, FrozenRestPoints
    
    email = request.session.get('dashboard_user_email')
    if not email:
        return JsonResponse({'success': False, 'error': 'Not authenticated'})
    
    if request.method == 'POST':
        import json
        try:
            data = json.loads(request.body)
            rest_card_id = data.get('rest_card_id')
            
            with transaction.atomic():
                # Get the rest card
                rest_card = RestCard.objects.get(id=rest_card_id, member_email=email)
                
                # Get all unclaimed frozen points
                frozen_entries = FrozenRestPoints.objects.filter(
                    member_email=email,
                    points_claimed=False,
                    frozen_points__gt=0
                )
                
                total_points = sum(entry.frozen_points for entry in frozen_entries)
                
                if total_points > 0:
                    # Transfer points to rest card
                    rest_card.total_rest_points += total_points
                    rest_card.save()
                    
                    # Mark entries as claimed
                    from django.utils.timezone import now
                    for entry in frozen_entries:
                        entry.points_claimed = True
                        entry.claimed_at = now()
                        entry.rest_card = rest_card
                        entry.save()
                
                return JsonResponse({
                    'success': True, 
                    'message': f'{total_points} points transferred to your Rest Card!',
                    'new_balance': float(rest_card.total_rest_points)
                })
                
        except RestCard.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Rest Card not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})
