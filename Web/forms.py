# dashboard/forms.py
from __future__ import annotations

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.forms import (
    CheckboxInput,
    ClearableFileInput,
    DateInput,
    Select,
    Textarea,
    TextInput,
)

# IMPORTANT: import the PROXY models from dashboard.models
# (These point to the same DB tables defined in web.models)
from .models import Post, Event


class AdminAuthenticationForm(AuthenticationForm):
    """
    Restrict dashboard login to staff users.
    """
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not getattr(user, "is_staff", False):
            raise forms.ValidationError(
                "You don't have admin access on this dashboard.",
                code="no_admin",
            )


class PostForm(forms.ModelForm):
    """
    Editor-facing Post form.

    We intentionally exclude:
      - slug, excerpt, read_minutes, badge  (auto-generated in model.save())
      - is_published, is_featured           (set by actions in the view/UI, not raw inputs)

    Editable fields: title, category, content, thumbnail, image
    """
    class Meta:
        model = Post
        fields = [
            "title",
            "category",
            "content",
            "thumbnail",
            "image",
        ]
        widgets = {
            "title": TextInput(attrs={
                "class": "field ring-brand",
                "placeholder": "Post title",
                "maxlength": 350,
            }),
            "category": Select(attrs={
                "class": "field ring-brand",
            }),
            "content": Textarea(attrs={
                "class": "field ring-brand",
                "rows": 12,
                "placeholder": "Write your post content…",
            }),
            "thumbnail": ClearableFileInput(attrs={
                "class": "field ring-brand",
                "accept": "image/*",
            }),
            "image": ClearableFileInput(attrs={
                "class": "field ring-brand",
                "accept": "image/*",
            }),
        }

    def clean_title(self):
        title = self.cleaned_data.get("title", "").strip()
        if not title:
            raise forms.ValidationError("Title is required.")
        return title


class EventForm(forms.ModelForm):
    """
    Event form aligned with web.models.Event (proxied here).

    Fields: name, description, date, location, thumbnail, flier, badge
    Note: There is NO `is_published` on Event; don't add it.
    """
    class Meta:
        model = Event
        fields = ["name", "description", "date", "location", "thumbnail", "flier", "badge"]
        widgets = {
            "name": TextInput(attrs={
                "class": "field ring-brand",
                "placeholder": "Event name",
                "maxlength": 255,
            }),
            "description": Textarea(attrs={
                "class": "field ring-brand",
                "rows": 6,
                "placeholder": "Describe the event…",
            }),
            "date": DateInput(attrs={
                "type": "date",
                "class": "field ring-brand",
            }),
            "location": TextInput(attrs={
                "class": "field ring-brand",
                "placeholder": "Event location",
                "maxlength": 255,
            }),
            "thumbnail": ClearableFileInput(attrs={
                "class": "field ring-brand",
                "accept": "image/*",
            }),
            "flier": ClearableFileInput(attrs={
                "class": "field ring-brand",
                "accept": "image/*",
            }),
            "badge": Select(attrs={
                "class": "field ring-brand",
            }),
        }

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()
        if not name:
            raise forms.ValidationError("Event name is required.")
        return name


# Back-compat alias so existing imports like `from dashboard.forms import BlogPostForm`
# continue to work without refactoring other files.
BlogPostForm = PostForm
