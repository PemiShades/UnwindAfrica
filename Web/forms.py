from django import forms
from .models import Post, Event

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['thumbnail', 'category', 'title', 'content', 'is_published']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input'}),
            'content': forms.Textarea(attrs={'rows': 6, 'class': 'form-textarea'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
        }

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['flier', 'thumbnail', 'title', 'brief_text', 'date']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input'}),
            'brief_text': forms.TextInput(attrs={'class': 'form-input'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
        }
