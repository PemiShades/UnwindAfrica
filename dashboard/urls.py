from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

urlpatterns = [
    path('', views.dashboard_home, name='dashboard_home'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),

    path('create-blog/', views.create_blog_page, name='create_blog_page'),
    path('submit-blog/', views.create_blog, name='create_blog'),

    path('post/add/', views.create_blog, name='create_blog'),
    path('post/<slug:slug>/edit/', views.edit_blog, name='edit_blog'),
    path('post/<slug:slug>/delete/', views.delete_blog, name='delete_blog'),


    path('event/add/', views.create_event, name='create_event'),
    path('event/<int:event_id>/edit/', views.edit_event, name='edit_event'),
    path('event/<int:id>/delete/', views.delete_event, name='delete_event'),

]
