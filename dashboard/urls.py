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

    # Voting dashboard
    path("voting/", views.voting_dashboard, name="voting_dashboard"),
    path("voting/create/", views.create_campaign, name="create_campaign"),
    path("voting/<slug:slug>/edit/", views.edit_campaign, name="edit_campaign"),
    path("voting/<slug:slug>/delete/", views.delete_campaign, name="delete_campaign"),
    path("voting/<slug:slug>/voters/", views.view_campaign_voters, name="view_campaign_voters"),
    
    # Rest Card management
    path("rest-cards/<int:card_id>/edit/", views.edit_rest_card, name="edit_rest_card"),
    path("rest-cards/<int:card_id>/generate/", views.generate_rest_card, name="generate_rest_card"),
    path("rest-cards/<int:card_id>/resend/", views.resend_rest_card, name="resend_rest_card"),
    path("rest-cards/<int:card_id>/toggle-status/", views.toggle_rest_card_status, name="toggle_rest_card_status"),
    path("rest-cards/<int:card_id>/get/", views.get_rest_card, name="get_rest_card"),
    path("rest-cards/create/", views.create_rest_card, name="create_rest_card"),
    path("rest-cards/stats/", views.rest_cards_stats, name="rest_cards_stats"),
    path("engagement-data/", views.engagement_data, name="engagement_data"),
    path("rest-cards/export/", views.export_rest_cards, name="export_rest_cards"),
    path("rest-cards/import/", views.import_rest_cards, name="import_rest_cards"),
    path("nominees/export/", views.export_nominees, name="export_nominees"),
]
