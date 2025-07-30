# from .models import Event

# Create your views here.
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from .models import Event
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_date
from collections import defaultdict
from django.db.models import Q
from django.shortcuts import render, redirect
from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.utils import timezone
from .models import Post, Event, BlogCategory
from .forms import PostForm, EventForm
from datetime import date

import logging


def home(request):
    today = timezone.now().date()
    events = Event.objects.filter(date__gte=today).order_by('date')
    posts = Post.objects.filter(is_published=True).order_by('-created_at')[:6]
    return render(request, 'Web/home.html', {
        'posts': posts,
        'events': events,
    })
    # return render(request, 'Web/home.html', {'events': events})



def about(request):
	return render(request, 'Web/about.html', context={})

def packages(request):
	return render(request, 'Web/packages.html', context={})

def custom_404(request, exception):
    return render(request, '404.html', status=404)


def add_post_view(request):
    form = PostForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        form.save()
        return redirect('dashboard')
    return render(request, 'add_post.html', {'form': form})

def add_event_view(request):
    form = EventForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        form.save()
        return redirect('dashboard')
    return render(request, 'add_event.html', {'form': form})



# import json

# def dashboard_view(request):
#     today = timezone.now().date()

#     blog_count = Post.objects.count()
#     published_count = Post.objects.filter(is_published=True).count()
#     unpublished_count = Post.objects.filter(is_published=False).count()
#     event_count = Event.objects.count()
#     expired_events = Event.objects.filter(is_expired=True).count()
#     upcoming_events = Event.objects.filter(date__gte=today).count()
#     recent_posts = Post.objects.order_by('-created_at')[:5]
#     upcoming_events_list = Event.objects.filter(date__gte=today).order_by('date')[:5]
#     category_distribution = BlogCategory.objects.annotate(post_count=Count('posts'))
#     empty_posts = Post.objects.filter(content__isnull=True)
#     unused_categories = BlogCategory.objects.annotate(num_posts=Count('posts')).filter(num_posts=0)

#     # Chart data
#     monthly_counts = Post.objects.annotate(month=TruncMonth("created_at")).values("month").annotate(count=Count("id")).order_by("month")
#     chart_labels = [entry["month"].strftime("%b %Y") for entry in monthly_counts]
#     chart_values = [entry["count"] for entry in monthly_counts]

#     category_labels = [cat.name for cat in category_distribution]
#     category_values = [cat.post_count for cat in category_distribution]

#     context = {
#         'blog_count': blog_count,
#         'published_count': published_count,
#         'unpublished_count': unpublished_count,
#         'event_count': event_count,
#         'expired_events': expired_events,
#         'upcoming_events': upcoming_events,
#         'recent_posts': recent_posts,
#         'upcoming_events_list': upcoming_events_list,
#         'category_distribution': category_distribution,
#         'empty_posts': empty_posts,
#         'unused_categories': unused_categories,
#         'chart_labels': json.dumps(chart_labels),
#         'chart_values': json.dumps(chart_values),
#         'category_labels': json.dumps(category_labels),
#         'category_values': json.dumps(category_values),
#     }

#     return render(request, 'Web/Dashboard/dashboard.html', context)


def dashboard_view(request):
    # Pie Chart: Posts by Category (with titles)
    category_data = (
        BlogCategory.objects.annotate(post_count=Count('posts'))
        .filter(post_count__gt=0)
        .values('id', 'name', 'post_count')
    )

    # Map of category id -> list of post titles
    category_titles_map = defaultdict(list)
    for post in Post.objects.select_related('category').filter(category__isnull=False):
        category_titles_map[post.category_id].append(post.title)

    category_chart_labels = []
    category_chart_counts = []
    category_chart_tooltips = []

    for cat in category_data:
        category_chart_labels.append(cat['name'])
        category_chart_counts.append(cat['post_count'])
        category_chart_tooltips.append(category_titles_map[cat['id']])

    # Line Chart: Blogs Over Time
    monthly_data = (
        Post.objects
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )

    context = {
        'blog_count': Post.objects.count(),
        'published_count': Post.objects.filter(is_published=True).count(),
        'unpublished_count': Post.objects.filter(is_published=False).count(),
        'event_count': Event.objects.count(),
        'upcoming_events': Event.objects.filter(date__gte=timezone.now()).count(),
        'expired_events': Event.objects.filter(date__lt=timezone.now()).count(),
        'upcoming_events_list': Event.objects.filter(date__gte=timezone.now().date()).order_by('date')[:5],


        'category_chart_labels': category_chart_labels,
        'category_chart_counts': category_chart_counts,
        'category_chart_tooltips': category_chart_tooltips,
        'monthly_chart_labels': [m['month'].strftime('%b %Y') for m in monthly_data],
        'monthly_chart_counts': [m['count'] for m in monthly_data],

        'category_distribution': category_data,
        'recent_posts': Post.objects.order_by('-created_at')[:5],
        # 'upcoming_events_list': Event.objects.filter(date__gte=timezone.now()).order_by('date')[:5],
        'empty_posts': Post.objects.filter(content__isnull=True),
        'unused_categories': BlogCategory.objects.annotate(post_count=Count('posts')).filter(post_count=0),

        'blog_categories': BlogCategory.objects.all(),
        'posts': Post.objects.filter(is_published=True).order_by('-created_at')[:6],

    }

    return render(request, 'Web/Dashboard/dashboard.html', context)




