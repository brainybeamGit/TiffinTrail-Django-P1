from django.contrib import admin
from .models import (
    CustomerProfile, DeliveryAddress, Coupon,
    Cart, CartItem, Order, OrderItem,
    Subscription, Review, PasswordResetOTP
)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'created_at')
    search_fields = ('user__username', 'user__email', 'phone')


@admin.register(DeliveryAddress)
class DeliveryAddressAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'recipient_name', 'phone_number', 'city', 'pincode', 'is_default')
    list_filter = ('is_default', 'city')
    search_fields = ('recipient_name', 'street_address', 'area', 'pincode', 'user__username')


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_type', 'discount_value', 'min_order_amount', 'is_active', 'valid_until')
    list_filter = ('is_active', 'discount_type')
    search_fields = ('code',)


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'session_key', 'items_count', 'subtotal', 'final_total', 'updated_at')
    inlines = [CartItemInline]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'user', 'chef', 'status', 'final_amount', 'payment_method', 'payment_status', 'created_at')
    list_filter = ('status', 'payment_method', 'payment_status', 'created_at')
    search_fields = ('order_number', 'user__username', 'recipient_name', 'recipient_phone')
    inlines = [OrderItemInline]


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('subscription_number', 'user', 'chef', 'plan', 'start_date', 'end_date', 'status', 'delivery_slot', 'payment_status')
    list_filter = ('status', 'delivery_slot', 'dietary_preference', 'payment_status')
    search_fields = ('subscription_number', 'user__username', 'recipient_name')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'chef', 'order', 'meal', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('user__username', 'chef__business_name', 'order__order_number', 'comment')


@admin.register(PasswordResetOTP)
class PasswordResetOTPAdmin(admin.ModelAdmin):
    list_display = ('email', 'user', 'otp', 'user_type', 'is_used', 'expires_at', 'created_at')
    list_filter = ('user_type', 'is_used', 'created_at')
    search_fields = ('email', 'user__username', 'otp')
    readonly_fields = ('created_at',)
