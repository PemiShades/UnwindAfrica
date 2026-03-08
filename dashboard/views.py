# dashboard/views.py
from datetime import date, timedelta
from collections import Counter
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST, require_http_methods
from django.http import JsonResponse
from django.utils.text import slugify
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth import login as auth_login
from django.db.models import Avg, Count, Sum
from django.utils.timezone import now

from .models import Post, Event
from .forms import PostForm, EventForm, AdminAuthenticationForm, VotingCampaignForm, NomineeForm
from Web.models import PageView, Session, VotingCampaign, Nominee, Vote, Transaction, Book


def _ensure_unique_slug(instance, base_text: str):
    """
    Ensure a unique slug for the instance, based on base_text (usually the title).
    Works with proxy model pointing to your concrete model that actually stores "slug".
    """
    base = slugify(base_text or "post") or "post"
    slug = base
    Model = instance.__class__
    i = 1
    while Model.objects.filter(slug=slug).exclude(pk=instance.pk).exists():
        i += 1
        slug = f"{base}-{i}"
    instance.slug = slug

def _calculate_avg_session_duration(sessions_qs):
    """Calculate average session duration in minutes"""
    if not sessions_qs.exists():
        return 0

    # Calculate duration for each session
    durations = []
    for session in sessions_qs:
        duration = session.duration  # in seconds
        if duration > 0:  # Only count sessions with activity
            durations.append(duration / 60)  # Convert to minutes

    return round(sum(durations) / len(durations), 1) if durations else 0


def _get_top_pages(since_date):
    """Get top 5 most visited pages"""
    top_pages = PageView.objects.filter(timestamp__gte=since_date)\
        .values('url')\
        .annotate(views=Count('id'))\
        .order_by('-views')[:5]

    return list(top_pages)


def add_months(d, n):
    """Add n months to date d"""
    y = d.year + (d.month - 1 + n) // 12
    m = (d.month - 1 + n) % 12 + 1
    return d.replace(year=y, month=m)


@login_required
def dashboard_home(request):
    from collections import Counter
    posts_qs = Post.objects.all().order_by("-created_at")
    events_qs = Event.objects.all().order_by("-created_at")

    # Forms required by includes (even if tab is hidden by Alpine)
    post_form = PostForm()
    event_form = EventForm()

    # Calculate real analytics data
    # Sessions from last 30 days
    thirty_days_ago = now() - timedelta(days=30)
    recent_sessions = Session.objects.filter(start_time__gte=thirty_days_ago)
    total_sessions = recent_sessions.count()

    # Bounce rate: sessions with only 1 page view - optimized with aggregate
    from django.db.models import Count
    bounce_sessions = recent_sessions.filter(page_views__lte=1).count()
    bounce_rate = (bounce_sessions / total_sessions * 100) if total_sessions > 0 else 0

    # Page views from last 30 days - optimized with aggregate
    recent_page_views = PageView.objects.filter(timestamp__gte=thirty_days_ago).count()

    # KPIs (align with index.html keys) - optimized to avoid multiple queries
    kpis = {
        "total_sessions": total_sessions,
        "events_count": events_qs.count(),
        "pending_events": 0,  # Could be used for events awaiting approval
        "bounce_rate": round(bounce_rate, 1),
        "posts_total": posts_qs.count(),
        "posts_published": posts_qs.filter(is_published=True).count(),
        "posts_featured": posts_qs.filter(is_featured=True).count(),
        "events_upcoming": events_qs.filter(
            date__gte=date.today(),
            date__lte=date.today() + timedelta(days=60)
        ).count(),
        # Additional metrics
        "page_views_30d": recent_page_views,
        "avg_session_duration": _calculate_avg_session_duration(recent_sessions),
        "top_pages": _get_top_pages(thirty_days_ago),
    }

    # Categories chart - optimized with values_list
    cats = list(posts_qs.values_list('category', flat=True))
    category_chart_labels = sorted(set(cats))
    category_chart_counts = [cats.count(c) for c in category_chart_labels]

    # Monthly chart (last 12 months) - Posts - optimized with values and annotate
    from django.db.models.functions import TruncMonth
    posts_by_month = posts_qs.annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(count=Count('id'))
    
    first_of_this_month = date.today().replace(day=1)
    monthly_chart_labels, monthly_chart_counts = [], []
    posts_by_month_dict = {p['month'].strftime('%Y-%m'): p['count'] for p in posts_by_month if p['month']}
    for i in range(-11, 1):
        d = add_months(first_of_this_month, i)
        key = d.strftime("%Y-%m")
        monthly_chart_labels.append(d.strftime("%b %Y"))
        monthly_chart_counts.append(posts_by_month_dict.get(key, 0))

    # Voting data
    from Web.models import VotingCampaign, Nominee, Vote, Transaction
    campaigns = VotingCampaign.objects.all().order_by('-start_date')
    nominees = Nominee.objects.all().order_by('-vote_count')
    votes = Vote.objects.all().order_by('-created_at')
    transactions = Transaction.objects.all().order_by('-created_at')
    
    # Calculate total revenue from successful transactions
    total_revenue = Transaction.objects.filter(status='success').aggregate(total=Sum('amount'))['total'] or 0
    
    # EdBritish Trial Registrations
    from Web.models import EdBritishTrialRegistration
    trial_registrations = EdBritishTrialRegistration.objects.all().order_by('-created_at')[:50]
    
    # Engagement chart data: monthly vote counts
    votes_by_month = Counter(v.created_at.strftime("%Y-%m") for v in votes)
    first_of_this_month = date.today().replace(day=1)
    votes_monthly_labels, votes_monthly_counts = [], []
    for i in range(-11, 1):
        d = add_months(first_of_this_month, i)
        key = d.strftime("%Y-%m")
        votes_monthly_labels.append(d.strftime("%b %Y"))
        votes_monthly_counts.append(votes_by_month.get(key, 0))
    
    # Rest Cards data
    from Web.models import RestCard
    rest_cards = RestCard.objects.all().order_by('-activated_at')
    active_cards = rest_cards.filter(status='active')
    pending_cards = rest_cards.filter(status='pending')
    total_rest_points = RestCard.objects.aggregate(total=Sum('total_rest_points'))['total'] or 0
    
    # Books data
    books = Book.objects.all().order_by('-created_at')
    books_available = books.filter(status='available').count()
    books_on_loan = books.filter(status='on_loan').count()
    
    # Calculate average votes per nominee
    avg_votes_per_nominee = 0
    if nominees.count() > 0:
        avg_votes_per_nominee = round(votes.count() / nominees.count())
    
    # Nominee chart data (top 10 nominees by votes)
    top_nominees = nominees[:10]
    nominee_chart_labels = [nominee.name for nominee in top_nominees]
    nominee_chart_counts = [nominee.vote_count for nominee in top_nominees]
    
    # Campaign votes chart data
    campaign_vote_chart_labels = [campaign.name for campaign in campaigns]
    campaign_vote_chart_counts = []
    for campaign in campaigns:
        campaign_vote_chart_counts.append(Vote.objects.filter(nominee__campaign=campaign).count())
    
    # Votes monthly trends chart data
    votes_monthly_labels, votes_monthly_counts = [], []
    first_of_this_month = date.today().replace(day=1)
    for i in range(-11, 1):
        d = add_months(first_of_this_month, i)
        key = d.strftime("%Y-%m")
        votes_monthly_labels.append(d.strftime("%b %Y"))
        # Count votes in this month
        month_votes = Vote.objects.filter(
            created_at__year=d.year,
            created_at__month=d.month
        ).count()
        votes_monthly_counts.append(month_votes)
    
    ctx = {
        "posts": list(posts_qs[:18]),
        "events": events_qs[:12],
        "kpis": kpis,
        "category_chart_labels": category_chart_labels,
        "category_chart_counts": category_chart_counts,
        "monthly_chart_labels": monthly_chart_labels,
        "monthly_chart_counts": monthly_chart_counts,
        "nominee_chart_labels": nominee_chart_labels,
        "nominee_chart_counts": nominee_chart_counts,
        "campaign_vote_chart_labels": campaign_vote_chart_labels,
        "campaign_vote_chart_counts": campaign_vote_chart_counts,
        "votes_monthly_labels": votes_monthly_labels,
        "votes_monthly_counts": votes_monthly_counts,
        "post_form": post_form,
        "event_form": event_form,
        "campaigns": campaigns,
        "nominees": nominees,
        "votes": votes,
        "transactions": transactions,
        "total_revenue": total_revenue,
        "rest_cards": rest_cards,
        "active_cards": active_cards,
        "pending_cards": pending_cards,
        "total_rest_points": total_rest_points,
        "books": books,
        "books_available": books_available,
        "books_on_loan": books_on_loan,
        "avg_votes_per_nominee": avg_votes_per_nominee,
        "trial_registrations": trial_registrations,
    }
    return render(request, "dashboard/index.html", ctx)


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard_home")

    form = AdminAuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        auth_login(request, form.get_user())
        return redirect("dashboard_home")

    return render(request, "dashboard/login.html", {"form": form})


