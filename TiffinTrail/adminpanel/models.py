import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from chef.models import ChefProfile
from customer.models import Order


class Complaint(models.Model):
    CATEGORY_CHOICES = [
        ('food_quality', 'Food Quality & Taste'),
        ('delivery_delay', 'Delivery Delay'),
        ('packaging', 'Packaging & Spillage'),
        ('wrong_item', 'Wrong Item Delivered'),
        ('billing', 'Billing & Payment Issue'),
        ('hygiene', 'Hygiene & Cleanliness'),
        ('other', 'Other Support Inquiry'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low Priority'),
        ('medium', 'Medium Priority'),
        ('high', 'High Priority'),
        ('urgent', 'Urgent / Critical'),
    ]

    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('waiting_customer', 'Waiting for Customer'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]

    ticket_number = models.CharField(max_length=50, unique=True, editable=False)
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='complaints')
    chef = models.ForeignKey(ChefProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='complaints')
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name='complaints')
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='food_quality')
    subject = models.CharField(max_length=200)
    description = models.TextField()
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='open')
    assigned_admin = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_complaints')
    admin_notes = models.TextField(blank=True, help_text="Internal notes for administrators only (not visible to customer)")
    customer_response = models.TextField(blank=True, help_text="Customer-visible response message")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.ticket_number:
            ts = timezone.now().strftime('%Y%m%d')
            rand_code = uuid.uuid4().hex[:6].upper()
            self.ticket_number = f"TT-CMP-{ts}-{rand_code}"
        if self.status in ['resolved', 'closed'] and not self.resolved_at:
            self.resolved_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.ticket_number}: {self.subject} ({self.get_status_display()})"


class AdminNotification(models.Model):
    TYPE_CHOICES = [
        ('chef_reg', 'New Chef Registration'),
        ('verification', 'Chef Verification Pending'),
        ('complaint', 'Customer Support Complaint'),
        ('order', 'High Value / Urgent Order'),
        ('payment', 'Payment / Refund Action'),
        ('system', 'System Notice'),
    ]

    title = models.CharField(max_length=150)
    message = models.TextField()
    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES, default='system')
    link = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_notification_type_display()}] {self.title}"


class ChefVerificationLog(models.Model):
    ACTION_CHOICES = [
        ('approved', 'Application Approved'),
        ('rejected', 'Application Rejected'),
        ('under_review', 'Moved to Under Review'),
        ('info_requested', 'Additional Information Requested'),
        ('resubmission', 'Marked for Resubmission'),
    ]

    chef = models.ForeignKey(ChefProfile, on_delete=models.CASCADE, related_name='verification_logs')
    admin = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        admin_name = self.admin.username if self.admin else 'System'
        return f"{self.chef.business_name} - {self.get_action_display()} by {admin_name}"


class AdminActivityLog(models.Model):
    admin = models.ForeignKey(User, on_delete=models.CASCADE, related_name='admin_activities')
    action = models.CharField(max_length=100)
    target_model = models.CharField(max_length=50, blank=True)
    target_id = models.CharField(max_length=50, blank=True)
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.admin.username}: {self.action} on {self.target_model} #{self.target_id}"
