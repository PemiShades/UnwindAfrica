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
def dashboard_home(request):
    posts_qs = Post.objects.all()
    events_qs = Event.objects.all()

    # Forms needed by included partials (even when the tab isn't active)
    post_form = PostForm()
    event_form = EventForm()

    # KPIs expected by index.html
    kpis = {
        # what index.html reads:
        "total_sessions": None,            # plug your analytics when ready
        "events_count": events_qs.count(),
        "pending_events": 0,               # adjust to your pending logic
        "bounce_rate": None,               # plug real metric when ready

        # plus the older ones we also compute (optional):
        "posts_total": posts_qs.count(),
        "posts_published": posts_qs.filter(is_published=True).count(),
        "posts_featured": posts_qs.filter(is_featured=True).count(),
        "events_upcoming": events_qs.filter(
            date__gte=date.today(),
            date__lte=date.today() + timedelta(days=60)
        ).count(),
    }

    # Category + monthly charts (unchanged idea; keep if you already have it)
    cats = [p.category for p in posts_qs]
    category_chart_labels = sorted(set(cats))
    category_chart_counts = [cats.count(c) for c in category_chart_labels]

    from datetime import date as _d
    def add_months(d, n):
        y = d.year + (d.month - 1 + n) // 12
        m = (d.month - 1 + n) % 12 + 1
        return d.replace(year=y, month=m)

    by_month = Counter(p.created_at.strftime("%Y-%m") for p in posts_qs)
    first_of_this_month = _d.today().replace(day=1)
    monthly_chart_labels, monthly_chart_counts = [], []
    for i in range(-11, 1):
        d = add_months(first_of_this_month, i)
        key = d.strftime("%Y-%m")
        monthly_chart_labels.append(d.strftime("%b %Y"))
        monthly_chart_counts.append(by_month.get(key, 0))

    ctx = {
        "posts": posts_qs[:18],
        "events": events_qs[:12],
        "kpis": kpis,
        "category_chart_labels": category_chart_labels,
        "category_chart_counts": category_chart_counts,
        "monthly_chart_labels": monthly_chart_labels,
        "monthly_chart_counts": monthly_chart_counts,

        # <<< important >>>
        "post_form": post_form,
        "event_form": event_form,
    }
    return render(request, "dashboard/index.html", ctx)

    posts = Post.objects.all()[:18]
    events = Event.objects.all()[:12]

    # KPIs
    kpis = {
        "posts_total": Post.objects.count(),
        "posts_published": Post.objects.filter(is_published=True).count(),
        "posts_featured": Post.objects.filter(is_featured=True).count(),
        "events_upcoming": Event.objects.filter(
            date__gte=date.today(),
            date__lte=date.today()+timedelta(days=60)
        ).count(),
    }

    # Charts: categories and monthly counts (last 12 months)
    cats = [p.category for p in Post.objects.all()]
    category_chart_labels = sorted(set(cats))
    category_chart_counts = [cats.count(c) for c in category_chart_labels]

    # Build last 12 months safely without requiring dateutil
    by_month = Counter(p.created_at.strftime("%Y-%m") for p in Post.objects.all())
    labels_pretty, counts = [], []

    def add_months(d, n):
        # add n months to d (first of month)
        y = d.year + (d.month - 1 + n) // 12
        m = (d.month - 1 + n) % 12 + 1
        return d.replace(year=y, month=m)

    first_of_this_month = date.today().replace(day=1)
    for i in range(-11, 1):  # last 12 months, oldest -> newest
        d = add_months(first_of_this_month, i)
        iso = d.strftime("%Y-%m")
        labels_pretty.append(d.strftime("%b %Y"))
        counts.append(by_month.get(iso, 0))

    ctx = {
        "posts": posts,
        "events": events,
        "kpis": kpis,
        "category_chart_labels": category_chart_labels,
        "category_chart_counts": category_chart_counts,
        "monthly_chart_labels": labels_pretty,
        "monthly_chart_counts": counts,
    }
    return render(request, "dashboard/index.html", ctx)

# ---------- Blog create/edit with explicit "draft/publish" actions ----------
def create_blog(request):
    if request.method == "POST":
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            action = request.POST.get("action")
            post.is_published = (action == "publish")
            post.save()
            return redirect("dashboard_home")
    else:
        form = PostForm()
    return render(request, "dashboard/create_blog.html", {"post_form": form})

def edit_blog(request, slug):
    post = get_object_or_404(Post, slug=slug)
    if request.method == "POST":
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            post = form.save(commit=False)
            action = request.POST.get("action")
            if action in {"draft", "publish"}:
                post.is_published = (action == "publish")
            post.save()
            return redirect("dashboard_home")
    else:
        form = PostForm(instance=post)
    return render(request, "dashboard/create_blog.html", {"post_form": form, "editing": True, "post": post})

@require_POST
def delete_blog(request, slug):
    get_object_or_404(Post, slug=slug).delete()
    return redirect("dashboard_home")

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
