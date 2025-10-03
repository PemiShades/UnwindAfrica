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
    today = timezone.now().date()
    events = Event.objects.filter(date__gte=today).order_by('date')
    posts = Post.objects.filter(is_published=True).order_by('-created_at')[:6]
    return render(request, 'Web/home.html', {
        'posts': posts,
        'events': events,
    })


def about(request):
    return render(request, 'Web/about.html', context={})


def packages(request):
    return render(request, 'Web/packages.html', context={})


def custom_404(request, exception):
    return render(request, '404.html', status=404)


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
