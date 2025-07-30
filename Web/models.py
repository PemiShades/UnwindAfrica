# Create your models here.
from django.db import models
from django.utils import timezone


def upload_thumbnail_image(self, post_id):
	return "uploads/posts/{post_id}"

# blog model

class BlogCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name

class Post(models.Model):
    thumbnail = models.ImageField(upload_to='posts/thumbnails/')
    category = models.ForeignKey(BlogCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="posts")
    title = models.CharField(max_length=350)
    content = models.TextField(null=True, help_text="Write the full blog post here")
    created_at = models.DateTimeField(auto_now_add=True)
    is_published = models.BooleanField(default=True)

    def __str__(self):
        return self.title


class Event(models.Model):
    flier = models.ImageField(upload_to='events/fliers/') 
    thumbnail = models.ImageField(upload_to='events/thumbnails/')
    title = models.CharField(max_length=100)
    brief_text = models.CharField(max_length=250)
    date = models.DateField()
    is_expired = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        self.is_expired = self.date < timezone.now().date()
        super().save(*args, **kwargs)
