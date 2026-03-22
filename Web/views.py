from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.utils import timezone
from django.utils.timezone import now
from django.db.models import Q, Count
from django.db.models.functions import TruncMonth
from datetime import date
import logging

from .models import Post, Event, BlogCategory
from .forms import PostForm, EventForm

logger = logging.getLogger(__name__)


def home(request):
    from .models import VotingCampaign, Nominee
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
    
    return render(request, 'Web/home.html', {
        'campaign': latest_campaign,
        'total_nominations': total_nominations,
        'days_remaining': days_remaining,
        'top_nominees': top_nominees,
        'active_campaigns': active_campaigns,
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
                from django.conf import settings
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=True
                )
            except Exception as email_err:
                # Log email error but don't fail the signup
                print(f"Email sending error: {email_err}")
            
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
    return render(request, 'Web/packages.html', context={})


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
    """Redirect to home page's card request section"""
    from django.shortcuts import redirect
    return redirect('/#card-request')


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
    """Payment page for votes"""
    from .models import Vote
    
    vote = get_object_or_404(Vote, id=vote_id)
    
    if request.method == 'POST':
        # Process payment (implement Paystack integration)
        payment_method = request.POST.get('payment_method')
        
        # For now, just mark as paid
        vote.payment_status = 'paid'
        vote.save()
        
        return redirect('vote_confirmation', vote_id=vote.id)
    
    context = {
        'vote': vote,
        'campaign': vote.nominee.campaign
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
    """Nomination form for couples"""
    from .models import VotingCampaign
    from .forms import NominationForm
    
    # Get active campaign
    campaign = VotingCampaign.objects.filter(is_active=True).order_by('-start_date').first()
    
    if not campaign:
        return render(request, 'Web/nominate.html', {'campaign': None, 'error': 'No active campaign'})
    
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
            from .models import RestCard, FrozenRestPoints, TokenWallet
            
            has_rest_card = RestCard.objects.filter(member_email=email).exists()
            has_frozen_points = FrozenRestPoints.objects.filter(member_email=email, frozen_points__gt=0).exists()
            has_token_wallet = TokenWallet.objects.filter(member_email=email).exists()
            
            if not (has_rest_card or has_frozen_points or has_token_wallet):
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
    from .models import RestCard, FrozenRestPoints, TokenWallet, Vote
    
    # Check authentication
    email = request.session.get('dashboard_user_email')
    if not email:
        return render(request, 'Web/community/user_dashboard_login.html', {})
    
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
    
    context = {
        'email': email,
        'rest_card': rest_card,
        'frozen_points': total_frozen_points,
        'frozen_entries': frozen_entries,
        'token_wallet': token_wallet,
        'recent_votes': recent_votes,
    }
    
    return render(request, 'Web/community/user_dashboard.html', context)


def user_dashboard_logout(request):
    """Log out from user dashboard"""
    if 'dashboard_user_email' in request.session:
        del request.session['dashboard_user_email']
    if 'dashboard_authenticated' in request.session:
        del request.session['dashboard_authenticated']
    return redirect('home')


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

