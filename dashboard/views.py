# dashboard/views.py
from datetime import date, timedelta
from collections import Counter
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from .models import Post, Event  # proxies
from .forms import PostForm, EventForm

# ---------- Home: lists + KPIs + chart arrays ----------
# dashboard/views.py

# dashboard/views.py
from datetime import date, timedelta
from collections import Counter

from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.utils.text import slugify

from .models import Post, Event
from .forms import PostForm, EventForm
from django.contrib.auth.decorators import login_required


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

@login_required
def dashboard_home(request):
    posts_qs = Post.objects.all().order_by("-created_at")
    events_qs = Event.objects.all().order_by("-created_at")

    # Forms required by includes (even if tab is hidden by Alpine)
    post_form = PostForm()
    event_form = EventForm()

    # KPIs (align with index.html keys)
    kpis = {
        "total_sessions": None,  # plug your analytics later
        "events_count": events_qs.count(),
        "pending_events": 0,     # adjust if you track pending moderation
        "bounce_rate": None,

        # extra counts (optional)
        "posts_total": posts_qs.count(),
        "posts_published": posts_qs.filter(is_published=True).count(),
        "posts_featured": posts_qs.filter(is_featured=True).count(),
        "events_upcoming": events_qs.filter(
            date__gte=date.today(),
            date__lte=date.today() + timedelta(days=60)
        ).count(),
    }

    # Categories chart
    cats = [p.category for p in posts_qs]
    category_chart_labels = sorted(set(cats))
    category_chart_counts = [cats.count(c) for c in category_chart_labels]

    # Monthly chart (last 12 months)
    def add_months(d, n):
        y = d.year + (d.month - 1 + n) // 12
        m = (d.month - 1 + n) % 12 + 1
        return d.replace(year=y, month=m)

    by_month = Counter(p.created_at.strftime("%Y-%m") for p in posts_qs)
    first_of_this_month = date.today().replace(day=1)
    monthly_chart_labels, monthly_chart_counts = [], []
    for i in range(-11, 1):
        d = add_months(first_of_this_month, i)
        key = d.strftime("%Y-%m")
        monthly_chart_labels.append(d.strftime("%b %Y"))
        monthly_chart_counts.append(by_month.get(key, 0))

    ctx = {
        "posts": list(posts_qs[:18]),
        "events": events_qs[:12],
        "kpis": kpis,
        "category_chart_labels": category_chart_labels,
        "category_chart_counts": category_chart_counts,
        "monthly_chart_labels": monthly_chart_labels,
        "monthly_chart_counts": monthly_chart_counts,
        "post_form": post_form,
        "event_form": event_form,
    }
    return render(request, "dashboard/index.html", ctx)




from .forms import AdminAuthenticationForm  # <-- import it

def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard_home")

    form = AdminAuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        auth_login(request, form.get_user())
        return redirect("dashboard_home")

    return render(request, "dashboard/login.html", {"form": form})


def create_blog(request):
    if request.method == "POST":
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            action = request.POST.get("action")  # "publish" or "draft"
            post.is_published = (action == "publish")
            if hasattr(post, "slug") and not post.slug:
                _ensure_unique_slug(post, post.title or "post")
            post.save()
            return redirect("dashboard_home")
    else:
        form = PostForm()
    return render(request, "dashboard/create_blog.html", {
        "blog_form": form,
        "editing": False,
    })


def edit_blog(request, slug):
    post = get_object_or_404(Post, slug=slug)
    if request.method == "POST":
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            post = form.save(commit=False)
            action = request.POST.get("action")
            if action in {"publish", "draft"}:
                post.is_published = (action == "publish")
            if hasattr(post, "slug") and not post.slug:
                _ensure_unique_slug(post, post.title or "post")
            post.save()
            return redirect("dashboard_home")
    else:
        form = PostForm(instance=post)
    return render(request, "dashboard/create_blog.html", {
        "blog_form": form,
        "editing": True,
        "post": post,
    })


@require_POST
def delete_blog(request, slug):
    get_object_or_404(Post, slug=slug).delete()
    return redirect("dashboard_home")


# Optional: small API example (used if needed by charts)
# def engagement_api(request):
#     data = {
#         "posts_total": Post.objects.count(),
#         "posts_published": Post.objects.filter(is_published=True).count(),
#         "events_next_30_days": Event.objects.filter(
#             date__gte=date.today(), date__lte=date.today() + timedelta(days=30)
#         ).count(),
#     }
#     return JsonResponse(data)

@require_POST
def toggle_feature(request, slug):
    post = get_object_or_404(Post, slug=slug)
    post.is_featured = not post.is_featured
    post.save(update_fields=["is_featured"])
    return redirect("dashboard_home")

# ---------- Events ----------
def create_event(request):
    if request.method == "POST":
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect("dashboard_home")
    else:
        form = EventForm()
    return render(request, "dashboard/create_event.html", {"event_form": form})

def edit_event(request, slug):
    event = get_object_or_404(Event, slug=slug)
    if request.method == "POST":
        form = EventForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            form.save()
            return redirect("dashboard_home")
    else:
        form = EventForm(instance=event)
    return render(request, "dashboard/create_event.html", {"event_form": form, "editing": True, "event": event})

@require_POST
def delete_event(request, slug):
    get_object_or_404(Event, slug=slug).delete()
    return redirect("dashboard_home")

# ---------- Simple API used by urls ----------
def engagement_api(request):
    # minimal example; wire to your real metrics as needed
    data = {
        "posts_total": Post.objects.count(),
        "posts_published": Post.objects.filter(is_published=True).count(),
        "events_next_30_days": Event.objects.filter(
            date__gte=date.today(), date__lte=date.today()+timedelta(days=30)
        ).count(),
    }
    return JsonResponse(data)
