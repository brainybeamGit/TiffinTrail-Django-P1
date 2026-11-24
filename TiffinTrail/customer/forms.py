from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import CustomerProfile, DeliveryAddress, Review, Order, Subscription, MealPlan


import re

class CustomerRegistrationForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First Name',
            'pattern': r"[A-Za-z\s.'-]+",
            'title': 'Only letters allowed (no numbers)'
        })
    )
    last_name = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last Name',
            'pattern': r"[A-Za-z\s.'-]+",
            'title': 'Only letters allowed (no numbers)'
        })
    )
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'}))
    phone = forms.CharField(
        max_length=10,
        min_length=10,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '10-Digit Mobile Number (e.g. 9876543210)',
            'maxlength': '10',
            'pattern': '[0-9]{10}',
            'inputmode': 'numeric',
            'title': 'Must be exactly 10 digits'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password (min 8 chars, 1 special char)'
        }),
        min_length=8
    )
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm Password'}))

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
        }

    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name', '').strip()
        if any(char.isdigit() for char in first_name):
            raise ValidationError("First name must contain only letters, numbers are not allowed.")
        if not re.match(r"^[A-Za-z\s.'-]+$", first_name):
            raise ValidationError("First name must contain only letters, numbers are not allowed.")
        return first_name

    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name', '').strip()
        if any(char.isdigit() for char in last_name):
            raise ValidationError("Last name must contain only letters, numbers are not allowed.")
        if not re.match(r"^[A-Za-z\s.'-]+$", last_name):
            raise ValidationError("Last name must contain only letters, numbers are not allowed.")
        return last_name

    def clean_email(self):
        email = self.cleaned_data.get('email', '').lower()
        if User.objects.filter(email=email).exists():
            raise ValidationError("An account with this email address already exists.")
        return email

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip().replace(' ', '').replace('-', '')
        if not phone.isdigit() or len(phone) != 10:
            raise ValidationError("Mobile number must be exactly 10 digits.")
        return phone

    def clean_password(self):
        password = self.cleaned_data.get('password', '')
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long.")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>_+\-=\[\]\\;\'`~]', password):
            raise ValidationError("Password must contain at least one special character (e.g. @, #, $, %, etc.).")
        return password

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
            CustomerProfile.objects.create(
                user=user,
                phone=self.cleaned_data["phone"]
            )
        return user


class CustomerProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))

    class Meta:
        model = CustomerProfile
        fields = ['phone', 'bio', 'profile_image']
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'A little about your taste preferences...'}),
            'profile_image': forms.FileInput(attrs={'class': 'form-control'}),
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
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            profile.save()
        return profile


class DeliveryAddressForm(forms.ModelForm):
    class Meta:
        model = DeliveryAddress
        fields = ['title', 'recipient_name', 'phone_number', 'street_address', 'area', 'city', 'pincode', 'delivery_notes', 'is_default']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Home, Office, Parent’s Home'}),
            'recipient_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Name of person receiving meal'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '10-digit mobile number'}),
            'street_address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Flat/House No, Building, Street'}),
            'area': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Area / Locality / Landmark'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'pincode': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Pincode (e.g. 560038)'}),
            'delivery_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Gate directions, bell instruction...'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.Select(attrs={'class': 'form-select'}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Share your experience with freshness, taste, and packaging...'}),
        }


class CheckoutForm(forms.Form):
    recipient_name = forms.CharField(max_length=120, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Recipient Full Name'}))
    recipient_phone = forms.CharField(max_length=20, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contact Phone Number'}))
    address_choice = forms.CharField(required=False)
    
    # New address fields if no saved address chosen
    street_address = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Flat/House No, Building Name'}))
    area = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Area / Landmark'}))
    city = forms.CharField(required=False, initial='Bengaluru', widget=forms.TextInput(attrs={'class': 'form-control'}))
    pincode = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Postal Pincode'}))
    delivery_notes = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Special delivery instructions...'}))
    save_address = forms.BooleanField(required=False, initial=True, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    
    payment_method = forms.ChoiceField(
        choices=Order.PAYMENT_METHODS,
        initial='online',
        widget=forms.RadioSelect
    )


class SubscriptionForm(forms.Form):
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        help_text="Choose when you'd like your meal service to begin"
    )
    delivery_slot = forms.ChoiceField(
        choices=Subscription.DELIVERY_SLOTS,
        initial='lunch',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    dietary_preference = forms.ChoiceField(
        choices=Subscription.DIETARY_CHOICES,
        initial='veg',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    recipient_name = forms.CharField(max_length=120, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Recipient Name'}))
    recipient_phone = forms.CharField(max_length=20, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}))
    address_choice = forms.CharField(required=False)
    
    street_address = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Flat / Building / Street'}))
    area = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Area / Locality'}))
    city = forms.CharField(required=False, initial='Bengaluru', widget=forms.TextInput(attrs={'class': 'form-control'}))
    pincode = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Pincode'}))
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Spice preferences, no coriander, less oil, etc.'}))
    payment_method = forms.ChoiceField(
        choices=[('online', 'Instant Online Payment (Cards/UPI/NetBanking)'), ('cod', 'Pay at First Delivery (Cash/UPI)')],
        initial='online',
        widget=forms.RadioSelect
    )

    def clean_start_date(self):
        start_date = self.cleaned_data.get('start_date')
        if start_date and start_date < timezone.now().date():
            raise ValidationError("Subscription start date cannot be in the past.")
        return start_date