@require_POST
@login_required
def create_blog(request):
    """Create a new blog post via AJAX"""
    try:
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            action = request.POST.get("action", "draft")
            post.is_published = (action == "publish")
            
            # Ensure unique slug
            if not post.slug:
                _ensure_unique_slug(post, post.title or "post")
            
            post.save()
            return JsonResponse({"ok": True})
        
        # Return form errors
        errors = {field: error[0] for field, error in form.errors.items()}
        return JsonResponse({"ok": False, "error": "Invalid form", "errors": errors}, status=400)
    
    except Exception as e:
        # Log the error in production
        print(f"Error creating blog: {e}")
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


@require_POST
@login_required
def edit_blog(request, slug):
    """Edit an existing blog post via AJAX"""
    try:
        post = get_object_or_404(Post, slug=slug)
        form = PostForm(request.POST, request.FILES, instance=post)
        
        if form.is_valid():
            post = form.save(commit=False)
            action = request.POST.get("action", "draft")
            
            if action in {"publish", "draft"}:
                post.is_published = (action == "publish")
            
            # Ensure slug is still unique if title changed
            if not post.slug or form.has_changed() and 'title' in form.changed_data:
                _ensure_unique_slug(post, post.title or "post")
            
            post.save()
            return JsonResponse({"ok": True})
        
        # Return form errors
        errors = {field: error[0] for field, error in form.errors.items()}
        return JsonResponse({"ok": False, "error": "Invalid form", "errors": errors}, status=400)
    
    except Exception as e:
        print(f"Error editing blog: {e}")
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


@require_POST
@login_required
def delete_blog(request, slug):
    get_object_or_404(Post, slug=slug).delete()
    return redirect("dashboard_home")


@require_POST
@login_required
def toggle_feature(request, slug):
    post = get_object_or_404(Post, slug=slug)
    post.is_featured = not post.is_featured
    post.save(update_fields=["is_featured"])
    return redirect("dashboard_home")


# ---------- Events ----------
@require_POST
@login_required
def create_event(request):
    """Create a new event via AJAX"""
    try:
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            # Ensure unique slug
            if not event.slug:
                _ensure_unique_slug(event, event.name or "event")
            event.save()
            return JsonResponse({"ok": True})

        # Return form errors
        errors = {field: error[0] for field, error in form.errors.items()}
        return JsonResponse({"ok": False, "error": "Invalid form", "errors": errors}, status=400)

    except Exception as e:
        print(f"Error creating event: {e}")
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


