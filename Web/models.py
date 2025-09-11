from django.db import models
from django.utils.text import slugify
from django.utils import timezone
from django.urls import reverse


class BlogCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name


class Post(models.Model):
    CATEGORY_CHOICES = [
        ("Travel", "Travel"), ("Health", "Health"), ("Lifestyle", "Lifestyle"),
        ("Wellness", "Wellness"), ("Adventure", "Adventure"), ("Relaxation", "Relaxation"),
        ("Food", "Food"), ("Events", "Events"), ("Culture", "Culture"),
        ("Mindfulness", "Mindfulness"), ("Inspiration", "Inspiration"),
        ("Nature", "Nature"), ("Guides", "Guides"), ("Stories", "Stories"),
        ("Experiences", "Experiences"),
    ]

    # Card visuals
    thumbnail = models.ImageField(upload_to='posts/thumbnails/')
    image = models.ImageField(upload_to='blog_images/', blank=True, null=True)

    # Metadata
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default="Travel")
    title = models.CharField(max_length=350)
    excerpt = models.TextField(blank=True, help_text="Short teaser used on cards")
    content = models.TextField(null=True, help_text="Full post content")
    read_minutes = models.PositiveIntegerField(default=4)

    # Flags
    is_published = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)

    # Slug + dates
    slug = models.SlugField(unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Optional chip/badge on card (e.g., 'Guide')
    badge = models.CharField(max_length=40, blank=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("blog_detail", kwargs={"slug": self.slug})

    def save(self, *args, **kwargs):
        # slug (yours)
        if not self.slug:
            base = slugify(self.title)
            slug = base
            i = 2
            while Post.objects.filter(slug=slug).exists():
                slug = f"{base}-{i}"; i += 1
            self.slug = slug

        # excerpt (first ~180 chars, plain text)
        if not self.excerpt and self.content:
            text = re.sub(r"<[^>]+>", "", self.content)
            text = re.sub(r"\s+", " ", text).strip()
            self.excerpt = (text[:177] + "…") if len(text) > 180 else text

        # read_minutes (~220 wpm)
        if (not self.read_minutes or self.read_minutes == 0) and self.content:
            words = len(re.findall(r"\b\w+\b", self.content))
            self.read_minutes = max(1, round(words / 220))

        # optional badge default
        if not self.badge:
            if self.is_featured:
                self.badge = "Featured"
            elif self.category == "Guides":
                self.badge = "Guide"

        super().save(*args, **kwargs)


class Event(models.Model):
    # Card visuals
    flier = models.ImageField(upload_to='events/fliers/')
    thumbnail = models.ImageField(upload_to='events/thumbnails/')

    # Details
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=255, blank=True)
    date = models.DateField()

    # Nice label on card (e.g., Featured, Limited, New, Premium)
    BADGE_CHOICES = [("Featured", "Featured"), ("Limited", "Limited"), ("New", "New"), ("Premium", "Premium")]
    badge = models.CharField(max_length=20, blank=True, choices=BADGE_CHOICES)

    # Slug + dates
    slug = models.SlugField(unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date", "-created_at"]

    def __str__(self):
        return f"{self.name} — {self.date}"

    @property
    def is_expired(self):
        return self.date < timezone.now().date()

    def get_absolute_url(self):
        return reverse("event_detail", kwargs={"slug": self.slug})

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)
            slug = base
            i = 2
            while Event.objects.filter(slug=slug).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)
