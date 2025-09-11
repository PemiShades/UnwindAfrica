from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from Web.models import Post, Event, BlogCategory
from .forms import BlogForm, EventForm
from django.utils.text import slugify
from .forms import BlogForm
from collections import defaultdict
from django.db.models import Count
from django.views.decorators.http import require_POST

from django.shortcuts import redirect
from django.contrib import messages


# def dashboard_home(request):
#     posts = Post.objects.order_by('-created_at')[:5]
#     events = Event.objects.order_by('-created_at')[:5]

#     category_data = (
#         Post.objects.values('category')
#         .annotate(post_count=Count('id'))
#         .filter(post_count__gt=0)
#         .order_by('-post_count')
#     )

#     return render(request, 'dashboard/dashboard.html', {

#         'posts': posts,
#         'events': events,
#         'category_data': category_data,
#         'blog_form': BlogForm(),
#         'event_form': EventForm(),
#     })

from django.utils import timezone

from django.utils import timezone

def dashboard_home(request):
    posts = Post.objects.order_by('-created_at')[:5]
    events = Event.objects.order_by('-created_at')[:5]

    # Blog Stats
    blog_count = Post.objects.count()
    published_count = Post.objects.filter(is_published=True).count()
    unpublished_count = Post.objects.filter(is_published=False).count()

    # Event Stats
    event_count = Event.objects.count()
    upcoming_events = Event.objects.filter(date__gte=timezone.now()).count()
    expired_events = Event.objects.filter(date__lt=timezone.now()).count()
    upcoming_events_list = Event.objects.filter(date__gte=timezone.now()).order_by('date')[:6]  # Get event list

    return render(request, 'dashboard/dashboard.html', {
        'posts': posts,
        'events': events,
        'form': BlogForm(),
        'event_form': EventForm(),
        'blog_count': blog_count,
        'published_count': published_count,
        'unpublished_count': unpublished_count,
        'event_count': event_count,
        'upcoming_events': upcoming_events,
        'expired_events': expired_events,
        'upcoming_events_list': upcoming_events_list,  # ✅ include this
    })




def create_blog_page(request):
    form = BlogForm()
    return render(request, 'dashboard/blog_form.html', {'form': form})


# def create_blog(request):
#     if request.method == 'POST':
#         form = BlogForm(request.POST, request.FILES)
#         if form.is_valid():
#             blog = form.save(commit=False)
#             blog.slug = slugify(blog.title)
#             blog.save()
#             messages.success(request, 'Blog post created successfully.')
#     return redirect('dashboard_home')


def create_blog(request):
    if request.method == 'POST':
        form = BlogForm(request.POST, request.FILES)
        if form.is_valid():
            blog = form.save(commit=False)
            blog.slug = slugify(blog.title)
            blog.save()
            messages.success(request, 'Blog post created successfully.')
            return redirect('dashboard_home')
        else:
            messages.error(request, 'There was an error with your submission.')
            return render(request, 'dashboard/blog_form.html', {'form': form})
    return redirect('create_blog_page')



def edit_blog(request, slug):
    blog = get_object_or_404(Post, slug=slug)
    if request.method == 'POST':
        form = BlogForm(request.POST, request.FILES, instance=blog)
        if form.is_valid():
            form.save()
            messages.success(request, 'Blog post updated.')
    return redirect('dashboard_home')


def delete_blog(request, slug):
    blog = get_object_or_404(Post, slug=slug)
    blog.delete()
    messages.warning(request, 'Blog post deleted.')
    return redirect('dashboard_home')


def create_event(request):
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Event created.')
    return redirect('dashboard_home')


@require_POST
def edit_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    form = EventForm(request.POST, request.FILES, instance=event)
    if form.is_valid():
        form.save()
        messages.success(request, 'Event updated successfully.')
    else:
        messages.error(request, 'There was a problem updating the event.')

    return redirect('dashboard_home')  # adjust name if different






def delete_event(request, id):
    event = get_object_or_404(Event, id=id)
    event.delete()
    messages.warning(request, 'Event deleted.')
    return redirect('dashboard_home')