@login_required
def edit_event(request, identifier):
    """Edit an existing event via AJAX"""
    try:
        # Try slug first, then pk
        try:
            event = get_object_or_404(Event, slug=identifier)
        except:
            event = get_object_or_404(Event, pk=identifier)

        if request.method == "POST":
            form = EventForm(request.POST, request.FILES, instance=event)
            if form.is_valid():
                event = form.save(commit=False)
                # Ensure slug is still unique if name changed
                if not event.slug or form.has_changed() and 'name' in form.changed_data:
                    _ensure_unique_slug(event, event.name or "event")
                event.save()
                return JsonResponse({"ok": True})

            # Return form errors
            errors = {field: error[0] for field, error in form.errors.items()}
            return JsonResponse({"ok": False, "error": "Invalid form", "errors": errors}, status=400)

    except Exception as e:
        print(f"Error editing event: {e}")
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


@require_POST
@login_required
def delete_event(request, identifier):
    try:
        # Try slug first, then pk
        try:
            event = get_object_or_404(Event, slug=identifier)
        except:
            event = get_object_or_404(Event, pk=identifier)
        event.delete()
        return JsonResponse({"ok": True})
    except Exception as e:
        print(f"Error deleting event: {e}")
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


# ---------- API ----------
def engagement_api(request):
    data = {
        "posts_total": Post.objects.count(),
        "posts_published": Post.objects.filter(is_published=True).count(),
        "events_next_30_days": Event.objects.filter(
            date__gte=date.today(), 
            date__lte=date.today() + timedelta(days=30)
        ).count(),
    }
    return JsonResponse(data)


@login_required
def voting_dashboard(request):
    """Voting dashboard: view campaigns, nominees, and votes"""
    campaigns = VotingCampaign.objects.all().order_by('-start_date')
    nominees = Nominee.objects.all().order_by('-vote_count')
    votes = Vote.objects.all().order_by('-created_at')
    transactions = Transaction.objects.all().order_by('-created_at')
    
    # Calculate total revenue
    total_revenue = Transaction.objects.filter(status='success').aggregate(total=Sum('amount'))['total'] or 0
    
    # Prepare chart data for nominees
    nominee_names = [f"{n.name} ({n.campaign.name})" for n in nominees[:15]]
    nominee_votes = [n.vote_count for n in nominees[:15]]
    
    # Prepare chart data for votes by campaign
    from collections import Counter
    campaign_votes = Counter(v.nominee.campaign.name for v in votes)
    campaign_names = sorted(campaign_votes.keys())
    campaign_vote_counts = [campaign_votes[c] for c in campaign_names]
    
    # Prepare chart data for votes over time (last 12 months)
    def add_months(d, n):
        y = d.year + (d.month - 1 + n) // 12
        m = (d.month - 1 + n) % 12 + 1
        return d.replace(year=y, month=m)
    
    votes_by_month = Counter(v.created_at.strftime("%Y-%m") for v in votes)
    first_of_this_month = date.today().replace(day=1)
    monthly_labels, monthly_counts = [], []
    for i in range(-11, 1):
        d = add_months(first_of_this_month, i)
        key = d.strftime("%Y-%m")
        monthly_labels.append(d.strftime("%b %Y"))
        monthly_counts.append(votes_by_month.get(key, 0))
    
    # Campaign form
    if request.method == 'POST' and 'create_campaign' in request.POST:
        form = VotingCampaignForm(request.POST, request.FILES)
        if form.is_valid():
            campaign = form.save(commit=False)
            if not campaign.slug:
                _ensure_unique_slug(campaign, campaign.name or "campaign")
            campaign.save()
            return redirect('voting_dashboard')
    else:
        form = VotingCampaignForm()
    
    context = {
        'campaigns': campaigns,
        'nominees': nominees,
        'votes': votes,
        'transactions': transactions,
        'total_revenue': total_revenue,
        'campaign_form': form,
        'nominee_chart_labels': nominee_names,
        'nominee_chart_counts': nominee_votes,
        'campaign_vote_chart_labels': campaign_names,
        'campaign_vote_chart_counts': campaign_vote_counts,
        'votes_monthly_labels': monthly_labels,
        'votes_monthly_counts': monthly_counts,
    }
    
    return render(request, 'dashboard/voting.html', context)


@login_required
def view_campaign_voters(request, slug):
    """View all voters for a specific campaign"""
    campaign = get_object_or_404(VotingCampaign, slug=slug)
    voters = Vote.objects.filter(nominee__campaign=campaign).order_by('-created_at')
    
    context = {
        'campaign': campaign,
        'voters': voters,
    }
    
    return render(request, 'dashboard/view_campaign_voters.html', context)


@require_POST
@login_required
def create_campaign(request):
    """Create a new voting campaign via AJAX"""
    try:
        form = VotingCampaignForm(request.POST, request.FILES)
        if form.is_valid():
            campaign = form.save(commit=False)
            if not campaign.slug:
                _ensure_unique_slug(campaign, campaign.name or "campaign")
            campaign.save()
            return JsonResponse({"ok": True})
        
        errors = {field: error[0] for field, error in form.errors.items()}
        return JsonResponse({"ok": False, "error": "Invalid form", "errors": errors}, status=400)
    
    except Exception as e:
        print(f"Error creating campaign: {e}")
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


@login_required
def edit_campaign(request, slug):
    """Edit an existing voting campaign via AJAX"""
    try:
        campaign = get_object_or_404(VotingCampaign, slug=slug)
        
        if request.method == "POST":
            form = VotingCampaignForm(request.POST, request.FILES, instance=campaign)
            if form.is_valid():
                campaign = form.save(commit=False)
                if not campaign.slug or form.has_changed() and 'name' in form.changed_data:
                    _ensure_unique_slug(campaign, campaign.name or "campaign")
                campaign.save()
                
                # Check if it's an AJAX request
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({"ok": True})
                else:
                    # Regular form submission - redirect back to dashboard
                    return redirect('voting_dashboard')
            
            errors = {field: error[0] for field, error in form.errors.items()}
            return JsonResponse({"ok": False, "error": "Invalid form", "errors": errors}, status=400)
    
    except Exception as e:
        print(f"Error editing campaign: {e}")
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


