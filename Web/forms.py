from django import forms
from .models import Post, Event

from django import forms
from .models import Post

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'category', 'thumbnail', 'image', 'content', 'is_published']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full border border-gray-300 rounded-md px-4 py-2 focus:outline-none focus:ring-2 focus:ring-teal-500'
            }),
            'category': forms.Select(attrs={
                'class': 'w-full border border-gray-300 rounded-md px-4 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-teal-500'
            }),
            'thumbnail': forms.ClearableFileInput(attrs={
                'class': 'block w-full text-sm text-gray-600 bg-white border border-gray-300 rounded-md cursor-pointer file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-teal-600 file:text-white hover:file:bg-teal-700'
            }),
            'image': forms.ClearableFileInput(attrs={
                'class': 'block w-full text-sm text-gray-600 bg-white border border-gray-300 rounded-md cursor-pointer file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-gray-500 file:text-white hover:file:bg-gray-600'
            }),
            'content': forms.Textarea(attrs={
                'rows': 10,
                'class': 'w-full border border-gray-300 rounded-md px-4 py-3 focus:outline-none focus:ring-2 focus:ring-teal-500'
            }),
        }


# class PostForm(forms.ModelForm):
#     class Meta:
#         model = Post
#         fields = ['thumbnail', 'category', 'title', 'content', 'is_published']
#         widgets = {
#             'title': forms.TextInput(attrs={'class': 'form-input'}),
#             'content': forms.Textarea(attrs={'rows': 6, 'class': 'form-textarea'}),
#             'category': forms.Select(attrs={'class': 'form-select'}),
#         }

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['flier', 'thumbnail', 'name', 'description', 'location','date']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input'}),
            'brief_text': forms.TextInput(attrs={'class': 'form-input'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
        }
