from decimal import Decimal
import re
from django import forms
from django.contrib.auth.models import User
from django.utils import timezone
from chef.models import ChefProfile, Meal, MealPlan, MenuCategory
from customer.models import Coupon, Order, Subscription, CustomerProfile, Review
from .models import Complaint, ChefVerificationLog


class ChefVerificationForm(forms.ModelForm):
    admin_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Internal verification review notes...'})
    )

    class Meta:
        model = ChefProfile
        fields = ['verification_status', 'is_approved', 'is_active', 'commission_rate', 'rejection_reason']
        widgets = {
            'verification_status': forms.Select(attrs={'class': 'form-select'}),
            'commission_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.50', 'min': '0', 'max': '50'}),
            'rejection_reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Reason sent to chef if rejected or requiring resubmission'}),
            'is_approved': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ComplaintUpdateForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = ['status', 'priority', 'assigned_admin', 'admin_notes', 'customer_response']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'assigned_admin': forms.Select(attrs={'class': 'form-select'}),
            'admin_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Internal notes (visible to staff only)...'}),
            'customer_response': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Response message visible to customer...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assigned_admin'].queryset = User.objects.filter(is_staff=True)


class ComplaintCreateForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = ['customer', 'chef', 'order', 'category', 'subject', 'description', 'priority']
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-select'}),
            'chef': forms.Select(attrs={'class': 'form-select'}),
            'order': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'subject': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Complaint subject'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Detailed customer grievance...'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
        }


class AdminCouponForm(forms.ModelForm):
    valid_until = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
        input_formats=['%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d']
    )

    class Meta:
        model = Coupon
        fields = [
            'code', 'description', 'discount_type', 'discount_value',
            'min_order_amount', 'max_discount_amount', 'usage_limit',
            'is_active', 'valid_until'
        ]
        labels = {
            'description': 'Promotional Description',
            'discount_type': 'Discount Type',
            'discount_value': 'Discount Value',
            'min_order_amount': 'Minimum Order Amount (₹)',
            'max_discount_amount': 'Maximum Discount Cap (₹)',
            'usage_limit': 'Usage Limit (Total Redemptions)',
            'is_active': 'Active for Customer Checkout',
            'valid_until': 'Valid Until (Expiry Date/Time)',
        }
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control text-uppercase font-monospace', 'placeholder': 'e.g. FESTIVE50'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Get 50% off on your first meal order.'}),
            'discount_type': forms.Select(attrs={'class': 'form-select'}),
            'discount_value': forms.NumberInput(attrs={'class': 'form-control', 'step': '1.00', 'min': '1'}),
            'min_order_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '1.00', 'min': '0'}),
            'max_discount_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '1.00', 'placeholder': 'Cap for % discount'}),
            'usage_limit': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_code(self):
        code = self.cleaned_data['code'].upper().strip()
        qs = Coupon.objects.filter(code=code)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(f"Coupon code '{code}' already exists.")
        return code


class AdminMealPlanForm(forms.ModelForm):
    class Meta:
        model = MealPlan
        fields = [
            'chef', 'name', 'description', 'plan_type', 'duration_days',
            'meals_per_day', 'price', 'original_price', 'is_veg',
            'is_active', 'features', 'delivery_schedule', 'service_conditions'
        ]
        widgets = {
            'chef': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Traditional South Indian Thali Plan'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Brief summary of this meal plan...'}),
            'plan_type': forms.Select(attrs={'class': 'form-select'}),
            'duration_days': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'meals_per_day': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 3}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '1.00'}),
            'original_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '1.00'}),
            'is_veg': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'features': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': "Daily Changing Sabzi & Dal\nFresh Hot Phulkas\nPacked in Thermal Casserole"}),
            'delivery_schedule': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Lunch: 12:00 PM – 1:30 PM | Dinner: 7:30 PM – 9:00 PM'}),
            'service_conditions': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Pause or skip days with 24 hours prior notice.'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['chef'].empty_label = "Platform-wide (Available for all chefs)"
        self.fields['chef'].required = False
        self.fields['features'].help_text = "Enter each feature / inclusion on a new line."



class AdminMealForm(forms.ModelForm):
    class Meta:
        model = Meal
        fields = [
            'name', 'chef', 'category', 'meal_type', 'price',
            'is_veg', 'cuisine', 'available_quantity', 'calories', 'preparation_time',
            'is_available', 'is_featured', 'description', 'image'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Dish Name'}),
            'chef': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'meal_type': forms.Select(attrs={'class': 'form-select'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '1.00', 'min': '0'}),
            'is_veg': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'cuisine': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. North Indian, Punjabi'}),
            'available_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'calories': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'preparation_time': forms.NumberInput(attrs={'class': 'form-control', 'min': '5'}),
            'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Dish ingredients, taste profile, and preparation style...'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
        }