@require_POST
@login_required
def delete_campaign(request, slug):
    """Delete a voting campaign"""
    try:
        campaign = get_object_or_404(VotingCampaign, slug=slug)
        campaign.delete()
        return JsonResponse({"ok": True})
    except Exception as e:
        print(f"Error deleting campaign: {e}")
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


@login_required
@require_POST
def delete_nominee(request, nominee_id):
    """Delete a nominee by ID and renumber remaining nominees in the campaign.

    After deletion, nominee numbers are re-assigned sequentially (001, 002, ...)
    within the same campaign to avoid gaps.
    """
    try:
        nominee = get_object_or_404(Nominee, pk=nominee_id)
        campaign = nominee.campaign

        # Delete the nominee
        nominee.delete()

        # Renumber remaining nominees for the campaign
        remaining = Nominee.objects.filter(campaign=campaign).order_by('order', 'created_at', 'pk')
        for idx, n in enumerate(remaining, start=1):
            new_number = str(idx).zfill(3)
            if (n.number or '') != new_number:
                n.number = new_number
                n.save(update_fields=['number'])

        return JsonResponse({"ok": True, "message": "Nominee deleted and numbers refreshed"})
    except Exception as e:
        print(f"Error deleting nominee: {e}")
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


@login_required
def edit_nominee(request, nominee_id):
    """Edit an existing nominee via AJAX - used for updating stories"""
    try:
        nominee = get_object_or_404(Nominee, pk=nominee_id)
        
        if request.method == "POST":
            # Check if JSON or form data
            if request.headers.get('Content-Type') == 'application/json':
                import json
                try:
                    data = json.loads(request.body)
                except json.JSONDecodeError:
                    return JsonResponse({"ok": False, "error": "Invalid JSON"}, status=400)
                
                # Update fields directly from JSON
                nominee.name = data.get('name', nominee.name)
                nominee.number = data.get('number', nominee.number or '')
                nominee.story = data.get('story', nominee.story or '')
                nominee.instagram_handle = data.get('instagram_handle', nominee.instagram_handle or '')
                nominee.order = int(data.get('order', nominee.order))
                nominee.save()
                return JsonResponse({"ok": True, "message": "Nominee updated successfully"})
            else:
                # Form submission
                form = NomineeForm(request.POST, request.FILES, instance=nominee)
                if form.is_valid():
                    form.save()
                    return JsonResponse({"ok": True, "message": "Nominee updated successfully"})
                
                errors = {field: error[0] for field, error in form.errors.items()}
                return JsonResponse({"ok": False, "error": "Invalid form", "errors": errors}, status=400)
        
        # For GET request, return nominee data as JSON
        return JsonResponse({
            "ok": True,
            "nominee": {
                "id": nominee.id,
                "name": nominee.name,
                "number": nominee.number,
                "story": nominee.story,
                "instagram_handle": nominee.instagram_handle,
                "order": nominee.order,
                "campaign": nominee.campaign.name,
            }
        })
    
    except Exception as e:
        print(f"Error editing nominee: {e}")
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


@login_required
def get_nominees_by_campaign(request, campaign_slug):
    """Get all nominees for a specific campaign"""
    try:
        campaign = get_object_or_404(VotingCampaign, slug=campaign_slug)
        nominees = Nominee.objects.filter(campaign=campaign).order_by('order', 'name')
        
        nominees_data = []
        for n in nominees:
            nominees_data.append({
                "id": n.id,
                "name": n.name,
                "number": n.number,
                "story": n.story,
                "instagram_handle": n.instagram_handle,
                "order": n.order,
                "vote_count": n.vote_count,
            })
        
        return JsonResponse({
            "ok": True,
            "campaign": {"id": campaign.id, "name": campaign.name},
            "nominees": nominees_data
        })
    except Exception as e:
        print(f"Error getting nominees: {e}")
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


# ---------- Rest Card Management ----------
from Web.models import RestCard

import random
from django.utils import timezone

@login_required
@require_http_methods(["GET", "POST"])
def edit_rest_card(request, card_id):
    """Edit a rest card"""
    try:
        card = get_object_or_404(RestCard, pk=card_id)
        
        if request.method == 'GET':
            # Return card data for editing
            return JsonResponse({
                "ok": True,
                "card": {
                    "id": card.pk,
                    "member_name": card.member_name,
                    "member_email": card.member_email,
                    "member_phone": card.member_phone,
                    "status": card.status
                }
            })
        
        # Parse JSON data if sent
        import json
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            member_name = data.get('member_name', '').strip()
            member_email = data.get('member_email', '').strip()
            member_phone = data.get('member_phone', '').strip()
        else:
            # Fallback to form data
            member_name = request.POST.get('member_name', '').strip()
            member_email = request.POST.get('member_email', '').strip()
            member_phone = request.POST.get('member_phone', '').strip()
        
        if member_name:
            card.member_name = member_name
        if member_email:
            card.member_email = member_email
        if member_phone:
            card.member_phone = member_phone
        
        card.save()
        return JsonResponse({"ok": True, "message": "Card updated successfully"})
    
    except Exception as e:
        print(f"Error editing rest card: {e}")
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def generate_rest_card(request, card_id):
    """Generate a rest card"""
    try:
        card = get_object_or_404(RestCard, pk=card_id)
        # In a real implementation, this would generate a PDF or image of the card
        # For now, we'll just return a success message
        return JsonResponse({"ok": True, "message": "Card generated successfully"})
    
    except Exception as e:
        print(f"Error generating rest card: {e}")
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def resend_rest_card(request, card_id):
    """Resend rest card details to the member"""
    try:
        card = get_object_or_404(RestCard, pk=card_id)
        # In a real implementation, this would send an email with the card details
        # For now, we'll just return a success message
        return JsonResponse({"ok": True, "message": "Card details resent successfully"})
    
    except Exception as e:
        print(f"Error resending rest card: {e}")
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def toggle_rest_card_status(request, card_id):
    """Activate or deactivate a rest card"""
    try:
        card = get_object_or_404(RestCard, pk=card_id)
        if card.status == 'active':
            card.status = 'suspended'
            message = "Card deactivated successfully"
        else:
            card.status = 'active'
            message = "Card activated successfully"
        card.save()
        return JsonResponse({"ok": True, "message": message, "new_status": card.status})
    
    except Exception as e:
        print(f"Error toggling rest card status: {e}")
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


