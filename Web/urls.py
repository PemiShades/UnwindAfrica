from django.urls import path
from . import views


urlpatterns = [
	path('',views.home,name="home"),
	path('about/',views.about,name="about"),
	path('packages/',views.packages,name="packages"),
]


handler404 = 'Web.views.custom_404'