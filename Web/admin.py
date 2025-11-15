from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum
from django.http import HttpResponse
import csv
from .models import (Event, Post, BlogCategory, VotingCampaign, Nominee, Vote, Transaction,
                     CommunityMember, RestCard, TokenWallet, TokenTransaction)


# ============= Existing Models =============
admin.site.register(Event)
admin.site.register(Post)
admin.site.register(BlogCategory)


# ============= Voting System Admin =============

class NomineeInline(admin.TabularInline):
    model = Nominee
    extra = 1
    fields = ('name', 'photo', 'story', 'instagram_handle', 'vote_count', 'order')
    readonly_fields = ('vote_count',)


@admin.register(VotingCampaign)
class VotingCampaignAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date', 'is_active', 'is_ongoing', 
                    'total_votes', 'total_revenue_display')
    list_filter = ('is_active', 'start_date')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [NomineeInline]
    readonly_fields = ('created_at', 'updated_at', 'total_votes', 'total_revenue_display')
    
    fieldsets = (
        ('Campaign Info', {
            'fields': ('name', 'slug', 'description', 'banner_image')
        }),
        ('Schedule', {
            'fields': ('start_date', 'end_date', 'is_active')
        }),
        ('Pricing', {
            'fields': ('vote_price', 'rest_points_per_vote')
        }),
        ('Statistics', {
            'fields': ('total_votes', 'total_revenue_display', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def total_revenue_display(self, obj):
        return f"₦{obj.total_revenue:,.2f}"
    total_revenue_display.short_description = 'Total Revenue'
    
    actions = ['export_campaign_report']
    
    def export_campaign_report(self, request, queryset):
        """Export campaign votes and transactions as CSV"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="voting_campaign_report.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Campaign', 'Nominee', 'Voter Name', 'Voter Email', 'Voter Phone',
            'Votes', 'Amount Paid', 'Rest Points', 'Payment Status', 'Date', 'Referral Source'
        ])
        
        for campaign in queryset:
            for vote in Vote.objects.filter(nominee__campaign=campaign).select_related(
                'nominee', 'transaction'
            ):
                writer.writerow([
                    campaign.name,
                    vote.nominee.name,
                    vote.voter_name,
                    vote.voter_email,
                    vote.voter_phone,
                    vote.vote_quantity,
                    vote.amount,
                    vote.rest_points_earned,
                    vote.transaction.status if hasattr(vote, 'transaction') else 'N/A',
                    vote.created_at.strftime('%Y-%m-%d %H:%M'),
                    vote.referral_source or 'N/A'
                ])
        
        return response
    export_campaign_report.short_description = 'Export Campaign Report (CSV)'


@admin.register(Nominee)
class NomineeAdmin(admin.ModelAdmin):
    list_display = ('name', 'campaign', 'vote_count', 'total_amount_raised_display', 
                    'instagram_link', 'order')
    list_filter = ('campaign',)
    search_fields = ('name', 'story', 'instagram_handle')
    list_editable = ('order',)
    readonly_fields = ('vote_count', 'created_at', 'total_amount_raised_display')
    
    fieldsets = (
        ('Nominee Info', {
            'fields': ('campaign', 'name', 'photo', 'story', 'instagram_handle')
        }),
        ('Display Settings', {
            'fields': ('order',)
        }),
        ('Statistics', {
            'fields': ('vote_count', 'total_amount_raised_display', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def total_amount_raised_display(self, obj):
        return f"₦{obj.total_amount_raised:,.2f}"
    total_amount_raised_display.short_description = 'Total Raised'
    
    def instagram_link(self, obj):
        if obj.instagram_url:
            return format_html('<a href="{}" target="_blank">@{}</a>', 
                             obj.instagram_url, obj.instagram_handle)
        return '-'
    instagram_link.short_description = 'Instagram'


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ('voter_name', 'nominee', 'vote_quantity', 'amount_display', 
                    'rest_points_earned', 'payment_status', 'created_at')
    list_filter = ('nominee__campaign', 'created_at', 'transaction__status')
    search_fields = ('voter_name', 'voter_email', 'voter_phone', 'nominee__name')
    readonly_fields = ('rest_points_earned', 'created_at')
    
    fieldsets = (
        ('Vote Details', {
            'fields': ('nominee', 'vote_quantity', 'amount', 'rest_points_earned')
        }),
        ('Voter Information', {
            'fields': ('voter_name', 'voter_email', 'voter_phone', 'referral_source')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def amount_display(self, obj):
        return f"₦{obj.amount:,.2f}"
    amount_display.short_description = 'Amount'
    
    def payment_status(self, obj):
        if hasattr(obj, 'transaction'):
            status = obj.transaction.status
            colors = {'success': 'green', 'pending': 'orange', 'failed': 'red'}
            return format_html(
                '<span style="color: {};">{}</span>',
                colors.get(status, 'black'),
                status.upper()
            )
        return format_html('<span style="color: gray;">NO TRANSACTION</span>')
    payment_status.short_description = 'Payment Status'
    
    actions = ['export_votes_csv']
    
    def export_votes_csv(self, request, queryset):
        """Export selected votes as CSV"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="votes_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Nominee', 'Campaign', 'Voter Name', 'Email', 'Phone',
            'Votes', 'Amount', 'Rest Points', 'Payment Status', 'Date'
        ])
        
        for vote in queryset.select_related('nominee', 'nominee__campaign', 'transaction'):
            writer.writerow([
                vote.nominee.name,
                vote.nominee.campaign.name,
                vote.voter_name,
                vote.voter_email,
                vote.voter_phone,
                vote.vote_quantity,
                vote.amount,
                vote.rest_points_earned,
                vote.transaction.status if hasattr(vote, 'transaction') else 'N/A',
                vote.created_at.strftime('%Y-%m-%d %H:%M')
            ])
        
        return response
    export_votes_csv.short_description = 'Export Selected Votes (CSV)'


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('reference', 'vote_nominee', 'amount_display', 'status', 
                    'paid_at', 'created_at')
    list_filter = ('status', 'created_at', 'paid_at')
    search_fields = ('reference', 'paystack_reference', 'vote__voter_name', 'vote__voter_email')
    readonly_fields = ('created_at', 'updated_at', 'paystack_response_display')
    
    fieldsets = (
        ('Transaction Info', {
            'fields': ('vote', 'reference', 'amount', 'status')
        }),
        ('Paystack Details', {
            'fields': ('paystack_reference', 'authorization_url', 'access_code')
        }),
        ('Timestamps', {
            'fields': ('paid_at', 'created_at', 'updated_at')
        }),
        ('Debug Info', {
            'fields': ('paystack_response_display',),
            'classes': ('collapse',)
        }),
    )
    
    def vote_nominee(self, obj):
        return obj.vote.nominee.name
    vote_nominee.short_description = 'Nominee'
    
    def amount_display(self, obj):
        return f"₦{obj.amount:,.2f}"
    amount_display.short_description = 'Amount'
    
    def paystack_response_display(self, obj):
        if obj.paystack_response:
            import json
            return format_html('<pre>{}</pre>', json.dumps(obj.paystack_response, indent=2))
        return 'No response data'
    paystack_response_display.short_description = 'Paystack Response'


# ============= Community & Rest Card Admin =============

@admin.register(CommunityMember)
class CommunityMemberAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'gender', 'location', 'created_at')
    list_filter = ('gender', 'location', 'created_at')
    search_fields = ('name', 'email', 'phone', 'location')
    readonly_fields = ('created_at', 'updated_at', 'google_form_timestamp')
    
    fieldsets = (
        ('Member Info', {
            'fields': ('name', 'email', 'phone')
        }),
        ('Demographics', {
            'fields': ('gender', 'location', 'interests')
        }),
        ('Engagement', {
            'fields': ('referral_source',)
        }),
        ('Google Form Sync', {
            'fields': ('google_form_timestamp', 'google_sheet_row_id'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['export_members_csv']
    
    def export_members_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="community_members.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Name', 'Email', 'Phone', 'Gender', 'Location', 'Interests', 'Joined Date'])
        
        for member in queryset:
            writer.writerow([
                member.name, member.email, member.phone, member.gender,
                member.location, member.interests, member.created_at.strftime('%Y-%m-%d')
            ])
        
        return response
    export_members_csv.short_description = 'Export Selected Members (CSV)'


@admin.register(RestCard)
class RestCardAdmin(admin.ModelAdmin):
    list_display = ('member_name', 'card_number_display', 'status', 'waitlist_position',
                    'total_rest_points', 'waitlist_joined_at')
    list_filter = ('status', 'waitlist_joined_at')
    search_fields = ('member_name', 'member_email', 'member_phone', 'card_number')
    readonly_fields = ('waitlist_joined_at', 'card_number_display')
    list_editable = ('status',)
    
    fieldsets = (
        ('Member Info', {
            'fields': ('member_name', 'member_email', 'member_phone')
        }),
        ('Card Details', {
            'fields': ('card_number_display', 'status', 'waitlist_position')
        }),
        ('Benefits', {
            'fields': ('total_rest_points',)
        }),
        ('Timestamps', {
            'fields': ('waitlist_joined_at', 'activated_at', 'expires_at'),
            'classes': ('collapse',)
        }),
    )
    
    def card_number_display(self, obj):
        if obj.card_number:
            # Format as XXXX-XXXX-XXXX-XXXX
            formatted = '-'.join([obj.card_number[i:i+4] for i in range(0, 16, 4)])
            return formatted
        return 'Not yet assigned'
    card_number_display.short_description = 'Card Number'
    
    actions = ['activate_cards', 'export_waitlist']
    
    def activate_cards(self, request, queryset):
        """Activate selected waitlist cards"""
        from django.utils import timezone
        count = 0
        for card in queryset.filter(status='waitlist'):
            card.status = 'pending'
            card.activated_at = timezone.now()
            card.save()
            count += 1
        self.message_user(request, f'{count} cards moved to pending activation')
    activate_cards.short_description = 'Activate Selected Cards'
    
    def export_waitlist(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="rest_card_waitlist.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Position', 'Name', 'Email', 'Phone', 'Status', 'Joined Date', 'Rest Points'])
        
        for card in queryset.order_by('waitlist_position'):
            writer.writerow([
                card.waitlist_position or 'N/A', card.member_name, card.member_email,
                card.member_phone, card.status, card.waitlist_joined_at.strftime('%Y-%m-%d'),
                card.total_rest_points
            ])
        
        return response
    export_waitlist.short_description = 'Export Waitlist (CSV)'


class TokenTransactionInline(admin.TabularInline):
    model = TokenTransaction
    extra = 0
    fields = ('transaction_type', 'amount', 'description', 'created_at')
    readonly_fields = ('created_at',)
    can_delete = False


@admin.register(TokenWallet)
class TokenWalletAdmin(admin.ModelAdmin):
    list_display = ('member_name', 'member_email', 'tokens_earned', 'tokens_used',
                    'available_tokens_display', 'created_at')
    search_fields = ('member_name', 'member_email')
    readonly_fields = ('created_at', 'updated_at', 'available_tokens_display')
    inlines = [TokenTransactionInline]
    
    fieldsets = (
        ('Member Info', {
            'fields': ('member_name', 'member_email')
        }),
        ('Token Balance', {
            'fields': ('tokens_earned', 'tokens_used', 'available_tokens_display')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def available_tokens_display(self, obj):
        return f"{obj.available_tokens:,.2f}"
    available_tokens_display.short_description = 'Available Tokens'
    
    actions = ['export_wallets']
    
    def export_wallets(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="token_wallets.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Name', 'Email', 'Tokens Earned', 'Tokens Used', 'Available Tokens'])
        
        for wallet in queryset:
            writer.writerow([
                wallet.member_name, wallet.member_email, wallet.tokens_earned,
                wallet.tokens_used, wallet.available_tokens
            ])
        
        return response
    export_wallets.short_description = 'Export Wallets (CSV)'


@admin.register(TokenTransaction)
class TokenTransactionAdmin(admin.ModelAdmin):
    list_display = ('wallet_member', 'transaction_type', 'amount', 'description_short',
                    'created_at')
    list_filter = ('transaction_type', 'created_at')
    search_fields = ('wallet__member_name', 'wallet__member_email', 'description', 'reference_id')
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Transaction Info', {
            'fields': ('wallet', 'transaction_type', 'amount')
        }),
        ('Details', {
            'fields': ('description', 'reference_id')
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        }),
    )
    
    def wallet_member(self, obj):
        return obj.wallet.member_name
    wallet_member.short_description = 'Member'
    
    def description_short(self, obj):
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
    description_short.short_description = 'Description'
