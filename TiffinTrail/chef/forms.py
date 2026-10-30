from decimal import Decimal
from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import ChefProfile, Meal, MealPlan, MenuCategory, DailyMenu


class ChefRegistrationForm(forms.ModelForm):
    first_name = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}))
    last_name = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'chef@example.com'}))
    phone = forms.CharField(max_length=20, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+91 98765 43210'}))
    business_name = forms.CharField(max_length=150, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': "e.g. Amrita's Punjabi Rasoi"}))
    kitchen_address = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Kitchen location/address'}), required=True)
    cuisines = forms.CharField(max_length=255, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. North Indian, Punjabi, Mughlai'}))
    specialties = forms.CharField(max_length=255, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Dal Makhani, Phulka Thali, Paneer'}))
    service_areas = forms.CharField(max_length=255, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Indiranagar, Koramangala, Whitefield'}))
    profile_image = forms.FileField(required=False, widget=forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}))
    cover_image = forms.FileField(required=False, widget=forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}))
    verification_document = forms.FileField(required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Minimum 8 characters'}), min_length=8)
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm password'}))

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Choose username (e.g. chef_amrita)'}),
        }

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("This username is already taken. Please choose another.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email address already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.email = self.cleaned_data["email"].lower()
        if commit:
            user.save()
            chef = ChefProfile.objects.create(
                user=user,
                business_name=self.cleaned_data["business_name"],
                phone=self.cleaned_data["phone"],
                kitchen_address=self.cleaned_data["kitchen_address"],
                cuisines=self.cleaned_data["cuisines"],
                specialties=self.cleaned_data.get("specialties", ""),
                service_areas=self.cleaned_data.get("service_areas", ""),
                profile_image=self.cleaned_data.get("profile_image"),
                cover_image=self.cleaned_data.get("cover_image"),
                verification_document=self.cleaned_data.get("verification_document"),
                verification_status='pending',
                is_approved=False,
                is_active=True
            )
            try:
                from adminpanel.models import AdminNotification
                AdminNotification.objects.create(
                    title=f"New Chef Registration: {chef.business_name}",
                    message=f"Chef {user.get_full_name() or user.username} has applied to join TiffinTrail with '{chef.business_name}'. Verification is pending.",
                    notification_type='chef_registration',
                    link=f"/adminpanel/chefs/{chef.id}/"
                )
            except Exception:
                pass
        return user


class ChefProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))

    class Meta:
        model = ChefProfile
        fields = [
            'business_name', 'phone', 'kitchen_address', 'service_areas',
            'cuisines', 'specialties', 'experience_years', 'starting_price',
            'working_days', 'working_hours', 'preparation_preferences',
            'is_accepting_orders', 'bio', 'profile_image', 'cover_image'
        ]
        widgets = {
            'business_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Amrita\'s Punjabi Rasoi'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. +91 98765 43210'}),
            'kitchen_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Kitchen location / address'}),
            'service_areas': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Indiranagar, Koramangala, Domlur'}),
            'cuisines': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. North Indian, Punjabi, Mughlai'}),
            'specialties': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Dal Makhani, Phulka Thali, Paneer Butter Masala'}),
            'experience_years': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 50}),
            'starting_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '1.00', 'min': '20'}),
            'working_days': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Monday – Saturday'}),
            'working_hours': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 8:00 AM – 8:00 PM'}),
            'preparation_preferences': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Preparation norms e.g. low-oil, pure ghee, no MSG'}),
            'is_accepting_orders': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Tell diners about your culinary background and heritage recipes...'}),
            'profile_image': forms.FileInput(attrs={'class': 'form-control'}),
            'cover_image': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email

    def save(self, commit=True):
        profile = super().save(commit=False)
        user = profile.user
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email'].lower()
        if commit:
            user.save()
            profile.save()
        return profile


class MealForm(forms.ModelForm):
    class Meta:
        model = Meal
        fields = [
            'name', 'category', 'meal_type', 'price', 'is_veg', 'cuisine',
            'calories', 'preparation_time', 'available_quantity',
            'is_available', 'is_featured', 'ingredients', 'allergen_info',
            'description', 'image'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Dal Makhani & Phulka Thali'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'meal_type': forms.Select(attrs={'class': 'form-select'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '1.00', 'min': '10'}),
            'is_veg': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'cuisine': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Punjabi, South Indian, Gujarati'}),
            'calories': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 520'}),
            'preparation_time': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 25'}),
            'available_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ingredients': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Key ingredients, spices, flours used'}),
            'allergen_info': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Contains dairy/nuts/sesame'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Detailed homestyle dish description...'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
        }


class MealPlanForm(forms.ModelForm):
    class Meta:
        model = MealPlan
        fields = [
            'name', 'description', 'plan_type', 'duration_days', 'meals_per_day',
            'price', 'original_price', 'is_veg', 'is_active', 'features',
            'delivery_schedule', 'service_conditions'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Weekly Executive Lunch Plan'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'What makes this subscription great for diners'}),
            'plan_type': forms.Select(attrs={'class': 'form-select'}),
            'duration_days': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'meals_per_day': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 3}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '1.00'}),
            'original_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '1.00', 'placeholder': 'Optional baseline comparison price'}),
            'is_veg': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'features': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'One bullet per line:\nDaily varied curries\n3 Soft Phulkas + Rice\nFree thermal delivery'}),
            'delivery_schedule': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Lunch: 12:00 PM – 1:30 PM'}),
            'service_conditions': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Pause policy, packing norms'}),
        }


class DailyMenuForm(forms.ModelForm):
    class Meta:
        model = DailyMenu
        fields = ['meal', 'date', 'slot', 'available_quantity', 'is_available', 'special_notes']
        widgets = {
            'meal': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'slot': forms.Select(attrs={'class': 'form-select'}),
            'available_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'special_notes': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Extra sweet curd served today'}),
        }

    def __init__(self, chef, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['meal'].queryset = Meal.objects.filter(chef=chef)
        if not self.instance.pk:
            self.fields['date'].initial = timezone.now().date()


class MenuCategoryForm(forms.ModelForm):
    class Meta:
        model = MenuCategory
        fields = ['name', 'description', 'icon', 'display_order']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Homestyle Thalis'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Category description'}),
            'icon': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 🍛, 🥗, 🍲'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }
