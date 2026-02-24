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
    if request.method == 'POST':
        try:
            # Create or update RestCard
            email = request.POST.get('email')
            name = request.POST.get('name')
            phone = request.POST.get('phone')
            
            if not email or not name or not phone:
                return JsonResponse({
                    'success': False,
                    'message': 'Please fill in all required fields'
                }, status=400)
            
            # Check if already exists
            rest_card, created = RestCard.objects.get_or_create(
                member_email=email,
                defaults={
                    'member_name': name,
                    'member_phone': phone,
                    'status': 'waitlist'
                }
            )
            
            if not created:
                # Update existing record
                rest_card.member_name = name
                rest_card.member_phone = phone
                rest_card.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Thank you for signing up! We will contact you soon with updates about your Rest Card.',
                'waitlist_position': rest_card.waitlist_position
            })
        
        except Exception as e:
            logger.error(f"Error processing rest card signup: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': 'Something went wrong. Please try again.'
            }, status=500)
    
    return render(request, 'Web/rest_card_signup.html')


def about(request):
    return render(request, 'Web/about.html', context={})


def raising_readers(request):
    return render(request, 'Web/raising_readers.html', context={})


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
    try:
        send_mail(subject, body, "no-reply@unwindafrica.com", ["hello@unwindafrica.com"], fail_silently=True)
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
        send_mail(subject_admin, body_admin, "no-reply@unwindafrica.com", ["clientservicesunwindafrica@gmail.com"], fail_silently=False)

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
            f"Phone: +234 123 456 7890\n"
            f"Email: hello@unwindafrica.com"
        )
        send_mail(subject_user, body_user, "no-reply@unwindafrica.com", [email], fail_silently=False)

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
    
    # Get active campaign
    campaign = VotingCampaign.objects.filter(is_active=True).order_by('-start_date').first()
    
    if not campaign:
        return render(request, 'Web/vote.html', {'campaign': None, 'error': 'No active campaign'})
    
    # Get all nominees for the campaign
    nominees = Nominee.objects.filter(campaign=campaign).order_by('number')
    
    context = {
        'campaign': campaign,
        'nominees': nominees
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

