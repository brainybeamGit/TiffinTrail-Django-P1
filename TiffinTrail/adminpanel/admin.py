from django.contrib import admin
from .models import Complaint, AdminNotification, ChefVerificationLog, AdminActivityLog


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ('ticket_number', 'customer', 'chef', 'category', 'priority', 'status', 'created_at')
    list_filter = ('status', 'priority', 'category')
    search_fields = ('ticket_number', 'subject', 'customer__username', 'chef__business_name')


@admin.register(AdminNotification)
class AdminNotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read')
    search_fields = ('title', 'message')


@admin.register(ChefVerificationLog)
class ChefVerificationLogAdmin(admin.ModelAdmin):
    list_display = ('chef', 'admin', 'action', 'created_at')
    list_filter = ('action',)
    search_fields = ('chef__business_name', 'admin__username')


@admin.register(AdminActivityLog)
class AdminActivityLogAdmin(admin.ModelAdmin):
    list_display = ('admin', 'action', 'target_model', 'target_id', 'created_at')
    search_fields = ('admin__username', 'action', 'target_id')