@login_required
def get_rest_card(request, card_id):
    """Return rest card data (GET) for modal editing"""
    try:
        if request.method != 'GET':
            return JsonResponse({"ok": False, "error": "Method not allowed"}, status=405)
        card = get_object_or_404(RestCard, pk=card_id)
        return JsonResponse({
            "ok": True,
            "card": {
                "id": card.pk,
                "member_name": card.member_name,
                "member_email": card.member_email,
                "member_phone": card.member_phone,
                "status": card.status
            }
        })
    except Exception as e:
        print(f"Error fetching rest card: {e}")
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


@login_required
@require_POST
def create_rest_card(request):
    """Create a new rest card via AJAX"""
    try:
        import json
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            member_name = data.get('member_name', '').strip()
            member_email = data.get('member_email', '').strip()
            member_phone = data.get('member_phone', '').strip()
        else:
            member_name = request.POST.get('member_name', '').strip()
            member_email = request.POST.get('member_email', '').strip()
            member_phone = request.POST.get('member_phone', '').strip()

        # generate unique 16-digit card number
        def gen_number():
            return ''.join(str(random.randint(0,9)) for _ in range(16))

        card_number = gen_number()
        while RestCard.objects.filter(card_number=card_number).exists():
            card_number = gen_number()

        card = RestCard.objects.create(
            card_number=card_number,
            member_name=member_name or 'New Member',
            member_email=member_email or '',
            member_phone=member_phone or '',
            status='active',
            activated_at=timezone.now()
        )

        return JsonResponse({
            'ok': True,
            'card': {
                'id': card.pk,
                'card_number': card.card_number,
                'member_name': card.member_name,
                'member_email': card.member_email,
                'member_phone': card.member_phone,
                'status': card.status,
                'total_rest_points': card.total_rest_points,
                'activated_at': card.activated_at.strftime('%b %d, %Y') if card.activated_at else '-'
            }
        })
    except Exception as e:
        print(f"Error creating rest card: {e}")
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


@login_required
def export_rest_cards(request):
    """Export all rest cards to CSV"""
    try:
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="rest_cards.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Card ID', 'Member Name', 'Member Email', 'Member Phone', 'Status', 'Created At', 'Activated At'])
        
        for card in RestCard.objects.all():
            writer.writerow([
                card.pk,
                card.member_name,
                card.member_email,
                card.member_phone,
                card.status,
                card.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                card.activated_at.strftime('%Y-%m-%d %H:%M:%S') if card.activated_at else ''
            ])
        
        return response
    
    except Exception as e:
        print(f"Error exporting rest cards: {e}")
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def import_rest_cards(request):
    """Import rest cards from CSV file"""
    try:
        if 'file' not in request.FILES:
            return JsonResponse({"ok": False, "error": "No file uploaded"}, status=400)
        
        import csv
        from io import TextIOWrapper
        
        file = request.FILES['file']
        if not file.name.endswith('.csv'):
            return JsonResponse({"ok": False, "error": "File must be a CSV"}, status=400)
        
        reader = csv.DictReader(TextIOWrapper(file, encoding='UTF-8'))
        imported_count = 0
        errors = []
        
        for row in reader:
            try:
                # Create or update rest card
                card, created = RestCard.objects.update_or_create(
                    pk=row.get('Card ID') if row.get('Card ID') else None,
                    defaults={
                        'member_name': row.get('Member Name', '').strip(),
                        'member_email': row.get('Member Email', '').strip(),
                        'member_phone': row.get('Member Phone', '').strip(),
                        'status': row.get('Status', 'pending').lower()
                    }
                )
                imported_count += 1
            except Exception as e:
                errors.append(f"Error processing row: {str(e)}")
        
        return JsonResponse({
            "ok": True, 
            "message": f"Imported {imported_count} cards", 
            "errors": errors
        })
    except Exception as e:
        print(f"Error importing rest cards: {e}")
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


@login_required
def rest_cards_stats(request):
    """Return simple counts for rest-cards KPIs (AJAX)"""
    try:
        total = RestCard.objects.count()
        active = RestCard.objects.filter(status='active').count()
        pending = RestCard.objects.filter(status='pending').count()
        total_points = RestCard.objects.aggregate(total=Sum('total_rest_points'))['total'] or 0
        return JsonResponse({"ok": True, "total": total, "active": active, "pending": pending, "total_points": total_points})
    except Exception as e:
        print(f"Error fetching rest cards stats: {e}")
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


@login_required
def engagement_data(request):
    """Return monthly engagement (votes) labels and counts for chart polling"""
    try:
        from Web.models import Vote
        from collections import Counter
        from datetime import date

        votes = Vote.objects.all()
        by_month = Counter(v.created_at.strftime("%Y-%m") for v in votes)

        def add_months(d, n):
            y = d.year + (d.month - 1 + n) // 12
            m = (d.month - 1 + n) % 12 + 1
            return d.replace(year=y, month=m)

        first_of_this_month = date.today().replace(day=1)
        monthly_chart_labels, monthly_chart_counts = [], []
        for i in range(-11, 1):
            d = add_months(first_of_this_month, i)
            key = d.strftime("%Y-%m")
            monthly_chart_labels.append(d.strftime("%b %Y"))
            monthly_chart_counts.append(by_month.get(key, 0))

        return JsonResponse({"ok": True, "labels": monthly_chart_labels, "counts": monthly_chart_counts})
    except Exception as e:
        print(f"Error fetching engagement data: {e}")
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


