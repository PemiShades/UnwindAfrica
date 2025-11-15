from django.db import models
from django.utils.text import slugify
from django.utils import timezone
from django.urls import reverse
import re


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


# ===================== NOMINATE TO UNWIND - VOTING SYSTEM =====================

class VotingCampaign(models.Model):
    """Monthly campaign (e.g., Nominate to Unwind – November Edition)"""
    name = models.CharField(max_length=255, help_text="e.g., Nominate to Unwind – November 2025")
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True, help_text="Campaign details shown on voting page")
    
    # Campaign period
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    
    # Settings
    vote_price = models.DecimalField(max_digits=10, decimal_places=2, default=500.00, 
                                     help_text="Price per vote in Naira")
    rest_points_per_vote = models.DecimalField(max_digits=10, decimal_places=2, default=100.00,
                                               help_text="Rest points earned per vote")
    
    # Visuals
    banner_image = models.ImageField(upload_to='campaigns/banners/', blank=True, null=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-start_date']
    
    def __str__(self):
        return self.name
    
    @property
    def is_ongoing(self):
        now = timezone.now()
        return self.is_active and self.start_date <= now <= self.end_date
    
    @property
    def total_votes(self):
        return sum(nominee.vote_count for nominee in self.nominees.all())
    
    @property
    def total_revenue(self):
        return Vote.objects.filter(
            nominee__campaign=self, 
            transaction__status='success'
        ).aggregate(total=models.Sum('amount'))['total'] or 0
    
    def get_absolute_url(self):
        return reverse("voting_campaign", kwargs={"slug": self.slug})
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)
            slug = base
            i = 2
            while VotingCampaign.objects.filter(slug=slug).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)


class Nominee(models.Model):
    """Person nominated for a campaign"""
    campaign = models.ForeignKey(VotingCampaign, on_delete=models.CASCADE, related_name='nominees')
    
    # Nominee details
    name = models.CharField(max_length=255)
    photo = models.ImageField(upload_to='nominees/photos/')
    story = models.TextField(help_text="Short story about why they deserve to unwind")
    instagram_handle = models.CharField(max_length=100, blank=True, help_text="Without @ symbol")
    
    # Vote tracking
    vote_count = models.PositiveIntegerField(default=0)
    
    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    order = models.PositiveIntegerField(default=0, help_text="Display order on voting page")
    
    class Meta:
        ordering = ['campaign', 'order', '-vote_count']
        unique_together = ['campaign', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.campaign.name})"
    
    @property
    def total_amount_raised(self):
        """Total money raised for this nominee"""
        return Vote.objects.filter(
            nominee=self,
            transaction__status='success'
        ).aggregate(total=models.Sum('amount'))['total'] or 0
    
    @property
    def instagram_url(self):
        if self.instagram_handle:
            handle = self.instagram_handle.lstrip('@')
            return f"https://instagram.com/{handle}"
        return None


class Vote(models.Model):
    """Individual vote purchase"""
    nominee = models.ForeignKey(Nominee, on_delete=models.CASCADE, related_name='votes')
    
    # Voter details
    voter_name = models.CharField(max_length=255)
    voter_email = models.EmailField()
    voter_phone = models.CharField(max_length=20)
    referral_source = models.CharField(max_length=255, blank=True, 
                                       help_text="Who told you about Unwind Africa?")
    
    # Vote details
    vote_quantity = models.PositiveIntegerField(default=1, help_text="Number of votes purchased")
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Total amount paid")
    rest_points_earned = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.vote_quantity} vote(s) for {self.nominee.name} by {self.voter_name}"
    
    def save(self, *args, **kwargs):
        # Auto-calculate rest points
        if not self.rest_points_earned:
            self.rest_points_earned = (self.vote_quantity * 
                                       self.nominee.campaign.rest_points_per_vote)
        super().save(*args, **kwargs)


