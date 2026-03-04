# Web/sitemaps.py
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Post, Event, VotingCampaign


# Static pages
class StaticViewSitemap(Sitemap):
    priority = 0.9
    changefreq = 'weekly'

    def items(self):
        return [
            'home',
            'about',
            'contact',
            'packages',
            'nominate',
            'rest_card_signup',
            'voting_campaigns_list',
            'faq',
            'explore',
            'blog_list',
        ]

    def location(self, item):
        return reverse(item)


# Blog posts
class BlogSitemap(Sitemap):
    changefreq = 'monthly'
    priority = 0.7

    def items(self):
        return Post.objects.filter(is_published=True)

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return obj.get_absolute_url()


# Events
class EventSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.8

    def items(self):
        return Event.objects.all()

    def lastmod(self, obj):
        return obj.created_at

    def location(self, obj):
        return obj.get_absolute_url()


# Voting campaigns
class CampaignSitemap(Sitemap):
    changefreq = 'daily'
    priority = 0.9  # high priority since this is active content

    def items(self):
        return VotingCampaign.objects.all()

    def lastmod(self, obj):
        return obj.updated_at if hasattr(obj, 'updated_at') else obj.start_date

    def location(self, obj):
        return reverse('voting_campaign', args=[obj.slug])
