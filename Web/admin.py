from django.contrib import admin
from .models import Event,Post, BlogCategory
# Register your models here.

admin.site.register(Event)
admin.site.register(Post)
admin.site.register(BlogCategory)