import uuid
from decimal import Decimal
from django.db import models
from django.db.models import Q, F
from django.contrib.auth.models import User
from django.utils import timezone
from chef.models import ChefProfile, Meal, MealPlan


class CustomerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
    phone = models.CharField(max_length=20, blank=True)
    profile_image = models.FileField(upload_to='customers/', blank=True, null=True)
    bio = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.user.email})"


class DeliveryAddress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    title = models.CharField(max_length=50, default='Home', help_text="e.g. Home, Office, Other")
    recipient_name = models.CharField(max_length=120)
    phone_number = models.CharField(max_length=20)
    street_address = models.CharField(max_length=255)
    area = models.CharField(max_length=120, help_text="Locality / Landmark")
    city = models.CharField(max_length=80, default="Bengaluru")
    pincode = models.CharField(max_length=10)
    delivery_notes = models.TextField(blank=True, help_text="Gate instructions, flat number, etc.")
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Delivery Addresses'
        ordering = ['-is_default', '-created_at']

    def save(self, *args, **kwargs):
        if self.is_default:
            DeliveryAddress.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(is_default=False)
        elif not DeliveryAddress.objects.filter(user=self.user).exclude(pk=self.pk).exists():
            self.is_default = True
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title}: {self.recipient_name}, {self.street_address}, {self.area}, {self.city} - {self.pincode}"

    @property
    def formatted(self):
        return f"{self.street_address}, {self.area}, {self.city} - {self.pincode}"


class Coupon(models.Model):
    COUPON_TYPES = [
        ('fixed', 'Flat Discount (₹)'),
        ('percent', 'Percentage (%)'),
    ]

    code = models.CharField(max_length=30, unique=True)
    description = models.CharField(max_length=200, blank=True)
    discount_type = models.CharField(max_length=10, choices=COUPON_TYPES, default='percent')
    discount_value = models.DecimalField(max_digits=6, decimal_places=2)
    min_order_amount = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('200.00'))
    max_discount_amount = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    usage_limit = models.PositiveIntegerField(default=100, help_text="Total maximum redemptions")
    times_used = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    valid_until = models.DateTimeField(null=True, blank=True)

    @property
    def is_currently_valid(self):
        """Checks if coupon is active, not expired, and not exhausted."""
        if not self.is_active:
            return False
        if self.valid_until:
            valid_dt = self.valid_until
            if timezone.is_naive(valid_dt):
                valid_dt = timezone.make_aware(valid_dt)
            if timezone.now() > valid_dt:
                return False
        if self.usage_limit and self.times_used >= self.usage_limit:
            return False
        return True

    @classmethod
    def get_available_coupons(cls):
        """Returns all coupons that are active, unexpired, and within usage limits."""
        now = timezone.now()
        return cls.objects.filter(
            is_active=True
        ).filter(
            Q(valid_until__isnull=True) | Q(valid_until__gt=now)
        ).filter(
            Q(usage_limit=0) | Q(usage_limit__isnull=True) | Q(times_used__lt=F('usage_limit'))
        ).order_by('-discount_value', 'code')

    def is_valid_for(self, amount):
        if not self.is_active:
            return False, "This coupon is inactive."
        if self.valid_until:
            valid_dt = self.valid_until
            if timezone.is_naive(valid_dt):
                valid_dt = timezone.make_aware(valid_dt)
            if timezone.now() > valid_dt:
                return False, "This coupon has expired."
        if self.usage_limit and self.times_used >= self.usage_limit:
            return False, "This coupon has reached its maximum usage limit."
        if amount < self.min_order_amount:
            return False, f"Minimum order amount of ₹{self.min_order_amount} required."
        return True, "Coupon applied successfully!"

    def calculate_discount(self, amount):
        valid, _ = self.is_valid_for(amount)
        if not valid:
            return Decimal('0.00')
        if self.discount_type == 'percent':
            disc = (amount * self.discount_value) / Decimal('100.00')
            if self.max_discount_amount and disc > self.max_discount_amount:
                disc = self.max_discount_amount
            return round(disc, 2)
        else:
            return min(self.discount_value, amount)

    def __str__(self):
        return f"{self.code} ({self.discount_value}{'%' if self.discount_type == 'percent' else '₹'} off)"