class AdminCustomerForm(forms.Form):
    first_name = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'})
    )
    last_name = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'})
    )
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'diner@example.com'})
    )
    phone = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '10-digit Phone'})
    )
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '••••••••'}),
        help_text="Required when creating. Leave blank to keep existing password when editing."
    )
    is_active = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    bio = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Customer profile notes or preferences...'})
    )

    def __init__(self, *args, user_instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_instance = user_instance
        if user_instance:
            self.fields['password'].required = False
            self.fields['username'].initial = user_instance.username
            self.fields['email'].initial = user_instance.email
            self.fields['first_name'].initial = user_instance.first_name
            self.fields['last_name'].initial = user_instance.last_name
            self.fields['is_active'].initial = user_instance.is_active
            profile = getattr(user_instance, 'customer_profile', None)
            if profile:
                self.fields['phone'].initial = profile.phone
                self.fields['bio'].initial = profile.bio
        else:
            self.fields['password'].required = True

    def clean_first_name(self):
        val = self.cleaned_data.get('first_name', '').strip()
        if not re.match(r"^[A-Za-z\s.'-]+$", val):
            raise forms.ValidationError("First name should only contain letters.")
        return val

    def clean_last_name(self):
        val = self.cleaned_data.get('last_name', '').strip()
        if not re.match(r"^[A-Za-z\s.'-]+$", val):
            raise forms.ValidationError("Last name should only contain letters.")
        return val

    def clean_phone(self):
        val = self.cleaned_data.get('phone', '').strip()
        if val:
            cleaned = re.sub(r'[\s\-+]', '', val)
            if cleaned.startswith('91') and len(cleaned) == 12:
                cleaned = cleaned[2:]
            if not (cleaned.isdigit() and len(cleaned) == 10):
                raise forms.ValidationError("Phone number must contain exactly 10 digits.")
            return cleaned
        return val

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        qs = User.objects.filter(username__iexact=username)
        if self.user_instance:
            qs = qs.exclude(pk=self.user_instance.pk)
        if qs.exists():
            raise forms.ValidationError(f"Username '{username}' is already in use.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        qs = User.objects.filter(email__iexact=email)
        if self.user_instance:
            qs = qs.exclude(pk=self.user_instance.pk)
        if qs.exists():
            raise forms.ValidationError(f"Email '{email}' is already registered.")
        return email


class AdminChefForm(forms.Form):
    first_name = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'})
    )
    last_name = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'})
    )
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'chef@example.com'})
    )
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '••••••••'}),
        help_text="Required when creating. Leave blank to keep existing password when editing."
    )
    business_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Annapurna Ghar Ka Khana'})
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '10-digit Mobile Number'})
    )
    specialties = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Punjabi Thalis, Dal Makhani'})
    )
    cuisines = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. North Indian, Gujarati, Punjabi'})
    )
    service_areas = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Satellite, Vastrapur, Indiranagar'})
    )
    starting_price = forms.DecimalField(
        max_digits=8,
        decimal_places=2,
        initial=Decimal('120.00'),
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '1.00', 'min': '0'})
    )
    commission_rate = forms.DecimalField(
        max_digits=4,
        decimal_places=2,
        initial=Decimal('10.00'),
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.50', 'min': '0', 'max': '50'})
    )
    kitchen_address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Home Kitchen Street Address & Area'})
    )
    bio = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Chef background, culinary story & cleanliness standards'})
    )
    verification_status = forms.ChoiceField(
        choices=ChefProfile.VERIFICATION_STATUSES,
        initial='approved',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    is_approved = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    is_active = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    def __init__(self, *args, chef_instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.chef_instance = chef_instance
        if chef_instance:
            self.fields['password'].required = False
            user = chef_instance.user
            self.fields['username'].initial = user.username
            self.fields['email'].initial = user.email
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['is_active'].initial = chef_instance.is_active
            self.fields['is_approved'].initial = chef_instance.is_approved
            self.fields['business_name'].initial = chef_instance.business_name
            self.fields['phone'].initial = chef_instance.phone
            self.fields['specialties'].initial = chef_instance.specialties
            self.fields['cuisines'].initial = chef_instance.cuisines
            self.fields['service_areas'].initial = chef_instance.service_areas
            self.fields['starting_price'].initial = chef_instance.starting_price
            self.fields['commission_rate'].initial = chef_instance.commission_rate
            self.fields['kitchen_address'].initial = chef_instance.kitchen_address
            self.fields['bio'].initial = chef_instance.bio
            self.fields['verification_status'].initial = chef_instance.verification_status
        else:
            self.fields['password'].required = True

    def clean_first_name(self):
        val = self.cleaned_data.get('first_name', '').strip()
        if not re.match(r"^[A-Za-z\s.'-]+$", val):
            raise forms.ValidationError("First name should only contain letters.")
        return val

    def clean_last_name(self):
        val = self.cleaned_data.get('last_name', '').strip()
        if not re.match(r"^[A-Za-z\s.'-]+$", val):
            raise forms.ValidationError("Last name should only contain letters.")
        return val

    def clean_phone(self):
        val = self.cleaned_data.get('phone', '').strip()
        if val:
            cleaned = re.sub(r'[\s\-+]', '', val)
            if cleaned.startswith('91') and len(cleaned) == 12:
                cleaned = cleaned[2:]
            if not (cleaned.isdigit() and len(cleaned) == 10):
                raise forms.ValidationError("Phone number must contain exactly 10 digits.")
            return cleaned
        return val

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        qs = User.objects.filter(username__iexact=username)
        if self.chef_instance:
            qs = qs.exclude(pk=self.chef_instance.user.pk)
        if qs.exists():
            raise forms.ValidationError(f"Username '{username}' is already in use.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        qs = User.objects.filter(email__iexact=email)
        if self.chef_instance:
            qs = qs.exclude(pk=self.chef_instance.user.pk)
        if qs.exists():
            raise forms.ValidationError(f"Email '{email}' is already registered.")
        return email


class AdminOrderEditForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = [
            'status', 'payment_status', 'payment_method',
            'recipient_name', 'recipient_phone', 'delivery_address_text', 'delivery_notes'
        ]
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'payment_status': forms.Select(attrs={'class': 'form-select'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'recipient_name': forms.TextInput(attrs={'class': 'form-control'}),
            'recipient_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'delivery_address_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'delivery_notes': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Gate notes, landmarks, instructions'}),
        }


class AdminSubscriptionEditForm(forms.ModelForm):
    class Meta:
        model = Subscription
        fields = [
            'status', 'delivery_slot', 'dietary_preference',
            'start_date', 'end_date', 'recipient_name', 'recipient_phone',
            'delivery_address_text', 'notes'
        ]
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'delivery_slot': forms.Select(attrs={'class': 'form-select'}),
            'dietary_preference': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'recipient_name': forms.TextInput(attrs={'class': 'form-control'}),
            'recipient_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'delivery_address_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Customer dietary or delivery instructions'}),
        }


class AdminProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }


class AdminPaymentRecordForm(forms.Form):
    order = forms.ModelChoiceField(
        queryset=Order.objects.all().order_by('-created_at'),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Associated Order"
    )
    payment_status = forms.ChoiceField(
        choices=Order.PAYMENT_STATUSES,
        initial='paid',
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Settlement Status"
    )
    payment_method = forms.ChoiceField(
        choices=Order.PAYMENT_METHODS,
        initial='online',
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Payment Method"
    )
    payment_transaction_id = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. UPI-TXN-987654 or Cash Receipt Ref'}),
        label="Transaction Reference / ID"
    )
    amount = forms.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Override amount (defaults to order total)'}),
        label="Amount Collected (₹)"
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional internal payment settlement note...'}),
        label="Settlement Remarks"
    )


class AdminPaymentEditForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['payment_status', 'payment_method', 'payment_transaction_id', 'final_amount']
        widgets = {
            'payment_status': forms.Select(attrs={'class': 'form-select'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'payment_transaction_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Transaction reference ID'}),
            'final_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }
        labels = {
            'payment_status': 'Payment Status',
            'payment_method': 'Payment Mode',
            'payment_transaction_id': 'Transaction ID / Reference',
            'final_amount': 'Final Settled Amount (₹)',
        }


class AdminComplaintEditForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = [
            'category', 'priority', 'status', 'subject', 'description',
            'customer', 'chef', 'order', 'assigned_admin', 'admin_notes', 'customer_response'
        ]
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'subject': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'customer': forms.Select(attrs={'class': 'form-select'}),
            'chef': forms.Select(attrs={'class': 'form-select'}),
            'order': forms.Select(attrs={'class': 'form-select'}),
            'assigned_admin': forms.Select(attrs={'class': 'form-select'}),
            'admin_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Internal notes...'}),
            'customer_response': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Response visible to customer...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assigned_admin'].queryset = User.objects.filter(is_staff=True)
        self.fields['chef'].required = False
        self.fields['order'].required = False


class AdminReviewEditForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment', 'is_hidden', 'moderation_notes']
        widgets = {
            'rating': forms.Select(attrs={'class': 'form-select'}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'is_hidden': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'moderation_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Internal moderation reason/notes'}),
        }
