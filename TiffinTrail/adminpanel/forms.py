from decimal import Decimal
from django import forms
from django.contrib.auth.models import User
from django.utils import timezone
from chef.models import ChefProfile, Meal, MealPlan, MenuCategory
from customer.models import Coupon, Order
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
            'is_veg', 'cuisine', 'available_quantity',
            'is_available', 'is_featured', 'description'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'chef': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'meal_type': forms.Select(attrs={'class': 'form-select'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '1.00'}),
            'is_veg': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'cuisine': forms.TextInput(attrs={'class': 'form-control'}),
            'available_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
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
