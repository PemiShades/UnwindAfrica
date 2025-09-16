# dashboard/urls.py
from django.urls import path, re_path
from . import views

urlpatterns = [
    path("", views.dashboard_home, name="dashboard_home"),
    path("login/", views.login_view, name="dashboard_login"),


    # Blog (canonical)
    path("blog/create/", views.create_blog, name="blog_create"),
    path("blog/<slug:slug>/edit/", views.edit_blog, name="blog_edit"),
    path("blog/<slug:slug>/delete/", views.delete_blog, name="blog_delete"),

    # Aliases (back-compat)
    path("post/add/", views.create_blog, name="create_blog"),
    path("post/<slug:slug>/edit/", views.edit_blog, name="edit_blog"),
    path("post/<slug:slug>/delete/", views.delete_blog, name="delete_blog"),

    # Events — accept slug OR pk via one identifier
    path("event/create/", views.create_event, name="create_event"),
    re_path(r"^event/(?P<identifier>[-a-zA-Z0-9_]+)/edit/$", views.edit_event, name="edit_event"),
    re_path(r"^event/(?P<identifier>[-a-zA-Z0-9_]+)/delete/$", views.delete_event, name="delete_event"),
]
