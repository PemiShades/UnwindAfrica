from django.urls import path
from . import views
from . import voting_views


urlpatterns = [
	path('',views.home,name="home"),
    path('test/', views.test, name='test'),
	path('about/',views.about,name="about"),
	path('packages/',views.packages,name="packages"),
    path('blog/<slug:slug>/', views.blog_detail, name='blog_detail'),
    path('unwind-thrive/', views.unwind_thrive, name='services'),

    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('terms/', views.terms, name='terms'),
    path('refund-policy/', views.refund_policy, name='refund_policy'),
    path('faq/', views.faq, name='faq'),

    path("quotes/request/", views.quote_request, name="quote_request"),
    path("card-request/", views.card_request, name="card_request"),

    path('blog/', views.blog_list, name='blog'),
    path('blog/', views.blog_list, name='blog_list'),
    path('events/', views.event_list, name='event_list'),
    path('events/<slug:slug>/', views.event_detail, name='event_detail'),
    path('contact/', views.contact, name='contact'),

    # Voting System URLs
    path('voting/', voting_views.voting_campaigns_list, name='voting_campaigns_list'),
    path('voting/<slug:slug>/', voting_views.voting_campaign_detail, name='voting_campaign'),
    path('voting/nominate/', voting_views.voting_campaign_detail, name='nominate'),
    path('voting/payment/initialize/', voting_views.initialize_payment, name='initialize_payment'),
    path('voting/payment/verify/<str:reference>/', voting_views.verify_payment, name='verify_payment'),
    path('voting/payment/thank-you/', voting_views.voting_thank_you, name='voting_thank_you'),
    path('voting/webhook/paystack/', voting_views.paystack_webhook, name='paystack_webhook'),
    
    # Community & Rest Card URLs
    path('community/', views.community_stats, name='community_stats'),
    path('rest-card/', views.rest_card_info, name='rest_card_info'),
    path('rest-card/join/', views.rest_card_waitlist_join, name='rest_card_waitlist_join'),
    path('rest-card/status/', views.rest_card_status, name='rest_card_status'),
    path('rest-card/signup/', views.rest_card_signup, name='rest_card_signup'),
    path('token-wallet/', views.token_wallet_view, name='token_wallet'),
    path('unwind-and-win/', views.unwind_and_win, name='unwind_and_win'),
    path('raising-readers/', views.raising_readers, name='raising_readers'),
    path('vote/', views.vote, name='vote'),
    path('payment/<int:vote_id>/', views.payment, name='payment'),
    path('vote-confirmation/<int:vote_id>/', views.vote_confirmation, name='vote_confirmation'),
    path('nominate/', views.nominate, name='nominate'),
    path('nomination-confirmation/<int:nominee_id>/', views.nomination_confirmation, name='nomination_confirmation'),
    path('my-rest-card/', views.my_rest_card, name='my_rest_card'),
    path('generate-rest-card/<int:card_id>/', views.generate_rest_card, name='generate_rest_card'),
]


handler404 = 'Web.views.custom_404'