# dashboard/models.py
from django.db import models
from Web import models as web_models

# Optional: dashboard-specific managers
class PublishedManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_published=True)

class BlogCategory(web_models.BlogCategory):
    class Meta:
        proxy = True
        verbose_name = "Blog category"
        verbose_name_plural = "Blog categories"

class Post(web_models.Post):
    # dashboard-only helpers/ordering/managers allowed here
    objects = models.Manager()
    published = PublishedManager()

    class Meta:
        proxy = True
        # dashboard can choose a different default ordering if you want:
        ordering = ["-created_at"]
        verbose_name = "Post"
        verbose_name_plural = "Posts"

    @property
    def status_label(self):
        return "Published" if self.is_published else "Draft"

class Event(web_models.Event):
    class Meta:
        proxy = True
        ordering = ["date", "-created_at"]
        verbose_name = "Event"
        verbose_name_plural = "Events"
