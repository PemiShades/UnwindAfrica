# dashboard/admin.py
from django.contrib import admin
from .models import Post, Event  # proxies to Web.models
from Web.models import Book
from Web.models import (
    GroupGetawayPackage,
    PackageAddOn,
    PackageOrder,
    PackageInstalment,
    PackagePayment,
    GroupGetawayEarlyAccessOffer,
)


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "is_published", "is_featured", "created_at")
    list_filter = ("is_published", "is_featured", "created_at", "category")
    search_fields = ("title", "excerpt", "content", "slug")
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("-created_at",)


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("name", "date", "location", "badge", "created_at")
    list_filter = ("date", "badge", "created_at",)
    search_fields = ("name", "location", "description", "slug")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("date", "-created_at")


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "status", "age_category", "genre", "times_borrowed", "created_at")
    list_filter = ("status", "age_category", "genre", "created_at")
    search_fields = ("title", "author", "description", "isbn")
    ordering = ("-created_at",)
    readonly_fields = ("times_borrowed", "created_at", "updated_at")


@admin.register(GroupGetawayPackage)
class GroupGetawayPackageAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "experience_duration", "pricing_basis", "price_per_person", "is_active", "created_at")
    list_filter = ("category", "experience_duration", "is_active", "created_at")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("price_per_person",)
    list_editable = ("price_per_person", "is_active")


@admin.register(PackageAddOn)
class PackageAddOnAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "regular_price", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name",)
    list_editable = ("price", "regular_price", "is_active")


@admin.register(PackageOrder)
class PackageOrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer_email", "package", "grand_total", "amount_paid", "outstanding_balance", "early_access_slot", "early_access_discount", "duration_months", "status", "created_at")
    list_filter = ("status", "package__category", "early_access_confirmed_at", "created_at")
    search_fields = ("customer_email", "customer_name", "package__name")
    ordering = ("-created_at",)
    readonly_fields = ("rest_forward_balance", "amount_paid", "outstanding_balance", "early_access_slot", "early_access_discount", "early_access_confirmed_at")


@admin.register(PackageInstalment)
class PackageInstalmentAdmin(admin.ModelAdmin):
    list_display = ("order", "month_number", "due_date", "total_due", "amount_paid", "status")
    list_filter = ("status",)
    search_fields = ("order__customer_email",)
    ordering = ("order", "month_number")


@admin.register(PackagePayment)
class PackagePaymentAdmin(admin.ModelAdmin):
    list_display = ("order", "amount", "status", "is_initial_deposit", "paid_at", "reference")
    list_filter = ("status", "is_initial_deposit", "paid_at")
    search_fields = ("order__customer_email", "reference", "paystack_reference")
    ordering = ("-paid_at",)


@admin.register(GroupGetawayEarlyAccessOffer)
class GroupGetawayEarlyAccessOfferAdmin(admin.ModelAdmin):
    list_display = ("name", "capacity", "confirmed_count")
    readonly_fields = ("confirmed_count",)
