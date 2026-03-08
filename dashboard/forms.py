# from django import forms
# from Web.models import Post, Event

# # from django import forms
# # from Web.models import Post

# class BlogForm(forms.ModelForm):
#     class Meta:
#         model = Post
#         fields = ['title', 'category', 'thumbnail', 'image', 'content', 'is_published']
#         widgets = {
#             'content': forms.Textarea(attrs={'rows': 8}),
#         }


# from django import forms
# from Web.models import Event

# class EventForm(forms.ModelForm):
#     class Meta:
#         model = Event
#         fields = ['flier', 'thumbnail', 'name', 'location', 'description', 'date']
#         widgets = {
#             'date': forms.DateInput(attrs={'type': 'date'}),
#         }







# dashboard/forms.py
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
from Web.models import VotingCampaign, Nominee



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





class AdminAuthenticationForm(AuthenticationForm):
    """
    Staff-only login form with UI-friendly widget attrs.
    """
    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request=request, *args, **kwargs)
        # Style the username/password inputs so your CSS hooks apply
        self.fields["username"].widget.attrs.update({
            "class": "",                 # leave empty, since you wrap with .input
            "placeholder": "your-username",
            "autocomplete": "username",
        })
        self.fields["password"].widget.attrs.update({
            "class": "",                 # leave empty; wrapper supplies look
            "placeholder": "••••••••",
            "autocomplete": "current-password",
        })

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


class VotingCampaignForm(forms.ModelForm):
    """
    Form for creating and editing voting campaigns in the dashboard.
    """
    class Meta:
        model = VotingCampaign
        fields = [
            'name', 'tagline', 'description', 'start_date', 'end_date',
            'vote_price', 'prize_description', 'is_active'
        ]
        widgets = {
            'name': TextInput(attrs={
                "class": "field ring-brand",
                "placeholder": "Campaign name (e.g., Valentine Edition)",
                "maxlength": 255,
            }),
            'tagline': TextInput(attrs={
                "class": "field ring-brand",
                "placeholder": "Short tagline (e.g., Spread love this February)",
                "maxlength": 255,
            }),
            'description': Textarea(attrs={
                "class": "field ring-brand",
                "rows": 6,
                "placeholder": "Detailed campaign description...",
            }),
            'start_date': DateInput(attrs={
                "type": "date",
                "class": "field ring-brand",
            }),
            'end_date': DateInput(attrs={
                "type": "date",
                "class": "field ring-brand",
            }),
            'vote_price': TextInput(attrs={
                "class": "field ring-brand",
                "placeholder": "Price per vote",
            }),
            'prize_description': Textarea(attrs={
                "class": "field ring-brand",
                "rows": 4,
                "placeholder": "Prize description for winners...",
            }),
            'is_active': CheckboxInput(attrs={
                "class": "field ring-brand",
            }),
        }


class VotingCampaignForm(forms.ModelForm):
    """
    Form for creating and editing voting campaigns.
    """
    class Meta:
        model = VotingCampaign
        fields = [
            "name", "description", "tagline", "start_date", "end_date",
            "vote_price", "rest_points_per_vote",
            "grand_prize", "grand_prize_description",
            "second_prize", "second_prize_description",
            "third_prize", "third_prize_description",
            "prize_description", "banner_image", "is_active"
        ]
        widgets = {
            "name": TextInput(attrs={
                "class": "field ring-brand",
                "placeholder": "Campaign name (e.g., Nominate to Unwind – February Edition)",
                "maxlength": 255,
            }),
            "description": Textarea(attrs={
                "class": "field ring-brand",
                "rows": 4,
                "placeholder": "Campaign description…",
            }),
            "tagline": TextInput(attrs={
                "class": "field ring-brand",
                "placeholder": "Short tagline (e.g., Spread love and relaxation)",
                "maxlength": 255,
            }),
            "start_date": DateInput(attrs={
                "type": "date",
                "class": "field ring-brand",
            }),
            "end_date": DateInput(attrs={
                "type": "date",
                "class": "field ring-brand",
            }),
            "vote_price": TextInput(attrs={
                "class": "field ring-brand",
                "placeholder": "Price per vote (e.g., 500)",
            }),
            "rest_points_per_vote": TextInput(attrs={
                "class": "field ring-brand",
                "placeholder": "Rest points per vote (e.g., 100)",
            }),
            "grand_prize": TextInput(attrs={
                "class": "field ring-brand",
                "placeholder": "Grand prize (e.g., Luxury Getaway)",
                "maxlength": 255,
            }),
            "grand_prize_description": Textarea(attrs={
                "class": "field ring-brand",
                "rows": 3,
                "placeholder": "Grand prize description…",
            }),
            "second_prize": TextInput(attrs={
                "class": "field ring-brand",
                "placeholder": "Second prize (e.g., Spa Retreat)",
                "maxlength": 255,
            }),
            "second_prize_description": Textarea(attrs={
                "class": "field ring-brand",
                "rows": 3,
                "placeholder": "Second prize description…",
            }),
            "third_prize": TextInput(attrs={
                "class": "field ring-brand",
                "placeholder": "Third prize (e.g., Dinner & Movie)",
                "maxlength": 255,
            }),
            "third_prize_description": Textarea(attrs={
                "class": "field ring-brand",
                "rows": 3,
                "placeholder": "Third prize description…",
            }),
            "prize_description": Textarea(attrs={
                "class": "field ring-brand",
                "rows": 3,
                "placeholder": "Overall prizes description…",
            }),
            "banner_image": ClearableFileInput(attrs={
                "class": "field ring-brand",
                "accept": "image/*",
            }),
            "is_active": CheckboxInput(attrs={
                "class": "field ring-brand",
            }),
        }

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()
        if not name:
            raise forms.ValidationError("Campaign name is required.")
        return name

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError("Start date must be before end date.")

        return cleaned_data


