from django.urls import path
from . import views


urlpatterns = [
	path('',views.home,name="home"),
    path('test/', views.test, name='test'),
	path('about/',views.about,name="about"),
	path('packages/',views.packages,name="packages"),
    path('blog/<slug:slug>/', views.blog_detail, name='blog_detail'),
    path('unwind-thrive/', views.unwind_thrive, name='services'),

    path("quotes/request/", views.quote_request, name="quote_request"),

    path('blog/', views.blog_list, name='blog'),
    path('blog/', views.blog_list, name='blog_list'),
    path('contact/', views.contact, name='contact'),



]


handler404 = 'Web.views.custom_404'