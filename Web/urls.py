from django.urls import path
from . import views
from . import voting_views


urlpatterns = [
	path('',views.home,name="home"),
    path('test/', views.test, name='test'),
	path('about/',views.about,name="about"),
    path('packages/',views.packages,name="packages"),
    path('api/v1/packages/', views.mobile_packages_api, name='mobile_packages_api'),
    path('api/v1/voting/campaigns/', views.mobile_voting_campaigns_api, name='mobile_voting_campaigns_api'),
    path('api/v1/auth/request-code/', views.mobile_request_login_code, name='mobile_request_login_code'),
    path('api/v1/auth/verify-code/', views.mobile_verify_login_code, name='mobile_verify_login_code'),
    path('api/v1/dashboard/', views.mobile_dashboard_api, name='mobile_dashboard_api'),
    path('api/v1/voting/initialize/', views.mobile_initialize_vote_api, name='mobile_initialize_vote_api'),
    path('packages/<slug:slug>/',views.package_detail,name="package_detail"),
    path('packages/<slug:slug>/checkout/',views.package_checkout,name="package_checkout"),
    path('packages/order/<int:order_id>/',views.package_order,name="package_order"),
    path('packages/order/<int:order_id>/upgrade/', views.package_upgrade, name='package_upgrade'),
    path('packages/api/calculate-plan/',views.api_calculate_plan,name="api_calculate_plan"),
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
    path('voting/nominate/', views.nominate, name='nominate_form_alias'),
    path('voting/payment/initialize/', voting_views.initialize_payment, name='initialize_payment'),
    path('voting/payment/verify/<str:reference>/', voting_views.verify_payment, name='verify_payment'),
    path('voting/payment/thank-you/', voting_views.voting_thank_you, name='voting_thank_you'),
    path('voting/webhook/paystack/', voting_views.paystack_webhook, name='paystack_webhook'),
    path('voting/<slug:slug>/', voting_views.voting_campaign_detail, name='voting_campaign'),
    
    # API: Verify Rest Card
    path('api/verify-rest-card/', voting_views.verify_rest_card, name='verify_rest_card'),
    
    # Community & Rest Card URLs
    path('community/', views.community_stats, name='community_stats'),
    path('rest-card/', views.rest_card_info, name='rest_card_info'),
    path('rest-card/join/', views.rest_card_waitlist_join, name='rest_card_waitlist_join'),
    path('rest-card/status/', views.rest_card_status, name='rest_card_status'),
    path('rest-card/signup/', views.rest_card_signup, name='rest_card_signup'),
    path('token-wallet/', views.token_wallet_view, name='token_wallet'),
    path('unwind-and-win/', views.unwind_and_win, name='unwind_and_win'),
    path('raising-readers/', views.raising_readers, name='raising_readers'),
    path('edbritish-trial/', views.edbritish_trial, name='edbritish_trial'),
    path('edbritish-trial/register/', views.edbritish_trial_registration, name='edbritish_trial_registration'),
    # path('vote/', views.vote, name='vote'),
    path('payment/<int:vote_id>/', views.payment, name='payment'),
    path('vote-confirmation/<int:vote_id>/', views.vote_confirmation, name='vote_confirmation'),
    path('nominate/', views.nominate, name='nominate'),
    path('nomination-confirmation/<int:nominee_id>/', views.nomination_confirmation, name='nomination_confirmation'),
    path('my-rest-card/', views.my_rest_card, name='my_rest_card'),
    path('generate-rest-card/<int:card_id>/', views.generate_rest_card, name='generate_rest_card'),
    path('explore/', views.explore, name='explore'),
    
    # User Dashboard URLs
    path('dashboard/login/', views.user_dashboard_login, name='user_dashboard_login'),
    path('dashboard/verify-otp/', views.user_dashboard_verify_otp, name='user_dashboard_verify_otp'),
    path('dashboard/', views.user_dashboard, name='user_dashboard'),
    path('dashboard/logout/', views.user_dashboard_logout, name='user_dashboard_logout'),
    path('dashboard/claim-points/', views.claim_frozen_points, name='claim_frozen_points'),

    # Installment Payments URLs (Paystack)
    path('dashboard/packages/<int:order_id>/contribute/', views.initialize_installment_payment, name='initialize_installment_payment'),
    path('dashboard/packages/verify/<str:reference>/', views.verify_installment_payment, name='verify_installment_payment'),
]


handler404 = 'Web.views.custom_404'
