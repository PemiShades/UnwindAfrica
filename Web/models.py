from django.db import models
from django.utils.text import slugify
from django.utils.timezone import now
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
        return self.date < now().date()

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


# ===================== ANALYTICS SYSTEM =====================

class PageView(models.Model):
    """Track individual page views"""
    url = models.CharField(max_length=500)
    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField()
    referrer = models.CharField(max_length=500, blank=True)
    session_key = models.CharField(max_length=40)
    user = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['session_key']),
            models.Index(fields=['url']),
        ]

    def __str__(self):
        return f"{self.url} - {self.timestamp}"


class Session(models.Model):
    """Track user sessions"""
    session_key = models.CharField(max_length=40, unique=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    user = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL)
    start_time = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    page_views = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['session_key']),
            models.Index(fields=['start_time']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"Session {self.session_key} - {self.page_views} views"

    @property
    def duration(self):
        """Session duration in seconds"""
        return (self.last_activity - self.start_time).total_seconds()

    @property
    def is_bounce(self):
        """Bounce session = only 1 page view"""
        return self.page_views <= 1


# ===================== NOMINATE TO UNWIND - VOTING SYSTEM =====================

class VotingCampaign(models.Model):
    """Monthly campaign (e.g., Nominate to Unwind – November Edition)"""
    name = models.CharField(max_length=255, help_text="e.g., Nominate to Unwind – November 2025")
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True, help_text="Campaign details shown on voting page")
    tagline = models.CharField(max_length=255, blank=True, help_text="Short tagline for the campaign")
    
    # Campaign period
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    
    # Settings
    vote_price = models.DecimalField(max_digits=10, decimal_places=2, default=500.00, 
                                     help_text="Price per vote in Naira")
    rest_points_per_vote = models.DecimalField(max_digits=10, decimal_places=2, default=100.00,
                                               help_text="Rest points earned per vote")
    
    # Prizes
    grand_prize = models.CharField(max_length=255, blank=True, help_text="Grand prize description")
    grand_prize_description = models.TextField(blank=True, help_text="Detailed description of grand prize")
    second_prize = models.CharField(max_length=255, blank=True, help_text="Second prize description")
    second_prize_description = models.TextField(blank=True, help_text="Detailed description of second prize")
    third_prize = models.CharField(max_length=255, blank=True, help_text="Third prize description")
    third_prize_description = models.TextField(blank=True, help_text="Detailed description of third prize")
    prize_description = models.TextField(blank=True, help_text="Overall prizes description")
    
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
        current_now = now()
        return self.is_active and self.start_date <= current_now <= self.end_date
    
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
    number = models.CharField(max_length=50, blank=True, help_text="Nominee number on voting card")
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
    voter_email = models.EmailField(db_index=True)  # Added index for user lookups
    voter_phone = models.CharField(max_length=20)
    referral_source = models.CharField(max_length=255, blank=True, 
                                       help_text="Who told you about Unwind Africa?")
    
    # Payment information
    payment_status = models.CharField(
        max_length=20, 
        choices=[
            ('pending', 'Pending'),
            ('paid', 'Paid'),
            ('failed', 'Failed')
        ],
        default='pending'
    )
    
    # Vote details
    vote_quantity = models.PositiveIntegerField(default=1, help_text="Number of votes purchased")
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Total amount paid")
    rest_points_earned = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)  # Added index
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['nominee', 'created_at'], name='vote_nom_date_idx'),
            models.Index(fields=['payment_status'], name='vote_status_idx'),
        ]
    
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
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)  # Added index
    updated_at = models.DateTimeField(auto_now=True)
    
    # Raw response from Paystack (for debugging)
    paystack_response = models.JSONField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at'], name='trans_status_date_idx'),
        ]
    
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
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waitlist', db_index=True)  # Added index
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
        indexes = [
            models.Index(fields=['status', 'waitlist_joined_at'], name='restcard_status_date_idx'),
        ]
    
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
        
        # Check if status is being changed to active
        send_approval_email = False
        if self.pk:
            old_card = RestCard.objects.get(pk=self.pk)
            if old_card.status != 'active' and self.status == 'active':
                send_approval_email = True
        
        # Set waitlist position for new entries
        if not self.pk and self.status == 'waitlist' and not self.waitlist_position:
            max_position = RestCard.objects.filter(status='waitlist').aggregate(
                max_pos=models.Max('waitlist_position'))['max_pos']
            self.waitlist_position = (max_position or 0) + 1
        
        super().save(*args, **kwargs)
        
        # Send approval email if status was changed to active
        if send_approval_email:
            from django.core.mail import send_mail
            subject = "Your Rest Card has been approved!"
            body = (
                f"Dear {self.member_name},\n\n"
                f"Great news! Your Rest Card has been approved and activated.\n\n"
                f"Your card details:\n"
                f"Card Number: {self.card_number}\n"
                f"Status: Active\n\n"
                f"You can now access exclusive benefits, rewards, and experiences through your Rest Card.\n\n"
                f"Log in to your account to view your card and start exploring.\n\n"
                f"Best regards,\n"
                f"The Unwind Africa Team\n"
                f"Phone: +234 806 206 7832\n"
                f"Email: info@unwindafrica.com"
            )
            try:
                send_mail(subject, body, "no-reply@unwindafrica.com", [self.member_email], fail_silently=True)
            except Exception as e:
                print(f"Error sending approval email to {self.member_email}: {e}")


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


class Book(models.Model):
    """Book model for Raising Readers initiative"""
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('on_loan', 'On Loan'),
        ('high_demand', 'High Demand'),
        ('unavailable', 'Unavailable'),
    ]
    
    AGE_CATEGORY_CHOICES = [
        ('0-3', '0-3 years'),
        ('4-6', '4-6 years'),
        ('7-10', '7-10 years'),
        ('11-14', '11-14 years'),
        ('15+', '15+ years'),
        ('adult', 'Adult'),
    ]
    
    GENRE_CHOICES = [
        ('fiction', 'Fiction'),
        ('non-fiction', 'Non-Fiction'),
        ('mystery', 'Mystery'),
        ('adventure', 'Adventure'),
        ('fantasy', 'Fantasy'),
        ('science-fiction', 'Science Fiction'),
        ('biography', 'Biography'),
        ('history', 'History'),
        ('science', 'Science'),
        ('art', 'Art'),
        ('poetry', 'Poetry'),
        ('other', 'Other'),
    ]
    
    # Book details
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    cover_image = models.ImageField(upload_to='books/covers/', blank=True, null=True)
    description = models.TextField(blank=True)
    age_category = models.CharField(max_length=20, choices=AGE_CATEGORY_CHOICES)
    genre = models.CharField(max_length=50, choices=GENRE_CHOICES)
    
    # Availability
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    isbn = models.CharField(max_length=20, blank=True, help_text="ISBN number (optional)")
    
    # Tracking
    times_borrowed = models.PositiveIntegerField(default=0)
    current_borrower = models.ForeignKey(RestCard, on_delete=models.SET_NULL, null=True, blank=True, related_name='borrowed_books')
    borrow_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['title']
    
    def __str__(self):
        return f"{self.title} by {self.author}"
    
    @property
    def is_available(self):
        """Check if book is available for borrowing"""
        return self.status == 'available'
    
    @property
    def is_on_loan(self):
        """Check if book is currently on loan"""
        return self.status == 'on_loan'
    
    @property
    def is_high_demand(self):
        """Check if book is in high demand"""
        return self.status == 'high_demand'


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


class FrozenRestPoints(models.Model):
    """
    Stores rest points earned from voting that are "frozen" until the user
    applies for and receives a Rest Card.
    """
    member_email = models.EmailField(db_index=True)  # Added index
    member_name = models.CharField(max_length=255, blank=True)
    member_phone = models.CharField(max_length=20, blank=True)
    
    # Frozen points earned from voting
    frozen_points = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Link to Rest Card (when user applies and gets a card)
    rest_card = models.ForeignKey('RestCard', on_delete=models.SET_NULL, null=True, blank=True, related_name='frozen_points_transfers')
    points_claimed = models.BooleanField(default=False, db_index=True)  # Added index
    claimed_at = models.DateTimeField(null=True, blank=True)
    
    # Vote references
    vote = models.ForeignKey('Vote', on_delete=models.SET_NULL, null=True, blank=True, related_name='frozen_points_entry')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)  # Added index
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Frozen Rest Points'
        verbose_name_plural = 'Frozen Rest Points'
        indexes = [
            models.Index(fields=['member_email', 'points_claimed'], name='frozen_email_claimed_idx'),
        ]
    
    def __str__(self):
        return f"Frozen Points - {self.member_email}: {self.frozen_points}"


class EdBritishTrialRegistration(models.Model):
    """Trial class registrations for EdBritish Consult partnership"""
    
    # Parent/Guardian Information
    parent_name = models.CharField(max_length=200)
    parent_email = models.EmailField()
    parent_phone = models.CharField(max_length=50)
    country = models.CharField(max_length=100)
    
    # Child Information
    child_name = models.CharField(max_length=200)
    child_age = models.IntegerField()
    subject = models.CharField(max_length=50)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.child_name} - {self.subject} - {self.parent_email}"

