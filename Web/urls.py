from django.urls import path
from . import views


urlpatterns = [
	path('',views.home,name="home"),
	path('about/',views.about,name="about"),
	path('packages/',views.packages,name="packages"),
    path('blog/<slug:slug>/', views.blog_detail, name='blog_detail'),

    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('add-post/', views.add_post_view, name='add_post'),
    path('add-event/', views.add_event_view, name='add_event'),

    path('ajax/add-post/', views.add_post_ajax, name='add_post_ajax'),
    path('ajax/add-event/', views.add_event_ajax, name='add_event_ajax'),


    path('blog/', views.blog_list, name='blog'),
    path('blog/', views.blog_list, name='blog_list'),
    path('contact/', views.contact, name='contact'),



    path('dashboard/post/<int:post_id>/update/', views.update_post_ajax, name='update_post_ajax'),
    path('dashboard/post/<int:post_id>/delete/', views.delete_post_ajax, name='delete_post_ajax'),
    path('dashboard/event/<int:event_id>/update/', views.update_event_ajax, name='update_event_ajax'),
    path('dashboard/event/<int:event_id>/delete/', views.delete_event_ajax, name='delete_event_ajax'),

    path('events/<int:id>/edit/', views.edit_event, name='edit_event'),
    path('events/<int:id>/delete/', views.delete_event, name='delete_event'),
    path('events/upcoming/json/', views.get_upcoming_events, name='get_upcoming_events'),

]


handler404 = 'Web.views.custom_404'