@login_required
def get_nominee_details(request, nominee_id):
    """API: Get nominee details with all votes"""
    try:
        nominee = get_object_or_404(Nominee, pk=nominee_id)
        votes = nominee.votes.all().order_by('-created_at')
        
        votes_data = []
        for vote in votes:
            votes_data.append({
                'id': vote.id,
                'voter_name': vote.voter_name,
                'voter_email': vote.voter_email,
                'voter_phone': vote.voter_phone,
                'votes': vote.vote_quantity,
                'amount': float(vote.amount),
                'status': vote.payment_status,
                'date': vote.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        return JsonResponse({
            'ok': True,
            'nominee': {
                'id': nominee.id,
                'number': nominee.number or '',
                'name': nominee.name,
                'photo': nominee.photo.url if nominee.photo else '',
                'votes_count': nominee.vote_count,
                'total_raised': float(nominee.total_amount_raised),
                'story': nominee.story,
                'instagram_handle': nominee.instagram_handle or '',
                'instagram_url': nominee.instagram_url or '',
                'campaign': nominee.campaign.name if nominee.campaign else '',
                'created_at': nominee.created_at.strftime('%B %d, %Y'),
                'votes': votes_data
            }
        })
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=400)


@login_required
@require_POST
def delete_vote(request, vote_id):
    """API: Delete a vote and update nominee count"""
    try:
        vote = get_object_or_404(Vote, pk=vote_id)
        nominee = vote.nominee
        
        # Delete transaction if exists
        if hasattr(vote, 'transaction'):
            vote.transaction.delete()
        
        vote.delete()
        
        # Update nominee vote count
        nominee.vote_count = nominee.votes.count()
        nominee.save()
        
        return JsonResponse({'ok': True, 'msg': 'Vote deleted'})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=400)


@login_required
def get_nominees_data(request):
    """API: Get all nominees with vote counts for dashboard"""
    try:
        campaign_id = request.GET.get('campaign_id')
        nominees = Nominee.objects.all()
        
        if campaign_id:
            nominees = nominees.filter(campaign_id=campaign_id)
        
        nominees = nominees.order_by('-vote_count')
        
        data = []
        for nominee in nominees:
            data.append({
                'id': nominee.id,
                'number': nominee.number or '',
                'name': nominee.name,
                'photo': nominee.photo.url if nominee.photo else '',
                'votes': nominee.vote_count,
                'raised': float(nominee.total_amount_raised),
                'campaign': nominee.campaign.name if nominee.campaign else ''
            })
        
        return JsonResponse({'ok': True, 'nominees': data})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=400)


@login_required
@require_POST
def add_vote(request):
    """API: Add a new vote (admin only)"""
    try:
        import json
        data = json.loads(request.body)
        
        nominee = get_object_or_404(Nominee, pk=data.get('nominee_id'))
        campaign = nominee.campaign
        
        vote_qty = int(data.get('vote_quantity', 1))
        amount = float(campaign.vote_price) * vote_qty
        
        vote = Vote.objects.create(
            nominee=nominee,
            voter_name=data.get('voter_name', 'Admin'),
            voter_email=data.get('voter_email', 'admin@unwindafrica.com'),
            voter_phone=data.get('voter_phone', '+234800000000'),
            vote_quantity=vote_qty,
            amount=amount,
            rest_points_earned=float(campaign.rest_points_per_vote) * vote_qty,
            payment_status='paid'
        )
        
        # Create transaction
        Transaction.objects.create(
            vote=vote,
            reference=f'ADMIN_{vote.id}_{now().timestamp()}',
            amount=amount,
            status='success',
            paid_at=now()
        )
        
        # Update nominee count
        nominee.vote_count = nominee.votes.count()
        nominee.save()
        
        return JsonResponse({'ok': True, 'msg': 'Vote added', 'vote_id': vote.id})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=400)


@login_required
def export_nominees(request):
    """Export all nominees and their votes to CSV"""
    try:
        import csv
        import io
        from django.http import HttpResponse
        
        # Create a string buffer to handle encoding
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header row
        writer.writerow([
            'Nominee ID',
            'Nominee Number',
            'Nominee Name',
            'Campaign',
            'Total Vote Count',
            'Total Amount Raised',
            'Voter Name',
            'Voter Email',
            'Voter Phone',
            'Votes Cast',
            'Amount Paid',
            'Payment Status',
            'Vote Date'
        ])
        
        # Get all nominees with their votes
        nominees = Nominee.objects.select_related('campaign').prefetch_related('votes').all().order_by('-vote_count')
        
        for nominee in nominees:
            # Get all votes for this nominee
            votes = nominee.votes.all().order_by('-created_at')
            
            if votes.exists():
                # Write a row for each vote
                for vote in votes:
                    try:
                        writer.writerow([
                            nominee.pk,
                            nominee.number or '',
                            nominee.name or '',
                            nominee.campaign.name if nominee.campaign else '',
                            nominee.vote_count,
                            str(nominee.total_amount_raised),  # Convert to string to avoid formatting issues
                            vote.voter_name or '',
                            vote.voter_email or '',
                            vote.voter_phone or '',
                            vote.vote_quantity,
                            str(vote.amount),  # Remove currency symbol for data integrity
                            vote.payment_status or '',
                            vote.created_at.strftime('%Y-%m-%d %H:%M:%S') if vote.created_at else '',
                        ])
                    except Exception as e:
                        print(f"Error writing vote for nominee {nominee.name}: {e}")
                        continue
            else:
                # Write nominee even if no votes
                try:
                    writer.writerow([
                        nominee.pk,
                        nominee.number or '',
                        nominee.name or '',
                        nominee.campaign.name if nominee.campaign else '',
                        nominee.vote_count,
                        str(nominee.total_amount_raised),
                        '',  # No voter data
                        '',
                        '',
                        '',
                        '',
                        '',
                        '',
                    ])
                except Exception as e:
                    print(f"Error writing nominee {nominee.name}: {e}")
                    continue
        
        # Create response with proper encoding
        response = HttpResponse(output.getvalue(), content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="nominees_and_votes_export.csv"'        
        return response
    
    except Exception as e:
        print(f"Error exporting nominees: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'ok': False, 
            'error': f'Export failed: {str(e)}'
        }, status=500)



