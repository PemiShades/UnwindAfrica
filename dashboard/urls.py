# dashboard/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard_home, name="dashboard_home"),

    # Blog (canonical)
    path("blog/create/", views.create_blog, name="blog_create"),
    path("blog/<slug:slug>/edit/", views.edit_blog, name="blog_edit"),
    path("blog/<slug:slug>/delete/", views.delete_blog, name="blog_delete"),

    # Aliases (kept for back-compat)
    path("post/add/", views.create_blog, name="create_blog"),
    path("post/<slug:slug>/edit/", views.edit_blog, name="edit_blog"),
    path("post/<slug:slug>/delete/", views.delete_blog, name="delete_blog"),

    # Events (use slug to match views)
    path("event/create/", views.create_event, name="create_event"),
    path("event/<slug:slug>/edit/", views.edit_event, name="edit_event"),
    path("event/<slug:slug>/delete/", views.delete_event, name="delete_event"),

    # API
    # path("api/metrics/engagement/", views.engagement_api, name="engagement_api"),
]
