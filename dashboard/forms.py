from django import forms
from Web.models import Post, Event

# from django import forms
# from Web.models import Post

class BlogForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'category', 'thumbnail', 'image', 'content', 'is_published']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 8}),
        }


from django import forms
from Web.models import Event

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['flier', 'thumbnail', 'name', 'location', 'description', 'date']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }
