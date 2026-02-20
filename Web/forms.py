from django import forms
from django.forms import TextInput, Textarea, Select, ClearableFileInput, DateInput, CheckboxInput

from .models import Post, Event, VotingCampaign, Nominee, Vote, RestCard


class PostForm(forms.ModelForm):
    """Form for creating and editing blog posts"""
    class Meta:
        model = Post
        fields = ['title', 'category', 'content', 'thumbnail', 'image', 'is_published']
        widgets = {
            'title': TextInput(attrs={
                'class': 'field ring-brand',
                'placeholder': 'Post title',
                'maxlength': 350,
            }),
            'category': Select(attrs={
                'class': 'field ring-brand',
            }),
            'content': Textarea(attrs={
                'class': 'field ring-brand',
                'rows': 8,
                'placeholder': 'Write your post content…',
            }),
            'thumbnail': ClearableFileInput(attrs={
                'class': 'field ring-brand',
                'accept': 'image/*',
            }),
            'image': ClearableFileInput(attrs={
                'class': 'field ring-brand',
                'accept': 'image/*',
            }),
            'is_published': CheckboxInput(attrs={
                'class': 'field ring-brand',
            }),
        }


class RestCardSignupForm(forms.ModelForm):
    """Form for Rest Card early sign-up"""
    class Meta:
        model = RestCard
        fields = ['member_name', 'member_email', 'member_phone']
        widgets = {
            'member_name': TextInput(attrs={
                'class': 'field ring-brand',
                'placeholder': 'Enter your full name',
                'maxlength': 255,
            }),
            'member_email': TextInput(attrs={
                'class': 'field ring-brand',
                'placeholder': 'Enter your email address',
                'type': 'email',
            }),
            'member_phone': TextInput(attrs={
                'class': 'field ring-brand',
                'placeholder': 'Enter your phone number',
                'maxlength': 20,
            }),
        }


class EventForm(forms.ModelForm):
    """Form for creating and editing events"""
    class Meta:
        model = Event
        fields = ['name', 'description', 'date', 'location', 'thumbnail', 'flier', 'badge']
        widgets = {
            'name': TextInput(attrs={
                'class': 'field ring-brand',
                'placeholder': 'Event name',
                'maxlength': 255,
            }),
            'description': Textarea(attrs={
                'class': 'field ring-brand',
                'rows': 6,
                'placeholder': 'Describe the event…',
            }),
            'date': DateInput(attrs={
                'type': 'date',
                'class': 'field ring-brand',
            }),
            'location': TextInput(attrs={
                'class': 'field ring-brand',
                'placeholder': 'Event location',
                'maxlength': 255,
            }),
            'thumbnail': ClearableFileInput(attrs={
                'class': 'field ring-brand',
                'accept': 'image/*',
            }),
            'flier': ClearableFileInput(attrs={
                'class': 'field ring-brand',
                'accept': 'image/*',
            }),
            'badge': Select(attrs={
                'class': 'field ring-brand',
            }),
        }


class NominationForm(forms.ModelForm):
    """
    Form for nominating an individual for a campaign.
    """
    NOMINATOR_NAME = forms.CharField(
        label='Nominator\'s Full Name',
        widget=TextInput(attrs={
            'class': 'field ring-brand',
            'placeholder': 'Enter your full name',
            'required': True
        })
    )
    NOMINATOR_EMAIL = forms.EmailField(
        label='Nominator\'s Email',
        widget=TextInput(attrs={
            'class': 'field ring-brand',
            'placeholder': 'Enter your email',
            'required': True
        })
    )
    NOMINATOR_PHONE = forms.CharField(
        label='Nominator\'s Phone Number',
        widget=TextInput(attrs={
            'class': 'field ring-brand',
            'placeholder': 'Enter your phone number',
            'required': True
        })
    )
    NOMINEE_NAME = forms.CharField(
        label='Nominee\'s Full Name',
        widget=TextInput(attrs={
            'class': 'field ring-brand',
            'placeholder': 'Enter nominee\'s full name',
            'required': True
        })
    )
    NOMINEE_AGE = forms.IntegerField(
        label='Nominee\'s Age',
        widget=TextInput(attrs={
            'class': 'field ring-brand',
            'placeholder': 'Enter nominee\'s age',
            'required': True
        })
    )
    NOMINEE_LOCATION = forms.CharField(
        label='Nominee\'s Location',
        widget=TextInput(attrs={
            'class': 'field ring-brand',
            'placeholder': 'Enter nominee\'s location',
            'required': True
        })
    )
    NOMINEE_SCHOOL = forms.CharField(
        label='Nominee\'s School / Institution (optional)',
        widget=TextInput(attrs={
            'class': 'field ring-brand',
            'placeholder': 'Enter nominee\'s school or institution',
            'required': False
        })
    )
    NOMINATION_REASON = forms.CharField(
        label='Why are you nominating this person?',
        widget=Textarea(attrs={
            'class': 'field ring-brand',
            'placeholder': 'Tell us why this person deserves to be recognized...',
            'required': True,
            'rows': 4
        })
    )
    NOMINEE_PHOTO = forms.ImageField(
        label='Upload Photo of Nominee (optional)',
        widget=ClearableFileInput(attrs={
            'class': 'field ring-brand',
            'accept': 'image/*',
            'required': False
        })
    )

    class Meta:
        model = Nominee
        fields = []

    def save(self, campaign, commit=True):
        """Custom save method to handle nomination with auto-numbering"""
        # Generate nominee number (001 to 50)
        next_number = Nominee.objects.filter(campaign=campaign).count() + 1
        nominee_number = f"{next_number:03d}"  # Format as 001, 002, etc.
        
        # Create nominee
        nominee = Nominee(
            campaign=campaign,
            number=nominee_number,
            name=self.cleaned_data['NOMINEE_NAME'],
            story=self.cleaned_data['NOMINATION_REASON'],
            photo=self.cleaned_data.get('NOMINEE_PHOTO')
        )
        
        if commit:
            nominee.save()
        
        return nominee


class VotingForm(forms.ModelForm):
    """
    Form for users to vote for nominees in a campaign.
    Voters must manually enter nominee information from their nominee card.
    """
    NOMINEE_NUMBER = forms.CharField(
        label='Nominee Number',
        widget=TextInput(attrs={
            'class': 'field ring-brand',
            'placeholder': 'Enter nominee number',
            'required': True
        })
    )
    COUPLE_NAME = forms.CharField(
        label='Couple Name',
        widget=TextInput(attrs={
            'class': 'field ring-brand',
            'placeholder': 'Enter couple name exactly as written on nominee card',
            'required': True
        })
    )
    VOTER_NAME = forms.CharField(
        label='Your Full Name',
        widget=TextInput(attrs={
            'class': 'field ring-brand',
            'placeholder': 'Enter your full name',
            'required': True
        })
    )
    VOTER_PHONE = forms.CharField(
        label='Your Phone Number',
        widget=TextInput(attrs={
            'class': 'field ring-brand',
            'placeholder': 'Enter your phone number',
            'required': True
        })
    )
    NUMBER_OF_VOTES = forms.ChoiceField(
        label='Number of Votes',
        choices=[
            (1, '1 Vote – ₦500'),
            (2, '2 Votes – ₦1,000'),
            (5, '5 Votes – ₦2,500'),
            (10, '10 Votes – ₦5,000 (2 bonus votes)'),
            (20, '20 Votes – ₦10,000 (5 bonus votes)'),
            (60, '60 Votes – ₦30,000 (10 bonus votes)')
        ],
        widget=Select(attrs={
            'class': 'field ring-brand',
            'required': True
        })
    )
    PROOF_OF_PAYMENT = forms.ImageField(
        label='Upload Proof of Payment',
        widget=ClearableFileInput(attrs={
            'class': 'field ring-brand',
            'accept': 'image/*',
            'required': True
        })
    )

    class Meta:
        model = Vote
        fields = []

    def clean_number_of_votes(self):
        """Convert string to integer for storage"""
        data = self.cleaned_data.get('NUMBER_OF_VOTES')
        if data:
            try:
                return int(data)
            except ValueError:
                raise forms.ValidationError("Please select a valid number of votes.")
        return data

    def save(self, campaign, commit=True):
        """Custom save method to handle vote creation"""
        # Get nominee or create if not exists
        nominee_number = self.cleaned_data['NOMINEE_NUMBER']
        couple_name = self.cleaned_data['COUPLE_NAME']
        
        # Try to find existing nominee
        nominee, created = Nominee.objects.get_or_create(
            campaign=campaign,
            number=nominee_number,
            defaults={
                'name': couple_name,
                'story': 'Nominated via voting form'
            }
        )
        
        # Create vote
        vote = Vote(
            nominee=nominee,
            voter_name=self.cleaned_data['VOTER_NAME'],
            voter_email=self.cleaned_data.get('VOTER_EMAIL', ''),  # Will be filled from payment
            voter_phone=self.cleaned_data['VOTER_PHONE'],
            vote_quantity=self.cleaned_data['NUMBER_OF_VOTES'],
            amount=self.cleaned_data['NUMBER_OF_VOTES'] * campaign.vote_price
        )
        
        if commit:
            vote.save()
        
        return vote
