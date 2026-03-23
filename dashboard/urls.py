# dashboard/urls.py
from django.urls import path, re_path
from . import views

urlpatterns = [
    # Admin CMS dashboard at /cms/
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
    
    # Nominee management - edit stories
    path("nominees/<int:nominee_id>/edit/", views.edit_nominee, name="edit_nominee"),
    path("nominees/by-campaign/<slug:campaign_slug>/", views.get_nominees_by_campaign, name="nominees_by_campaign"),
    
    # Rest Card management
    path("rest-cards/<int:card_id>/edit/", views.edit_rest_card, name="edit_rest_card"),
    path("rest-cards/<int:card_id>/generate/", views.generate_rest_card, name="generate_rest_card"),
    path("rest-cards/<int:card_id>/resend/", views.resend_rest_card, name="resend_rest_card"),
    path("rest-cards/<int:card_id>/toggle-status/", views.toggle_rest_card_status, name="toggle_rest_card_status"),
    path("rest-cards/<int:card_id>/get/", views.get_rest_card, name="get_rest_card"),
    path("rest-cards/create/", views.create_rest_card, name="create_rest_card"),
    path("rest-cards/stats/", views.rest_cards_stats, name="rest_cards_stats"),
    path("rest-cards/bulk-activate/", views.bulk_activate_cards, name="bulk_activate_cards"),
    path("rest-cards/bulk-deactivate/", views.bulk_deactivate_cards, name="bulk_deactivate_cards"),
    path("rest-cards/bulk-delete/", views.bulk_delete_cards, name="bulk_delete_cards"),
    path("rest-cards/activate-all/", views.activate_all_cards, name="activate_all_cards"),
    path("rest-cards/deactivate-all/", views.deactivate_all_cards, name="deactivate_all_cards"),
    path("rest-cards/generate-all/", views.generate_card_for_all, name="generate_card_for_all"),
    path("engagement-data/", views.engagement_data, name="engagement_data"),
    path("rest-cards/export/", views.export_rest_cards, name="export_rest_cards"),
    path("rest-cards/import/", views.import_rest_cards, name="import_rest_cards"),
    path("nominees/export/", views.export_nominees, name="export_nominees"),
    
    # Voting management APIs
    path("nominees/<int:nominee_id>/details/", views.get_nominee_details, name="nominee_details"),
    path("nominees/<int:nominee_id>/delete/", views.delete_nominee, name="delete_nominee"),
    path("nominees/data/", views.get_nominees_data, name="nominees_data"),
    path("votes/<int:vote_id>/delete/", views.delete_vote, name="delete_vote"),
    path("votes/add/", views.add_vote, name="add_vote"),
    
    # Raising Readers - Books Management
    path("books/", views.books_dashboard, name="books_dashboard"),
    path("books/create/", views.create_book, name="create_book"),
    path("books/<int:book_id>/", views.get_book, name="get_book"),
    path("books/<int:book_id>/edit/", views.edit_book, name="edit_book"),
    path("books/<int:book_id>/delete/", views.delete_book, name="delete_book"),
    path("books/<int:book_id>/toggle-status/", views.toggle_book_status, name="toggle_book_status"),
]
