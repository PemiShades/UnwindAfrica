"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic.base import RedirectView, TemplateView

from Web.sitemaps import StaticViewSitemap, BlogSitemap, EventSitemap, CampaignSitemap

sitemaps = {
    'static': StaticViewSitemap,
    'blog': BlogSitemap,
    'events': EventSitemap,
    'campaigns': CampaignSitemap,
}

urlpatterns = [
    path('admin/', admin.site.urls),
    # Admin Dashboard (CMS) - moved from /dashboard/ to avoid conflict with user dashboard
    path('cms/', include('dashboard.urls')),
    # Sitemap
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    # Robots.txt
    path('robots.txt', TemplateView.as_view(template_name='robots.txt', content_type='text/plain')),
    # Auth
    path("accounts/login/", auth_views.LoginView.as_view(
        template_name="dashboard/login.html"
    ), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(next_page="login"), name="logout"),
    # User dashboard is in Web.urls at /dashboard/
    # Safety: if anything still tries to go here, bounce to user dashboard
    path('accounts/profile/',
         RedirectView.as_view(pattern_name='user_dashboard', permanent=False)),
    path('', include('Web.urls')),
]

# Serve static and media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
