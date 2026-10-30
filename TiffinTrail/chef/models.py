from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify


class ChefProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='chef_profile')
    business_name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=160, unique=True, blank=True)
    bio = models.TextField(blank=True)
    profile_image = models.FileField(upload_to='chefs/', blank=True, null=True)
    cover_image = models.FileField(upload_to='chefs/covers/', blank=True, null=True)
    specialties = models.CharField(max_length=255, help_text="e.g. Punjabi Thalis, Dal Makhani, Gujarati Kadhi")
    cuisines = models.CharField(max_length=255, help_text="e.g. North Indian, Gujarati, South Indian")
    phone = models.CharField(max_length=20, blank=True)
    kitchen_address = models.TextField(blank=True, default="Home Kitchen, Indiranagar, Bengaluru")
    service_areas = models.CharField(max_length=255, help_text="Areas served e.g. Indiranagar, Koramangala, HSR Layout")
    starting_price = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('120.00'))
    experience_years = models.PositiveIntegerField(default=5)
    working_days = models.CharField(max_length=120, blank=True, default="Monday – Saturday")
    working_hours = models.CharField(max_length=120, blank=True, default="8:00 AM – 8:00 PM")
    preparation_preferences = models.TextField(blank=True, default="Fresh daily batch cooking, zero artificial food additives, food-grade thermal packaging.")
    commission_rate = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('10.00'), help_text="Platform commission percentage (e.g. 10.00 for 10%)")
    is_accepting_orders = models.BooleanField(default=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal('4.80'))
    review_count = models.PositiveIntegerField(default=0)
    VERIFICATION_STATUSES = [
        ('pending', 'Pending Review'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('resubmission', 'Resubmission Required'),
    ]
    verification_status = models.CharField(max_length=30, choices=VERIFICATION_STATUSES, default='approved')
    rejection_reason = models.TextField(blank=True)
    verification_document = models.FileField(upload_to='chefs/documents/', blank=True, null=True, help_text="Govt ID / FSSAI certificate")
    is_approved = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    fssai_license = models.CharField(max_length=50, blank=True, default="FSSAI-REG-2024-98412")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-rating', '-review_count', 'business_name']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.business_name or self.user.get_full_name() or self.user.username)
            candidate = base_slug
            idx = 1
            while ChefProfile.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                candidate = f"{base_slug}-{idx}"
                idx += 1
            self.slug = candidate
        super().save(*args, **kwargs)

    def __str__(self):
        return self.business_name or self.user.get_full_name() or self.user.username

    def get_cuisines_list(self):
        return [c.strip() for c in self.cuisines.split(',') if c.strip()]

    def get_service_areas_list(self):
        return [a.strip() for a in self.service_areas.split(',') if a.strip()]

    def update_rating(self):
        from customer.models import Review
        reviews = Review.objects.filter(chef=self)
        cnt = reviews.count()
        if cnt > 0:
            avg = reviews.aggregate(models.Avg('rating'))['rating__avg']
            self.rating = round(Decimal(str(avg)), 2)
            self.review_count = cnt
        else:
            self.rating = Decimal('5.00')
            self.review_count = 0
        self.save(update_fields=['rating', 'review_count'])


class MenuCategory(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, default="🍽")
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = 'Menu Categories'
        ordering = ['display_order', 'name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Meal(models.Model):
    MEAL_TYPE_CHOICES = [
        ('breakfast', 'Breakfast'),
        ('lunch', 'Lunch'),
        ('dinner', 'Dinner'),
        ('snacks', 'Evening Snacks'),
    ]

    chef = models.ForeignKey(ChefProfile, on_delete=models.CASCADE, related_name='meals')
    category = models.ForeignKey(MenuCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='meals')
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=160, blank=True)
    description = models.TextField()
    image = models.FileField(upload_to='meals/', blank=True, null=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    is_veg = models.BooleanField(default=True)
    cuisine = models.CharField(max_length=100, default='Homestyle Indian')
    meal_type = models.CharField(max_length=20, choices=MEAL_TYPE_CHOICES, default='lunch')
    calories = models.PositiveIntegerField(default=450, help_text="Approx calories")
    preparation_time = models.PositiveIntegerField(default=30, help_text="Minutes")
    available_quantity = models.PositiveIntegerField(default=20, help_text="Daily available portion count")
    is_available = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    ingredients = models.TextField(blank=True, help_text="Ingredients details")
    allergen_info = models.CharField(max_length=255, blank=True, help_text="e.g. Contains dairy, nuts, gluten")
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal('4.80'))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_featured', '-rating', 'name']

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(f"{self.name}-{self.chef.business_name or self.chef.id}")
            self.slug = base
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} (by {self.chef.business_name})"

    @property
    def dietary_label(self):
        return "Vegetarian" if self.is_veg else "Non-Vegetarian"


