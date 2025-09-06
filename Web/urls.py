from django.urls import path
from . import views


urlpatterns = [
	path('',views.home,name="home"),
    path('test/', views.test, name='test'),
	path('about/',views.about,name="about"),
	path('packages/',views.packages,name="packages"),
    path('blog/<slug:slug>/', views.blog_detail, name='blog_detail'),




    path('blog/', views.blog_list, name='blog'),
    path('blog/', views.blog_list, name='blog_list'),
    path('contact/', views.contact, name='contact'),



]


handler404 = 'Web.views.custom_404'