# Back-compat alias so existing imports like `from dashboard.forms import BlogPostForm`
# continue to work without refactoring other files.
BlogPostForm = PostForm

# Book Form for Raising Readers
from Web.models import Book

class BookForm(forms.ModelForm):
    """
    Form for adding/editing books in Raising Readers
    """
    class Meta:
        model = Book
        fields = [
            'title', 'author', 'cover_image', 'description', 
            'age_category', 'genre', 'status', 'isbn'
        ]
        widgets = {
            'title': TextInput(attrs={
                "class": "field ring-brand",
                "placeholder": "Book title",
                "maxlength": 255,
            }),
            'author': TextInput(attrs={
                "class": "field ring-brand",
                "placeholder": "Author name",
                "maxlength": 255,
            }),
            'description': Textarea(attrs={
                "class": "field ring-brand",
                "rows": 4,
                "placeholder": "Book description or summary...",
            }),
            'age_category': Select(attrs={
                "class": "field ring-brand",
            }),
            'genre': Select(attrs={
                "class": "field ring-brand",
            }),
            'status': Select(attrs={
                "class": "field ring-brand",
            }),
            'isbn': TextInput(attrs={
                "class": "field ring-brand",
                "placeholder": "ISBN (optional)",
                "maxlength": 20,
            }),
            'cover_image': ClearableFileInput(attrs={
                "class": "field ring-brand",
                "accept": "image/*",
            }),
        }

    def clean_title(self):
        title = self.cleaned_data.get("title", "").strip()
        if not title:
            raise forms.ValidationError("Title is required.")
        return title


# Nominee Form for editing nominee stories
class NomineeForm(forms.ModelForm):
    """
    Form for editing nominee details including their story.
    """
    class Meta:
        model = Nominee
        fields = [
            "name",
            "number",
            "photo",
            "story",
            "instagram_handle",
            "order",
        ]
        widgets = {
            "name": TextInput(attrs={
                "class": "field ring-brand",
                "placeholder": "Nominee name",
                "maxlength": 255,
            }),
            "number": TextInput(attrs={
                "class": "field ring-brand",
                "placeholder": "Nominee number (e.g., 001)",
                "maxlength": 50,
            }),
            "photo": ClearableFileInput(attrs={
                "class": "field ring-brand",
                "accept": "image/*",
            }),
            "story": Textarea(attrs={
                "class": "field ring-brand",
                "rows": 8,
                "placeholder": "Tell their story - why they deserve to unwind...",
            }),
            "instagram_handle": TextInput(attrs={
                "class": "field ring-brand",
                "placeholder": "Instagram handle (without @)",
                "maxlength": 100,
            }),
            "order": TextInput(attrs={
                "class": "field ring-brand",
                "type": "number",
                "min": "0",
            }),
        }

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()
        if not name:
            raise forms.ValidationError("Name is required.")
        return name