@csrf_exempt
def add_post_ajax(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        thumbnail = request.FILES.get('thumbnail')
        category_id = request.POST.get('category')

        if not title or not content or not thumbnail:
            return JsonResponse({'error': 'Missing fields'}, status=400)

        category = BlogCategory.objects.filter(id=category_id).first() if category_id else None

        Post.objects.create(
            title=title,
            content=content,
            thumbnail=thumbnail,
            category=category
        )
        return JsonResponse({'success': True})


@csrf_exempt
def add_event_ajax(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        brief_text = request.POST.get('brief_text')
        date = request.POST.get('date')
        thumbnail = request.FILES.get('thumbnail')
        flier = request.FILES.get('flier')

        if not title or not brief_text or not date or not thumbnail or not flier:
            return JsonResponse({'error': 'Missing fields'}, status=400)

        Event.objects.create(
            title=title,
            brief_text=brief_text,
            date=parse_date(date),
            thumbnail=thumbnail,
            flier=flier
        )
        return JsonResponse({'success': True})



from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt
@require_POST
def update_post_ajax(request, post_id):
    post = Post.objects.get(id=post_id)
    post.title = request.POST.get('title')
    post.content = request.POST.get('content')
    if 'thumbnail' in request.FILES:
        post.thumbnail = request.FILES['thumbnail']
    post.save()
    return JsonResponse({'success': True, 'title': post.title, 'content': post.content})

@csrf_exempt
@require_POST
def delete_post_ajax(request, post_id):
    Post.objects.filter(id=post_id).delete()
    return JsonResponse({'success': True})


@csrf_exempt
@require_POST
def update_event_ajax(request, event_id):
    event = Event.objects.get(id=event_id)
    event.title = request.POST.get('title')
    event.brief_text = request.POST.get('brief_text')
    event.date = parse_date(request.POST.get('date'))
    if 'thumbnail' in request.FILES:
        event.thumbnail = request.FILES['thumbnail']
    if 'flier' in request.FILES:
        event.flier = request.FILES['flier']
    event.save()
    return JsonResponse({'success': True, 'title': event.title, 'brief_text': event.brief_text})

@csrf_exempt
@require_POST
def delete_event_ajax(request, id):
    get_object_or_404(Event, id=id).delete()
    return JsonResponse({"success": True})

@csrf_exempt
@require_POST
def edit_event(request, id):
    event = get_object_or_404(Event, id=id)
    data = json.loads(request.body)
    event.title = data['title']
    event.date = data['date']
    event.brief_text = data['brief_text']
    event.save()
    return JsonResponse({"success": True})




def get_upcoming_events(request):
    events = Event.objects.filter(date__gte=timezone.now().date()).order_by('date')
    event_list = [
        {
            'id': e.id,
            'title': e.title,
            'brief_text': e.brief_text,
            'date': e.date.strftime('%Y-%m-%d'),
        } for e in events
    ]
    return JsonResponse({'events': event_list})


@require_POST
def edit_event(request, id):
    event = get_object_or_404(Event, id=id)
    event.title = request.POST.get('title')
    event.brief_text = request.POST.get('brief_text')
    event.date = request.POST.get('date')
    event.save()
    return JsonResponse({'success': True})


@require_POST
def delete_event(request, id):
    event = get_object_or_404(Event, id=id)
    event.delete()
    return JsonResponse({'success': True})


logger = logging.getLogger(__name__)

# upcoming_events = Event.objects.filter(date__gte=timezone.now().date()).order_by('date')
# print(f"{upcoming_events} is upcoming_events")
# logger.warning(f"Fetched {upcoming_events.count()} upcoming events")
# for event in upcoming_events:
#     logger.warning(f"Event: {event.title}, Date: {event.date}")