class MealPlan(models.Model):
    PLAN_TYPES = [
        ('daily', 'Daily Tiffin'),
        ('weekly', 'Weekly Subscription'),
        ('monthly', 'Monthly Subscription'),
    ]

    chef = models.ForeignKey(ChefProfile, on_delete=models.CASCADE, null=True, blank=True, related_name='meal_plans')
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=160, blank=True)
    description = models.TextField()
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPES, default='weekly')
    duration_days = models.PositiveIntegerField(default=7, help_text="Total days duration (e.g. 1, 7, 30)")
    meals_per_day = models.PositiveIntegerField(default=1, help_text="1 for Lunch, 2 for Lunch+Dinner")
    price = models.DecimalField(max_digits=8, decimal_places=2)
    original_price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="Standard non-discounted total")
    is_veg = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    features = models.TextField(help_text="Bullet points separated by newline")
    delivery_schedule = models.CharField(max_length=255, default="Lunch: 12:00 PM – 1:30 PM | Dinner: 7:30 PM – 9:00 PM")
    service_conditions = models.TextField(blank=True, default="Pause or skip days with 24 hours prior notice. Packed in hygienic thermal tiffins.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['price', 'name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        chef_part = f" - {self.chef.business_name}" if self.chef else " - Platform Wide"
        return f"{self.name} ({self.get_plan_type_display()}){chef_part}"

    @property
    def total_meals(self):
        return self.duration_days * self.meals_per_day

    @property
    def savings(self):
        if self.original_price and self.original_price > self.price:
            return self.original_price - self.price
        return None

    @property
    def savings_percent(self):
        if self.original_price and self.original_price > self.price:
            pct = ((self.original_price - self.price) / self.original_price) * 100
            return int(round(pct))
        return None

    def get_features_list(self):
        return [f.strip() for f in self.features.split('\n') if f.strip()]


class DailyMenu(models.Model):
    SLOT_CHOICES = [
        ('lunch', 'Lunch (12:00 PM – 1:30 PM)'),
        ('dinner', 'Dinner (7:30 PM – 9:00 PM)'),
        ('all_day', 'Both Lunch & Dinner'),
    ]

    chef = models.ForeignKey(ChefProfile, on_delete=models.CASCADE, related_name='daily_menus')
    date = models.DateField(db_index=True)
    meal = models.ForeignKey(Meal, on_delete=models.CASCADE, related_name='daily_schedules')
    slot = models.CharField(max_length=20, choices=SLOT_CHOICES, default='lunch')
    available_quantity = models.PositiveIntegerField(default=20)
    is_available = models.BooleanField(default=True)
    special_notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', 'slot', 'meal__name']
        unique_together = ('chef', 'date', 'meal', 'slot')

    def __str__(self):
        return f"{self.date} - {self.meal.name} ({self.get_slot_display()})"


class ChefNotification(models.Model):
    TYPE_CHOICES = [
        ('order', 'Incoming Order'),
        ('order_cancel', 'Order Cancelled'),
        ('subscription', 'New Subscription'),
        ('review', 'Customer Review'),
        ('payout', 'Payout Status'),
        ('system', 'System Notice'),
    ]

    chef = models.ForeignKey(ChefProfile, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=150)
    message = models.TextField()
    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES, default='order')
    link = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.chef.business_name}: {self.title}"