class Transaction(models.Model):
    """Payment transaction record"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]
    
    vote = models.OneToOneField(Vote, on_delete=models.CASCADE, related_name='transaction')
    
    # Paystack details
    reference = models.CharField(max_length=100, db_index=True,
                                 help_text="Payment reference - multiple votes can share same payment")
    paystack_reference = models.CharField(max_length=100, blank=True)
    authorization_url = models.URLField(blank=True)
    access_code = models.CharField(max_length=100, blank=True)
    
    # Transaction info
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Metadata
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Raw response from Paystack (for debugging)
    paystack_response = models.JSONField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Transaction {self.reference} - {self.status}"


# ===================== COMMUNITY & REST CARD SYSTEM =====================

class CommunityMember(models.Model):
    """Tracks community members from Google Form integration"""
    # Basic Info
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    
    # Demographics
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('non_binary', 'Non-Binary'),
        ('prefer_not_to_say', 'Prefer Not to Say'),
    ]
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, blank=True)
    location = models.CharField(max_length=255, blank=True, help_text="City or Country")
    
    # Engagement
    referral_source = models.CharField(max_length=255, blank=True)
    interests = models.TextField(blank=True, help_text="Comma-separated interests")
    
    # Google Form sync
    google_form_timestamp = models.DateTimeField(null=True, blank=True)
    google_sheet_row_id = models.IntegerField(null=True, blank=True, unique=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.email})"


class RestCard(models.Model):
    """Rest Card - Membership card for exclusive benefits"""
    STATUS_CHOICES = [
        ('waitlist', 'Waitlist'),
        ('pending', 'Pending Activation'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('expired', 'Expired'),
    ]
    
    # Member details
    member_email = models.EmailField(unique=True)
    member_name = models.CharField(max_length=255)
    member_phone = models.CharField(max_length=20)
    
    # Card details
    card_number = models.CharField(max_length=16, unique=True, blank=True, null=True,
                                   help_text="Auto-generated unique card number")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waitlist')
    waitlist_position = models.PositiveIntegerField(null=True, blank=True)
    
    # Benefits tracking
    total_rest_points = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                           help_text="Total rest points accumulated")
    
    # Timestamps
    waitlist_joined_at = models.DateTimeField(auto_now_add=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['waitlist_position', '-waitlist_joined_at']
    
    def __str__(self):
        return f"Rest Card - {self.member_name} ({self.status})"
    
    def save(self, *args, **kwargs):
        # Auto-generate card number if not exists
        if not self.card_number and self.status != 'waitlist':
            import random
            while True:
                card_num = ''.join([str(random.randint(0, 9)) for _ in range(16)])
                if not RestCard.objects.filter(card_number=card_num).exists():
                    self.card_number = card_num
                    break
        
        # Set waitlist position for new entries
        if not self.pk and self.status == 'waitlist' and not self.waitlist_position:
            max_position = RestCard.objects.filter(status='waitlist').aggregate(
                max_pos=models.Max('waitlist_position'))['max_pos']
            self.waitlist_position = (max_position or 0) + 1
        
        super().save(*args, **kwargs)


class TokenWallet(models.Model):
    """Token wallet for reward system"""
    # Link to member
    member_email = models.EmailField(unique=True)
    member_name = models.CharField(max_length=255)
    
    # Token tracking
    tokens_earned = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                       help_text="Total tokens earned from all activities")
    tokens_used = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                     help_text="Total tokens spent/redeemed")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-tokens_earned']
    
    def __str__(self):
        return f"Wallet - {self.member_name} ({self.available_tokens} available)"
    
    @property
    def available_tokens(self):
        """Calculate available tokens"""
        return self.tokens_earned - self.tokens_used


class TokenTransaction(models.Model):
    """Record of token earning/spending"""
    TRANSACTION_TYPE_CHOICES = [
        ('earn', 'Earned'),
        ('spend', 'Spent'),
        ('bonus', 'Bonus'),
        ('refund', 'Refund'),
    ]
    
    wallet = models.ForeignKey(TokenWallet, on_delete=models.CASCADE, related_name='transactions')
    
    # Transaction details
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(help_text="e.g., Voted for November Campaign, Redeemed for discount")
    
    # Reference (optional)
    reference_id = models.CharField(max_length=100, blank=True, 
                                   help_text="Related vote/transaction ID")
    
    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.transaction_type} - {self.amount} tokens - {self.wallet.member_name}"