# def _ensure_unique_slug(instance, base_text: str):
#     """
#     Ensure a unique slug for the instance, based on base_text (usually the title).
#     Works with proxy model pointing to your concrete model that actually stores "slug".
#     """
#     base = slugify(base_text or "post") or "post"
#     slug = base
#     Model = instance.__class__
#     i = 1
#     while Model.objects.filter(slug=slug).exclude(pk=instance.pk).exists():
#         i += 1
#         slug = f"{base}-{i}"
#     instance.slug = slug

# @login_required
# def dashboard_home(request):
#     posts_qs = Post.objects.all().order_by("-created_at")
#     events_qs = Event.objects.all().order_by("-created_at")

#     # Forms required by includes (even if tab is hidden by Alpine)
#     post_form = PostForm()
#     event_form = EventForm()

#     # KPIs (align with index.html keys)
#     kpis = {
#         "total_sessions": None,  # plug your analytics later
#         "events_count": events_qs.count(),
#         "pending_events": 0,     # adjust if you track pending moderation
#         "bounce_rate": None,

#         # extra counts (optional)
#         "posts_total": posts_qs.count(),
#         "posts_published": posts_qs.filter(is_published=True).count(),
#         "posts_featured": posts_qs.filter(is_featured=True).count(),
#         "events_upcoming": events_qs.filter(
#             date__gte=date.today(),
#             date__lte=date.today() + timedelta(days=60)
#         ).count(),
#     }

#     # Categories chart
#     cats = [p.category for p in posts_qs]
#     category_chart_labels = sorted(set(cats))
#     category_chart_counts = [cats.count(c) for c in category_chart_labels]

#     # Monthly chart (last 12 months)
#     def add_months(d, n):
#         y = d.year + (d.month - 1 + n) // 12
#         m = (d.month - 1 + n) % 12 + 1
#         return d.replace(year=y, month=m)

#     by_month = Counter(p.created_at.strftime("%Y-%m") for p in posts_qs)
#     first_of_this_month = date.today().replace(day=1)
#     monthly_chart_labels, monthly_chart_counts = [], []
#     for i in range(-11, 1):
#         d = add_months(first_of_this_month, i)
#         key = d.strftime("%Y-%m")
#         monthly_chart_labels.append(d.strftime("%b %Y"))
#         monthly_chart_counts.append(by_month.get(key, 0))

#     ctx = {
#         "posts": list(posts_qs[:18]),
#         "events": events_qs[:12],
#         "kpis": kpis,
#         "category_chart_labels": category_chart_labels,
#         "category_chart_counts": category_chart_counts,
#         "monthly_chart_labels": monthly_chart_labels,
#         "monthly_chart_counts": monthly_chart_counts,
#         "post_form": post_form,
#         "event_form": event_form,
#     }
#     return render(request, "dashboard/index.html", ctx)




# from .forms import AdminAuthenticationForm  # <-- import it

# def login_view(request):
#     if request.user.is_authenticated:
#         return redirect("dashboard_home")

#     form = AdminAuthenticationForm(request, data=request.POST or None)
#     if request.method == "POST" and form.is_valid():
#         auth_login(request, form.get_user())
#         return redirect("dashboard_home")

#     return render(request, "dashboard/login.html", {"form": form})


# # def create_blog(request):
# #     if request.method == "POST":
# #         form = PostForm(request.POST, request.FILES)
# #         if form.is_valid():
# #             post = form.save(commit=False)
# #             action = request.POST.get("action")  # "publish" or "draft"
# #             post.is_published = (action == "publish")
# #             if hasattr(post, "slug") and not post.slug:
# #                 _ensure_unique_slug(post, post.title or "post")
# #             post.save()
# #             return redirect("dashboard_home")
# #     else:
# #         form = PostForm()
# #     return render(request, "dashboard/create_blog.html", {
# #         "blog_form": form,
# #         "editing": False,
# #     })

# @require_POST
# @login_required
# @csrf_protect
# def create_blog(request):
#     if request.method == "POST":
#         form = PostForm(request.POST, request.FILES)
#         if form.is_valid():
#             post = form.save(commit=False)
#             action = request.POST.get("action")
#             post.is_published = (action == "publish")
#             if hasattr(post, "slug") and not post.slug:
#                 _ensure_unique_slug(post, post.title or "post")
#             post.save()
#             return JsonResponse({"ok": True})
#         return JsonResponse({"ok": False, "error": "Invalid form"})
#     return render(request, "dashboard/index.html", {"blog_form": PostForm(), "editing": False})

# # def create_blog(request):
# #     form = PostForm(request.POST, request.FILES)
# #     if form.is_valid():
# #         post = form.save(commit=False)

# #         action = request.POST.get("action", "draft")  # default = draft
# #         post.is_published = (action == "publish")

# #         if not post.slug:
# #             _ensure_unique_slug(post, post.title)

# #         post.save()
# #         return JsonResponse({"ok": True})