class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='carts')
    session_key = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def items_count(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def subtotal(self):
        total = sum(item.subtotal for item in self.items.select_related('meal'))
        return Decimal(str(total)) if total else Decimal('0.00')

    @property
    def delivery_fee(self):
        sub = self.subtotal
        if sub == Decimal('0.00'):
            return Decimal('0.00')
        # Free delivery over ₹350
        return Decimal('0.00') if sub >= Decimal('350.00') else Decimal('35.00')

    @property
    def tax_amount(self):
        # 5% GST on food
        return round((self.subtotal * Decimal('0.05')), 2)

    @property
    def discount_amount(self):
        if self.coupon:
            return self.coupon.calculate_discount(self.subtotal)
        return Decimal('0.00')

    @property
    def final_total(self):
        if self.subtotal == Decimal('0.00'):
            return Decimal('0.00')
        total = self.subtotal + self.delivery_fee + self.tax_amount - self.discount_amount
        return max(Decimal('0.00'), round(total, 2))

    def get_chef(self):
        first_item = self.items.select_related('meal__chef').first()
        return first_item.meal.chef if first_item else None

    def __str__(self):
        owner = self.user.username if self.user else f"Guest ({self.session_key})"
        return f"Cart #{self.id} for {owner}"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    meal = models.ForeignKey(Meal, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    special_instructions = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('cart', 'meal')

    @property
    def subtotal(self):
        return self.meal.price * self.quantity

    def __str__(self):
        return f"{self.quantity}x {self.meal.name}"


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Order Received'),
        ('confirmed', 'Confirmed by Chef'),
        ('preparing', 'Cooking in Progress'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    PAYMENT_METHODS = [
        ('cod', 'Cash on Delivery'),
        ('online', 'Online Payment (UPI/Cards/NetBanking)'),
    ]

    PAYMENT_STATUSES = [
        ('pending', 'Payment Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    order_number = models.CharField(max_length=50, unique=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    chef = models.ForeignKey(ChefProfile, on_delete=models.CASCADE, related_name='orders')
    recipient_name = models.CharField(max_length=120)
    recipient_phone = models.CharField(max_length=20)
    delivery_address_text = models.TextField()
    delivery_notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Meals subtotal")
    delivery_fee = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    tax_amount = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    discount_amount = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    final_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='online')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUSES, default='pending')
    payment_transaction_id = models.CharField(max_length=100, blank=True)
    cancellation_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.order_number:
            ts = timezone.now().strftime('%Y%m%d%H%M')
            unique_part = str(uuid.uuid4().hex[:6]).upper()
            self.order_number = f"TT-ORD-{ts}-{unique_part}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.order_number} ({self.get_status_display()})"

    @property
    def can_cancel(self):
        return self.status in ['pending', 'confirmed']

    @property
    def progress_step(self):
        mapping = {
            'pending': 1,
            'confirmed': 2,
            'preparing': 3,
            'out_for_delivery': 4,
            'delivered': 5,
            'cancelled': 0,
        }
        return mapping.get(self.status, 1)

    @property
    def is_delivered(self):
        return self.status == 'delivered'

    @property
    def customer_review(self):
        return self.reviews.first()

    @property
    def has_review(self):
        return self.reviews.exists()


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    meal = models.ForeignKey(Meal, on_delete=models.SET_NULL, null=True, blank=True)
    meal_name = models.CharField(max_length=150)
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity}x {self.meal_name} @ ₹{self.unit_price}"


class Subscription(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Payment Pending'),
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
        ('expired', 'Expired'),
    ]

    DELIVERY_SLOTS = [
        ('lunch', 'Lunch (12:00 PM – 1:30 PM)'),
        ('dinner', 'Dinner (7:30 PM – 9:00 PM)'),
        ('both', 'Lunch & Dinner Both'),
    ]

    DIETARY_CHOICES = [
        ('veg', 'Pure Vegetarian'),
        ('non_veg', 'Non-Vegetarian'),
        ('jain', 'Jain (No Onion / Garlic)'),
    ]

    subscription_number = models.CharField(max_length=50, unique=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    chef = models.ForeignKey(ChefProfile, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(MealPlan, on_delete=models.CASCADE, related_name='subscriptions')
    start_date = models.DateField()
    end_date = models.DateField()
    recipient_name = models.CharField(max_length=120)
    recipient_phone = models.CharField(max_length=20)
    delivery_address_text = models.TextField()
    delivery_slot = models.CharField(max_length=20, choices=DELIVERY_SLOTS, default='lunch')
    dietary_preference = models.CharField(max_length=20, choices=DIETARY_CHOICES, default='veg')
    notes = models.TextField(blank=True, help_text="Spice level, allergies, special diet instructions")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, default='online')
    payment_status = models.CharField(max_length=20, default='paid')
    payment_transaction_id = models.CharField(max_length=100, blank=True)
    cancellation_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.subscription_number:
            ts = timezone.now().strftime('%Y%m%d')
            unique_part = str(uuid.uuid4().hex[:6]).upper()
            self.subscription_number = f"TT-SUB-{ts}-{unique_part}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.subscription_number} - {self.plan.name} ({self.get_status_display()})"

    @property
    def is_currently_active(self):
        today = timezone.now().date()
        return self.status == 'active' and self.start_date <= today <= self.end_date

    @property
    def can_cancel(self):
        return self.status in ['active', 'pending', 'paused']

    @property
    def can_pause(self):
        return self.status == 'active'

    @property
    def can_resume(self):
        return self.status == 'paused'


class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    chef = models.ForeignKey(ChefProfile, on_delete=models.CASCADE, related_name='reviews')
    order = models.ForeignKey('Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='reviews')
    meal = models.ForeignKey(Meal, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviews')
    rating = models.PositiveSmallIntegerField(choices=[(i, f"{i} Stars") for i in range(1, 6)], default=5)
    comment = models.TextField()
    is_hidden = models.BooleanField(default=False, help_text="Hidden by admin moderation")
    moderation_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.chef.update_rating()

    def delete(self, *args, **kwargs):
        chef = self.chef
        super().delete(*args, **kwargs)
        chef.update_rating()

    def __str__(self):
        order_str = f" [Order #{self.order.order_number}]" if self.order else ""
        return f"{self.rating}★ by {self.user.get_full_name() or self.user.username} for {self.chef.business_name}{order_str}"


class PasswordResetOTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_reset_otps')
    email = models.EmailField()
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    user_type = models.CharField(max_length=20, default='customer')  # 'customer' or 'chef'

    class Meta:
        verbose_name = 'Password Reset OTP'
        verbose_name_plural = 'Password Reset OTPs'
        ordering = ['-created_at']

    def is_valid(self):
        return (not self.is_used) and (timezone.now() < self.expires_at)

    def __str__(self):
        status = "Valid" if self.is_valid() else ("Used" if self.is_used else "Expired")
        return f"OTP ({self.user_type}) for {self.email} [{status}]"
