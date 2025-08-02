from django.utils.text import slugify
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

# class Post(models.Model):
#     thumbnail = models.ImageField(upload_to='posts/thumbnails/')
#     image = models.ImageField(upload_to='blog_images/', blank=True, null=True)
#     category = models.ForeignKey(BlogCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="posts")
#     title = models.CharField(max_length=350)
#     content = models.TextField(null=True, help_text="Write the full blog post here")
#     created_at = models.DateTimeField(auto_now_add=True)
#     is_published = models.BooleanField(default=True)

#     def __str__(self):
#         return self.title



class Post(models.Model):
    CATEGORY_CHOICES = [
        ("Travel", "Travel"),
        ("Health", "Health"),
        ("Lifestyle", "Lifestyle"),
        ("Wellness", "Wellness"),
        ("Adventure", "Adventure"),
        ("Relaxation", "Relaxation"),
        ("Food", "Food"),
        ("Events", "Events"),
        ("Culture", "Culture"),
        ("Mindfulness", "Mindfulness"),
        ("Inspiration", "Inspiration"),
        ("Nature", "Nature"),
        ("Guides", "Guides"),
        ("Stories", "Stories"),
        ("Experiences", "Experiences"),
    ]

    thumbnail = models.ImageField(upload_to='posts/thumbnails/')
    image = models.ImageField(upload_to='blog_images/', blank=True, null=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default="Travel")
    title = models.CharField(max_length=350)
    content = models.TextField(null=True, help_text="Write the full blog post here")
    created_at = models.DateTimeField(auto_now_add=True)
    is_published = models.BooleanField(default=True)

    slug = models.SlugField(unique=True, blank=True)
    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)



class Event(models.Model):
    flier = models.ImageField(upload_to='events/fliers/') 
    thumbnail = models.ImageField(upload_to='events/thumbnails/')
    date = models.DateField()
    is_expired = models.BooleanField(default=False)
    name = models.CharField(max_length=255,null=True,blank=True)  # Add this
    description = models.TextField(null=True,blank=True)         # Add this
    location = models.CharField(max_length=255, null=True,blank=True)  # Add this
    created_at = models.DateTimeField(auto_now_add=True)  # 👈 add this

    def save(self, *args, **kwargs):
        self.is_expired = self.date < timezone.now().date()
        super().save(*args, **kwargs)