# #     return JsonResponse({"ok": False, "error": "Invalid form"}, status=400)

# def edit_blog(request, slug):
#     post = get_object_or_404(Post, slug=slug)
#     if request.method == "POST":
#         form = PostForm(request.POST, request.FILES, instance=post)
#         if form.is_valid():
#             post = form.save(commit=False)
#             action = request.POST.get("action")
#             if action in {"publish", "draft"}:
#                 post.is_published = (action == "publish")
#             if hasattr(post, "slug") and not post.slug:
#                 _ensure_unique_slug(post, post.title or "post")
#             post.save()
#             return redirect("dashboard_home")
#     else:
#         form = PostForm(instance=post)
#     return render(request, "dashboard/create_blog.html", {
#         "blog_form": form,
#         "editing": True,
#         "post": post,
#     })


# @require_POST
# def delete_blog(request, slug):
#     get_object_or_404(Post, slug=slug).delete()
#     return redirect("dashboard_home")


# # Optional: small API example (used if needed by charts)
# # def engagement_api(request):
# #     data = {
# #         "posts_total": Post.objects.count(),
# #         "posts_published": Post.objects.filter(is_published=True).count(),
# #         "events_next_30_days": Event.objects.filter(
# #             date__gte=date.today(), date__lte=date.today() + timedelta(days=30)
# #         ).count(),
# #     }
# #     return JsonResponse(data)

# @require_POST
# def toggle_feature(request, slug):
#     post = get_object_or_404(Post, slug=slug)
#     post.is_featured = not post.is_featured
#     post.save(update_fields=["is_featured"])
#     return redirect("dashboard_home")

# # ---------- Events ----------
# def create_event(request):
#     if request.method == "POST":
#         form = EventForm(request.POST, request.FILES)
#         if form.is_valid():
#             form.save()
#             return redirect("dashboard_home")
#     else:
#         form = EventForm()
#     return render(request, "dashboard/create_event.html", {"event_form": form})

# def edit_event(request, slug):
#     event = get_object_or_404(Event, slug=slug)
#     if request.method == "POST":
#         form = EventForm(request.POST, request.FILES, instance=event)
#         if form.is_valid():
#             form.save()
#             return redirect("dashboard_home")
#     else:
#         form = EventForm(instance=event)
#     return render(request, "dashboard/create_event.html", {"event_form": form, "editing": True, "event": event})

# @require_POST
# def delete_event(request, slug):
#     get_object_or_404(Event, slug=slug).delete()
#     return redirect("dashboard_home")

# # ---------- Simple API used by urls ----------
# def engagement_api(request):
#     # minimal example; wire to your real metrics as needed
#     data = {
#         "posts_total": Post.objects.count(),
#         "posts_published": Post.objects.filter(is_published=True).count(),
#         "events_next_30_days": Event.objects.filter(
#             date__gte=date.today(), date__lte=date.today()+timedelta(days=30)
#         ).count(),
#     }
#     return JsonResponse(data)


# ========== Raising Readers - Books Management ==========
from Web.models import Book
from .forms import BookForm

@login_required
def books_dashboard(request):
    """Books dashboard - view and manage all books"""
    books = Book.objects.all().order_by('-created_at')
    
    # Stats
    total_books = books.count()
    available_books = books.filter(status='available').count()
    on_loan_books = books.filter(status='on_loan').count()
    
    # Form for adding new book
    if request.method == 'POST' and 'create_book' in request.POST:
        form = BookForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('books_dashboard')
    else:
        form = BookForm()
    
    context = {
        'books': books,
        'book_form': form,
        'total_books': total_books,
        'available_books': available_books,
        'on_loan_books': on_loan_books,
    }
    
    return render(request, 'dashboard/books.html', context)


@require_POST
@login_required
def create_book(request):
    """Create a new book via AJAX"""
    try:
        form = BookForm(request.POST, request.FILES)
        if form.is_valid():
            book = form.save()
            return JsonResponse({"ok": True, "book_id": book.id})
        
        errors = {field: error[0] for field, error in form.errors.items()}
        return JsonResponse({"ok": False, "error": "Invalid form", "errors": errors}, status=400)
    
    except Exception as e:
        print(f"Error creating book: {e}")
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


@login_required
def edit_book(request, book_id):
    """Edit an existing book via AJAX"""
    try:
        book = get_object_or_404(Book, id=book_id)
        
        if request.method == "POST":
            form = BookForm(request.POST, request.FILES, instance=book)
            if form.is_valid():
                form.save()
                return JsonResponse({"ok": True})
            
            errors = {field: error[0] for field, error in form.errors.items()}
            return JsonResponse({"ok": False, "error": "Invalid form", "errors": errors}, status=400)
    
    except Exception as e:
        print(f"Error editing book: {e}")
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


@require_POST
@login_required
def delete_book(request, book_id):
    """Delete a book via AJAX"""
    try:
        book = get_object_or_404(Book, id=book_id)
        book.delete()
        return JsonResponse({"ok": True})
    except Exception as e:
        print(f"Error deleting book: {e}")
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


@require_POST
@login_required
def toggle_book_status(request, book_id):
    """Toggle book availability status"""
    try:
        book = get_object_or_404(Book, id=book_id)
        # Cycle through status: available -> unavailable -> available
        if book.status == 'available':
            book.status = 'unavailable'
        else:
            book.status = 'available'
        book.save()
        return JsonResponse({"ok": True, "new_status": book.status})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


@login_required
def get_book(request, book_id):
    """Get book details for editing"""
    try:
        book = get_object_or_404(Book, id=book_id)
        return JsonResponse({
            'id': book.id,
            'title': book.title,
            'author': book.author,
            'description': book.description,
            'age_category': book.age_category,
            'genre': book.genre,
            'status': book.status,
            'cover_image': book.cover_image.url if book.cover_image else None,
            'times_borrowed': book.times_borrowed,
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
