# dashboard/admin.py
from django.contrib import admin
from .models import Post, Event  # proxies to Web.models

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "is_published", "is_featured", "created_at")
    list_filter  = ("is_published", "is_featured", "created_at", "category")
    search_fields = ("title", "excerpt", "content", "slug")
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("-created_at",)

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("name", "date", "location", "badge", "created_at")
    list_filter  = ("date", "badge", "created_at",)
    search_fields = ("name", "location", "description", "slug")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("date", "-created_at")
