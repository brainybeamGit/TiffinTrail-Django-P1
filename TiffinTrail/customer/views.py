from decimal import Decimal
from datetime import timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.db import transaction
from django.db.models import Q, Avg, Count
from django.core.paginator import Paginator
from django.utils import timezone
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse

import razorpay
from django.conf import settings

from chef.models import ChefProfile, Meal, MealPlan, MenuCategory, ChefNotification
from .models import (
    CustomerProfile, DeliveryAddress, Coupon,
    Cart, CartItem, Order, OrderItem,
    Subscription, Review
)
from .forms import (
    CustomerRegistrationForm, CustomerProfileForm,
    DeliveryAddressForm, ReviewForm,
    CheckoutForm, SubscriptionForm
)


def get_or_create_cart(request):
    """Retrieves or creates a cart for the current authenticated user or guest session."""
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        # Migrate guest session cart if exists
        session_key = request.session.session_key
        if session_key:
            guest_cart = Cart.objects.filter(session_key=session_key).first()
            if guest_cart and guest_cart != cart:
                for item in guest_cart.items.all():
                    existing_item = cart.items.filter(meal=item.meal).first()
                    if existing_item:
                        existing_item.quantity += item.quantity
                        existing_item.save()
                    else:
                        item.cart = cart
                        item.save()
                guest_cart.delete()
        return cart
    else:
        if not request.session.session_key:
            request.session.create()
        cart, _ = Cart.objects.get_or_create(session_key=request.session.session_key)
        return cart


def home(request):
    """Dynamic Homepage featuring chefs, meals, plans, reviews, and testimonials."""
    featured_chefs = ChefProfile.objects.filter(is_approved=True, is_active=True).order_by('-rating', '-review_count')[:6]
    popular_meals = Meal.objects.filter(is_available=True, is_featured=True).select_related('chef', 'category')[:8]
    if not popular_meals.exists():
        popular_meals = Meal.objects.filter(is_available=True).select_related('chef', 'category')[:8]
    
    meal_plans = MealPlan.objects.filter(is_active=True).select_related('chef').order_by('price')[:4]
    categories = MenuCategory.objects.all().order_by('display_order')[:6]
    customer_reviews = Review.objects.select_related('user', 'chef').order_by('-rating', '-created_at')[:6]

    featured_coupon = Coupon.get_available_coupons().first()

    context = {
        'featured_chefs': featured_chefs,
        'popular_meals': popular_meals,
        'meal_plans': meal_plans,
        'categories': categories,
        'customer_reviews': customer_reviews,
        'featured_coupon': featured_coupon,
        'total_chefs': ChefProfile.objects.filter(is_approved=True, is_active=True).count(),
        'total_meals': Meal.objects.filter(is_available=True).count(),
    }
    return render(request, 'customer/home.html', context)


def chef_list(request):
    """Browse approved chefs with search, filtering, sorting, and pagination."""
    chefs = ChefProfile.objects.filter(is_approved=True, is_active=True)

    # Search
    search_query = request.GET.get('q', '').strip()
    if search_query:
        chefs = chefs.filter(
            Q(business_name__icontains=search_query) |
            Q(cuisines__icontains=search_query) |
            Q(specialties__icontains=search_query) |
            Q(service_areas__icontains=search_query)
        )

    # Filter: Cuisine
    cuisine_filter = request.GET.get('cuisine', '').strip()
    if cuisine_filter:
        chefs = chefs.filter(cuisines__icontains=cuisine_filter)

    # Filter: Rating
    rating_filter = request.GET.get('min_rating')
    if rating_filter:
        try:
            chefs = chefs.filter(rating__gte=Decimal(rating_filter))
        except (ValueError, TypeError):
            pass

    # Filter: Max starting price
    max_price = request.GET.get('max_price')
    if max_price:
        try:
            chefs = chefs.filter(starting_price__lte=Decimal(max_price))
        except (ValueError, TypeError):
            pass

    # Sort
    sort_by = request.GET.get('sort', 'rating_desc')
    if sort_by == 'price_asc':
        chefs = chefs.order_by('starting_price')
    elif sort_by == 'price_desc':
        chefs = chefs.order_by('-starting_price')
    elif sort_by == 'reviews':
        chefs = chefs.order_by('-review_count')
    else:  # rating_desc
        chefs = chefs.order_by('-rating', '-review_count')

    # Pagination
    paginator = Paginator(chefs, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Available cuisines for filter tags
    all_cuisines = set()
    for cp in ChefProfile.objects.filter(is_approved=True, is_active=True):
        all_cuisines.update(cp.get_cuisines_list())

    context = {
        'page_obj': page_obj,
        'chefs': page_obj.object_list,
        'search_query': search_query,
        'cuisine_filter': cuisine_filter,
        'rating_filter': rating_filter,
        'max_price': max_price,
        'sort_by': sort_by,
        'all_cuisines': sorted(list(all_cuisines)),
    }
    return render(request, 'customer/chef_list.html', context)


def chef_detail(request, pk=None, slug=None):
    """Detailed profile page for a chef with meals, plans, reviews, and review form."""
    if slug:
        chef = get_object_or_404(ChefProfile, slug=slug, is_approved=True, is_active=True)
    else:
        chef = get_object_or_404(ChefProfile, pk=pk, is_approved=True, is_active=True)

    meals = chef.meals.filter(is_available=True).select_related('category')
    meal_plans = chef.meal_plans.filter(is_active=True)
    if not meal_plans.exists():
        # Fall back to platform meal plans
        meal_plans = MealPlan.objects.filter(is_active=True, chef__isnull=True)

    reviews = chef.reviews.select_related('user').order_by('-created_at')
    user_review = None
    if request.user.is_authenticated:
        user_review = Review.objects.filter(chef=chef, user=request.user, meal__isnull=True).first()

    review_form = ReviewForm(instance=user_review) if request.user.is_authenticated else None

    context = {
        'chef': chef,
        'meals': meals,
        'meal_plans': meal_plans,
        'reviews': reviews,
        'user_review': user_review,
        'review_form': review_form,
    }
    return render(request, 'customer/chef_detail.html', context)


def menu(request):
    """Food menu catalog with full filtering, search, sorting, and pagination."""
    meals = Meal.objects.filter(is_available=True, chef__is_approved=True, chef__is_active=True).select_related('chef', 'category')

    # Search
    search_query = request.GET.get('q', '').strip()
    if search_query:
        meals = meals.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(cuisine__icontains=search_query) |
            Q(chef__business_name__icontains=search_query)
        )

    # Category filter
    category_slug = request.GET.get('category', '').strip()
    if category_slug:
        meals = meals.filter(category__slug=category_slug)

    # Dietary filter
    diet = request.GET.get('diet', '').strip()
    if diet == 'veg':
        meals = meals.filter(is_veg=True)
    elif diet == 'non_veg':
        meals = meals.filter(is_veg=False)

    # Chef filter
    chef_id = request.GET.get('chef')
    if chef_id:
        meals = meals.filter(chef_id=chef_id)

    # Price max
    max_price = request.GET.get('max_price')
    if max_price:
        try:
            meals = meals.filter(price__lte=Decimal(max_price))
        except (ValueError, TypeError):
            pass

    # Sorting
    sort_by = request.GET.get('sort', 'featured')
    if sort_by == 'price_asc':
        meals = meals.order_by('price')
    elif sort_by == 'price_desc':
        meals = meals.order_by('-price')
    elif sort_by == 'rating':
        meals = meals.order_by('-rating')
    else:  # featured / default
        meals = meals.order_by('-is_featured', '-rating', 'name')

    # Pagination
    paginator = Paginator(meals, 8)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    categories = MenuCategory.objects.all().order_by('display_order')
    approved_chefs = ChefProfile.objects.filter(is_approved=True, is_active=True).order_by('business_name')

    context = {
        'page_obj': page_obj,
        'meals': page_obj.object_list,
        'categories': categories,
        'approved_chefs': approved_chefs,
        'search_query': search_query,
        'category_slug': category_slug,
        'diet': diet,
        'selected_chef': chef_id,
        'max_price': max_price,
        'sort_by': sort_by,
    }
    return render(request, 'customer/menu.html', context)


def meal_detail(request, pk):
    """Detailed standalone view for a specific meal."""
    meal = get_object_or_404(Meal, pk=pk, is_available=True, chef__is_approved=True, chef__is_active=True)
    related_meals = Meal.objects.filter(
        chef=meal.chef, is_available=True
    ).exclude(pk=meal.pk)[:4]

    reviews = Review.objects.filter(meal=meal).select_related('user').order_by('-created_at')

    context = {
        'meal': meal,
        'related_meals': related_meals,
        'reviews': reviews,
    }
    return render(request, 'customer/meal_detail.html', context)


def meal_plans(request):
    """Dedicated meal plans and subscriptions browsing page."""
    plans = MealPlan.objects.filter(is_active=True).select_related('chef')

    plan_type = request.GET.get('type')
    if plan_type in ['daily', 'weekly', 'monthly']:
        plans = plans.filter(plan_type=plan_type)

    diet = request.GET.get('diet')
    if diet == 'veg':
        plans = plans.filter(is_veg=True)
    elif diet == 'non_veg':
        plans = plans.filter(is_veg=False)

    chefs = ChefProfile.objects.filter(is_approved=True, is_active=True)

    context = {
        'plans': plans,
        'plan_type': plan_type,
        'diet': diet,
        'chefs': chefs,
    }
    return render(request, 'customer/meal_plans.html', context)


@login_required
def subscribe(request, chef_id=None, plan_id=None):
    """Step-by-step subscription flow with chef selection, plan review, dates, address and checkout."""
    chef = None
    plan = None

    if chef_id:
        chef = get_object_or_404(ChefProfile, pk=chef_id, is_approved=True, is_active=True)
    if plan_id:
        plan = get_object_or_404(MealPlan, pk=plan_id, is_active=True)

    # If chef not specified in URL or plan doesn't have fixed chef, allow chef selection
    available_chefs = ChefProfile.objects.filter(is_approved=True, is_active=True)
    available_plans = MealPlan.objects.filter(is_active=True)
    user_addresses = request.user.addresses.all()

    if not chef and available_chefs.exists():
        chef = available_chefs.first()
    if not plan and available_plans.exists():
        plan = available_plans.first()

    if request.method == 'POST':
        form = SubscriptionForm(request.POST)
        selected_chef_id = request.POST.get('chef_id') or (chef.id if chef else None)
        selected_plan_id = request.POST.get('plan_id') or (plan.id if plan else None)

        if not selected_chef_id or not selected_plan_id:
            messages.error(request, "Please choose both a chef and a meal plan to subscribe.")
            return redirect('customer:subscribe')

        chef_obj = get_object_or_404(ChefProfile, pk=selected_chef_id, is_approved=True, is_active=True)
        plan_obj = get_object_or_404(MealPlan, pk=selected_plan_id, is_active=True)

        if form.is_valid():
            payment_method = form.cleaned_data['payment_method']

            # Strict check: Online payment subscriptions CANNOT be placed without Razorpay verification.
            if payment_method != 'cod':
                messages.error(request, "Online payment complete hone ke baad hi subscription confirm hoti hai. Kripya Razorpay gateway se payment karein.")
                return redirect('customer:subscribe_direct', chef_id=selected_chef_id, plan_id=selected_plan_id)

            start_date = form.cleaned_data['start_date']
            end_date = start_date + timedelta(days=plan_obj.duration_days)
            recipient_name = form.cleaned_data['recipient_name']
            recipient_phone = form.cleaned_data['recipient_phone']

            # Resolve address
            addr_choice = request.POST.get('address_choice')
            if addr_choice and addr_choice.isdigit():
                addr = DeliveryAddress.objects.filter(pk=int(addr_choice), user=request.user).first()
                if addr:
                    delivery_address_text = addr.formatted
                else:
                    delivery_address_text = f"{form.cleaned_data.get('street_address')}, {form.cleaned_data.get('area')}, {form.cleaned_data.get('city')} - {form.cleaned_data.get('pincode')}"
            else:
                street = form.cleaned_data.get('street_address', '')
                area = form.cleaned_data.get('area', '')
                city = form.cleaned_data.get('city', 'Bengaluru')
                pincode = form.cleaned_data.get('pincode', '')
                delivery_address_text = f"{street}, {area}, {city} - {pincode}" if area else f"{street}, {city} - {pincode}"
                # Save as address if requested
                if request.POST.get('save_address') and street and pincode:
                    DeliveryAddress.objects.create(
                        user=request.user,
                        title='Subscription Address',
                        recipient_name=recipient_name,
                        phone_number=recipient_phone,
                        street_address=street,
                        area=area,
                        city=city,
                        pincode=pincode
                    )

            # Create COD subscription
            sub = Subscription.objects.create(
                user=request.user,
                chef=chef_obj,
                plan=plan_obj,
                start_date=start_date,
                end_date=end_date,
                recipient_name=recipient_name,
                recipient_phone=recipient_phone,
                delivery_address_text=delivery_address_text,
                delivery_slot=form.cleaned_data['delivery_slot'],
                dietary_preference=form.cleaned_data['dietary_preference'],
                notes=form.cleaned_data.get('notes', ''),
                status='active',
                total_amount=plan_obj.price,
                payment_method='cod',
                payment_status='pending',
                payment_transaction_id=''
            )

            # Notify Chef
            ChefNotification.objects.create(
                chef=chef_obj,
                title="New Meal Plan Subscription (Cash on Delivery)",
                message=f"{recipient_name} subscribed to '{plan_obj.name}' ({sub.get_delivery_slot_display()}). Total: ₹{sub.total_amount}.",
                notification_type='subscription',
                link=f"/chef/subscriptions/{sub.id}/"
            )

            # Send Email Confirmation
            try:
                from .emails import send_subscription_confirmation_email
                send_subscription_confirmation_email(sub, async_send=True)
            except Exception:
                pass

            messages.success(request, f"🎉 Subscription successfully created! Your {plan_obj.name} starts on {start_date.strftime('%b %d, %Y')}.")
            return redirect('customer:subscription_detail', pk=sub.pk)
    else:
        initial_data = {
            'start_date': timezone.now().date() + timedelta(days=1),
            'recipient_name': request.user.get_full_name() or request.user.username,
            'recipient_phone': getattr(request.user, 'customer_profile', None).phone if hasattr(request.user, 'customer_profile') else '',
        }
        form = SubscriptionForm(initial=initial_data)

    context = {
        'chef': chef,
        'plan': plan,
        'available_chefs': available_chefs,
        'available_plans': available_plans,
        'user_addresses': user_addresses,
        'form': form,
        'razorpay_key_id': getattr(settings, 'RAZORPAY_KEY_ID', ''),
    }
    return render(request, 'customer/subscribe.html', context)


@login_required
def razorpay_subscription_create(request):
    """Generates a Razorpay Order ID for meal plan subscription checkout."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)

    selected_chef_id = request.POST.get('chef_id')
    selected_plan_id = request.POST.get('plan_id')

    if not selected_chef_id or not selected_plan_id:
        return JsonResponse({'status': 'error', 'message': 'Please choose both a chef and a meal plan.'}, status=400)

    chef_obj = get_object_or_404(ChefProfile, pk=selected_chef_id, is_approved=True, is_active=True)
    plan_obj = get_object_or_404(MealPlan, pk=selected_plan_id, is_active=True)

    recipient_name = request.POST.get('recipient_name', '').strip() or request.user.get_full_name() or request.user.username
    recipient_phone = request.POST.get('recipient_phone', '').strip()
    if not recipient_phone and hasattr(request.user, 'customer_profile'):
        recipient_phone = getattr(request.user.customer_profile, 'phone', '')

    if not recipient_name or not recipient_phone:
        return JsonResponse({'status': 'error', 'message': 'Recipient name and phone number are required.'}, status=400)

    amount_paise = int(round(plan_obj.price * Decimal('100.00')))
    if amount_paise <= 0:
        return JsonResponse({'status': 'error', 'message': 'Invalid subscription plan amount.'}, status=400)

    key_id = getattr(settings, 'RAZORPAY_KEY_ID', '')
    key_secret = getattr(settings, 'RAZORPAY_KEY_SECRET', '')

    if not key_id or not key_secret:
        return JsonResponse({'status': 'error', 'message': 'Razorpay payment keys are not configured.'}, status=500)

    try:
        client = razorpay.Client(auth=(key_id, key_secret))
        razorpay_order = client.order.create({
            'amount': amount_paise,
            'currency': 'INR',
            'payment_capture': 1,
            'notes': {
                'user_id': str(request.user.id),
                'username': request.user.username,
                'type': 'subscription',
                'plan_id': str(plan_obj.id),
                'plan_name': plan_obj.name[:40],
                'chef_id': str(chef_obj.id),
                'chef_name': chef_obj.business_name[:40],
                'recipient_name': recipient_name[:40],
            }
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Razorpay order creation failed: {str(e)}'}, status=500)

    return JsonResponse({
        'status': 'success',
        'key_id': key_id,
        'razorpay_order_id': razorpay_order['id'],
        'amount': razorpay_order['amount'],
        'currency': razorpay_order.get('currency', 'INR'),
        'customer_name': recipient_name,
        'customer_email': request.user.email or '',
        'customer_phone': recipient_phone,
        'plan_name': plan_obj.name,
        'chef_name': chef_obj.business_name,
    })


@login_required
def razorpay_subscription_verify(request):
    """Verifies Razorpay payment signature and confirms subscription."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)

    razorpay_payment_id = request.POST.get('razorpay_payment_id', '').strip()
    razorpay_order_id = request.POST.get('razorpay_order_id', '').strip()
    razorpay_signature = request.POST.get('razorpay_signature', '').strip()

    if not razorpay_payment_id or not razorpay_order_id or not razorpay_signature:
        return JsonResponse({'status': 'error', 'message': 'Missing payment signature credentials.'}, status=400)

    key_id = getattr(settings, 'RAZORPAY_KEY_ID', '')
    key_secret = getattr(settings, 'RAZORPAY_KEY_SECRET', '')

    try:
        client = razorpay.Client(auth=(key_id, key_secret))
        client.utility.verify_payment_signature({
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature,
        })
    except razorpay.errors.SignatureVerificationError:
        return JsonResponse({'status': 'error', 'message': 'Payment verification failed: Invalid Razorpay signature.'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Verification error: {str(e)}'}, status=400)

    selected_chef_id = request.POST.get('chef_id')
    selected_plan_id = request.POST.get('plan_id')

    if not selected_chef_id or not selected_plan_id:
        return JsonResponse({'status': 'error', 'message': 'Chef and meal plan are required.'}, status=400)

    chef_obj = get_object_or_404(ChefProfile, pk=selected_chef_id, is_approved=True, is_active=True)
    plan_obj = get_object_or_404(MealPlan, pk=selected_plan_id, is_active=True)

    form = SubscriptionForm(request.POST)
    if not form.is_valid():
        err_msgs = []
        for field, errors in form.errors.items():
            err_msgs.append(f"{field}: {', '.join(errors)}")
        return JsonResponse({'status': 'error', 'message': f"Form validation failed: {'; '.join(err_msgs)}"}, status=400)

    start_date = form.cleaned_data['start_date']
    end_date = start_date + timedelta(days=plan_obj.duration_days)
    recipient_name = form.cleaned_data['recipient_name']
    recipient_phone = form.cleaned_data['recipient_phone']

    # Resolve address
    addr_choice = request.POST.get('address_choice')
    if addr_choice and addr_choice.isdigit():
        addr = DeliveryAddress.objects.filter(pk=int(addr_choice), user=request.user).first()
        if addr:
            delivery_address_text = addr.formatted
        else:
            delivery_address_text = f"{form.cleaned_data.get('street_address')}, {form.cleaned_data.get('area')}, {form.cleaned_data.get('city')} - {form.cleaned_data.get('pincode')}"
    else:
        street = form.cleaned_data.get('street_address', '')
        area = form.cleaned_data.get('area', '')
        city = form.cleaned_data.get('city', 'Bengaluru')
        pincode = form.cleaned_data.get('pincode', '')
        if not street or not pincode:
            return JsonResponse({'status': 'error', 'message': 'Street address and pincode are required.'}, status=400)
        delivery_address_text = f"{street}, {area}, {city} - {pincode}" if area else f"{street}, {city} - {pincode}"
        if request.POST.get('save_address') and street and pincode:
            DeliveryAddress.objects.create(
                user=request.user,
                title='Subscription Address',
                recipient_name=recipient_name,
                phone_number=recipient_phone,
                street_address=street,
                area=area,
                city=city,
                pincode=pincode
            )

    sub = Subscription.objects.create(
        user=request.user,
        chef=chef_obj,
        plan=plan_obj,
        start_date=start_date,
        end_date=end_date,
        recipient_name=recipient_name,
        recipient_phone=recipient_phone,
        delivery_address_text=delivery_address_text,
        delivery_slot=form.cleaned_data['delivery_slot'],
        dietary_preference=form.cleaned_data['dietary_preference'],
        notes=form.cleaned_data.get('notes', ''),
        status='active',
        total_amount=plan_obj.price,
        payment_method='online',
        payment_status='paid',
        payment_transaction_id=razorpay_payment_id
    )

    ChefNotification.objects.create(
        chef=chef_obj,
        title="New Meal Plan Subscription (Paid via Razorpay)",
        message=f"{recipient_name} subscribed to '{plan_obj.name}' ({sub.get_delivery_slot_display()}). Total: ₹{sub.total_amount}.",
        notification_type='subscription',
        link=f"/chef/subscriptions/{sub.id}/"
    )

    # Send Email Confirmation
    try:
        from .emails import send_subscription_confirmation_email
        send_subscription_confirmation_email(sub, async_send=True)
    except Exception:
        pass

    messages.success(request, f"🎉 Subscription successfully activated! Payment of ₹{sub.total_amount} verified via Razorpay for {plan_obj.name}.")
    return JsonResponse({
        'status': 'success',
        'subscription_id': sub.pk,
        'subscription_number': sub.subscription_number,
        'redirect_url': reverse('customer:subscription_detail', kwargs={'pk': sub.pk}),
    })


@login_required
def my_subscriptions(request):
    """View customer's active, upcoming, completed, and paused subscriptions."""
    status_filter = request.GET.get('status', 'all')
    subs = Subscription.objects.filter(user=request.user).select_related('chef', 'plan')

    if status_filter != 'all':
        subs = subs.filter(status=status_filter)

    context = {
        'subscriptions': subs,
        'status_filter': status_filter,
    }
    return render(request, 'customer/subscriptions.html', context)


@login_required
def subscription_detail(request, pk):
    """Detailed view for a specific subscription with pause/resume and cancellation options."""
    subscription = get_object_or_404(Subscription, pk=pk, user=request.user)
    context = {
        'sub': subscription,
    }
    return render(request, 'customer/subscription_detail.html', context)


@login_required
def subscription_cancel(request, pk):
    """Cancel an active or paused subscription."""
    sub = get_object_or_404(Subscription, pk=pk, user=request.user)
    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        if sub.can_cancel:
            sub.status = 'cancelled'
            sub.cancellation_reason = reason or "Cancelled by customer."
            sub.save(update_fields=['status', 'cancellation_reason'])

            ChefNotification.objects.create(
                chef=sub.chef,
                title="Subscription Cancelled",
                message=f"Subscription #{sub.subscription_number} for '{sub.plan.name}' was cancelled by {sub.recipient_name}.",
                notification_type='order_cancel',
                link=f"/chef/subscriptions/{sub.id}/"
            )

            messages.success(request, "Your subscription has been cancelled.")
        else:
            messages.error(request, "This subscription cannot be cancelled at this stage.")
    return redirect('customer:subscription_detail', pk=sub.pk)


@login_required
def subscription_pause(request, pk):
    """Pause an active subscription."""
    sub = get_object_or_404(Subscription, pk=pk, user=request.user)
    if request.method == 'POST' and sub.can_pause:
        sub.status = 'paused'
        sub.save(update_fields=['status'])
        messages.success(request, "Your subscription delivery has been temporarily paused.")
    return redirect('customer:subscription_detail', pk=sub.pk)


@login_required
def subscription_resume(request, pk):
    """Resume a paused subscription."""
    sub = get_object_or_404(Subscription, pk=pk, user=request.user)
    if request.method == 'POST' and sub.can_resume:
        sub.status = 'active'
        sub.save(update_fields=['status'])
        messages.success(request, "Your subscription delivery has been resumed.")
    return redirect('customer:subscription_detail', pk=sub.pk)


def cart(request):
    """Shopping cart view with items, server-side totals, coupon code application, and breakdown."""
    cart_obj = get_or_create_cart(request)
    items = cart_obj.items.select_related('meal', 'meal__chef').order_by('created_at')

    # Validate items still available
    unavailable_items = []
    for item in items:
        if not item.meal.is_available:
            unavailable_items.append(item.meal.name)

    available_coupons = Coupon.get_available_coupons()

    context = {
        'cart': cart_obj,
        'items': items,
        'unavailable_items': unavailable_items,
        'available_coupons': available_coupons,
    }
    return render(request, 'customer/cart.html', context)


def cart_add(request, meal_id):
    """Adds a meal to the cart with server-side validation and quantity controls."""
    meal = get_object_or_404(Meal, pk=meal_id, is_available=True, chef__is_approved=True, chef__is_active=True)
    cart_obj = get_or_create_cart(request)

    qty = 1
    if request.method == 'POST':
        try:
            qty = max(1, min(20, int(request.POST.get('quantity', 1))))
        except ValueError:
            qty = 1

    item, created = CartItem.objects.get_or_create(cart=cart_obj, meal=meal)
    if not created:
        item.quantity = min(20, item.quantity + qty)
    else:
        item.quantity = qty
    item.save()

    messages.success(request, f"Added {meal.name} to your tiffin cart.")
    
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('customer:cart')


def cart_update(request, item_id):
    """Increase, decrease, or update quantity of an item in the cart."""
    if request.method == 'POST':
        cart_obj = get_or_create_cart(request)
        item = get_object_or_404(CartItem, pk=item_id, cart=cart_obj)
        action = request.POST.get('action')

        if action == 'increment':
            item.quantity = min(20, item.quantity + 1)
            item.save()
        elif action == 'decrement':
            if item.quantity > 1:
                item.quantity -= 1
                item.save()
            else:
                item.delete()
                messages.info(request, f"Removed {item.meal.name} from cart.")
        elif action == 'set':
            try:
                new_qty = int(request.POST.get('quantity', 1))
                if new_qty <= 0:
                    item.delete()
                else:
                    item.quantity = min(20, new_qty)
                    item.save()
            except ValueError:
                pass

    return redirect('customer:cart')


def cart_remove(request, item_id):
    """Remove a specific item from the cart."""
    if request.method == 'POST':
        cart_obj = get_or_create_cart(request)
        item = get_object_or_404(CartItem, pk=item_id, cart=cart_obj)
        meal_name = item.meal.name
        item.delete()
        messages.success(request, f"Removed {meal_name} from your cart.")
    return redirect('customer:cart')


def cart_clear(request):
    """Clears all items from the current cart."""
    if request.method == 'POST':
        cart_obj = get_or_create_cart(request)
        cart_obj.items.all().delete()
        cart_obj.coupon = None
        cart_obj.save()
        messages.info(request, "Your cart has been cleared.")
    return redirect('customer:cart')


def cart_apply_coupon(request):
    """Apply a discount coupon to the cart."""
    if request.method == 'POST':
        code = request.POST.get('coupon_code', '').strip().upper()
        next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
        redirect_target = next_url if next_url and next_url.startswith('/') else 'customer:cart'
        cart_obj = get_or_create_cart(request)

        if not code:
            messages.error(request, "Please enter a valid promo code.")
            return redirect(redirect_target)

        coupon = Coupon.objects.filter(code=code, is_active=True).first()
        if not coupon:
            messages.error(request, f"Coupon code '{code}' is invalid or expired.")
            return redirect(redirect_target)

        valid, msg = coupon.is_valid_for(cart_obj.subtotal)
        if not valid:
            messages.error(request, msg)
            return redirect(redirect_target)

        cart_obj.coupon = coupon
        cart_obj.save()
        messages.success(request, f"{coupon.code} applied successfully!")
        return redirect(redirect_target)
    return redirect('customer:cart')


def cart_remove_coupon(request):
    """Remove active coupon from the cart."""
    if request.method == 'POST':
        cart_obj = get_or_create_cart(request)
        cart_obj.coupon = None
        cart_obj.save()
        messages.info(request, "Coupon removed.")
        next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
        if next_url and next_url.startswith('/'):
            return redirect(next_url)
    return redirect('customer:cart')


def _extract_delivery_address(request, recipient_name, recipient_phone):
    """Helper to extract and format delivery address from checkout request."""
    delivery_notes = request.POST.get('delivery_notes', '').strip()
    addr_choice = request.POST.get('address_choice')
    delivery_address_text = ""

    if addr_choice and addr_choice.isdigit():
        addr = DeliveryAddress.objects.filter(pk=int(addr_choice), user=request.user).first()
        if addr:
            delivery_address_text = addr.formatted
            if addr.delivery_notes and not delivery_notes:
                delivery_notes = addr.delivery_notes

    if not delivery_address_text:
        street = request.POST.get('street_address', '').strip()
        area = request.POST.get('area', '').strip()
        city = request.POST.get('city', 'Bengaluru').strip()
        pincode = request.POST.get('pincode', '').strip()
        if not street or not pincode:
            return None, delivery_notes, "Please select an existing address or enter complete address details (Street & Pincode required)."
        delivery_address_text = f"{street}, {area}, {city} - {pincode}" if area else f"{street}, {city} - {pincode}"

        save_addr = request.POST.get('save_address')
        if save_addr in ('on', 'true', True):
            DeliveryAddress.objects.create(
                user=request.user,
                title='Saved Delivery Address',
                recipient_name=recipient_name,
                phone_number=recipient_phone,
                street_address=street,
                area=area,
                city=city,
                pincode=pincode,
                delivery_notes=delivery_notes
            )

    return delivery_address_text, delivery_notes, None


def _process_cart_order(user, cart_obj, items, recipient_name, recipient_phone, delivery_address_text, delivery_notes, payment_method, payment_status, payment_transaction_id):
    """Helper to atomize order creation, items copy, cart clearance, and chef notification."""
    primary_chef = items.first().meal.chef
    subtotal = cart_obj.subtotal
    delivery_fee = cart_obj.delivery_fee
    tax_amount = cart_obj.tax_amount
    discount_amount = cart_obj.discount_amount
    final_amount = cart_obj.final_total

    with transaction.atomic():
        order = Order.objects.create(
            user=user,
            chef=primary_chef,
            recipient_name=recipient_name,
            recipient_phone=recipient_phone,
            delivery_address_text=delivery_address_text,
            delivery_notes=delivery_notes,
            status='pending',
            total_amount=subtotal,
            delivery_fee=delivery_fee,
            tax_amount=tax_amount,
            discount_amount=discount_amount,
            final_amount=final_amount,
            payment_method=payment_method,
            payment_status=payment_status,
            payment_transaction_id=payment_transaction_id,
        )

        for item in items:
            OrderItem.objects.create(
                order=order,
                meal=item.meal,
                meal_name=item.meal.name,
                unit_price=item.meal.price,
                quantity=item.quantity,
                subtotal=item.subtotal
            )

        # Increment coupon usage if applied
        if cart_obj.coupon:
            Coupon.objects.filter(pk=cart_obj.coupon.pk).update(times_used=F('times_used') + 1)

        # Clear cart
        cart_obj.items.all().delete()
        cart_obj.coupon = None
        cart_obj.save()

        # Notify Chef
        ChefNotification.objects.create(
            chef=primary_chef,
            title="New Incoming Food Order",
            message=f"Order #{order.order_number} received from {recipient_name} ({items.count()} dishes). Total: ₹{final_amount}.",
            notification_type='order',
            link=f"/chef/orders/{order.id}/"
        )

        # Send Order Confirmation Email to Customer & Store Owner
        try:
            from .emails import send_order_confirmation_email
            send_order_confirmation_email(order, async_send=True)
        except Exception as _em_err:
            pass

    return order


@login_required
def checkout(request):
    """Complete checkout flow with address selection, calculations, and order creation."""
    cart_obj = get_or_create_cart(request)
    items = cart_obj.items.select_related('meal', 'meal__chef').all()

    if not items.exists():
        messages.warning(request, "Your cart is empty. Add fresh meals before checkout!")
        return redirect('customer:menu')

    # Verify meals availability
    unavailable = [item.meal.name for item in items if not item.meal.is_available]
    if unavailable:
        messages.error(request, f"Some items are currently unavailable: {', '.join(unavailable)}. Please remove them to proceed.")
        return redirect('customer:cart')

    user_addresses = request.user.addresses.all()
    default_address = user_addresses.filter(is_default=True).first() or user_addresses.first()
    available_coupons = Coupon.get_available_coupons()

    if request.method == 'POST':
        payment_method = request.POST.get('payment_method', '').strip()

        # Strict check: Online payment orders CANNOT be placed without Razorpay verification.
        if payment_method != 'cod':
            messages.error(request, "Online payment complete hone ke baad hi order confirm hota hai. Kripya Razorpay gateway se payment karein.")
            return redirect('customer:checkout')

        recipient_name = request.POST.get('recipient_name', '').strip()
        recipient_phone = request.POST.get('recipient_phone', '').strip()

        if not recipient_name or not recipient_phone:
            messages.error(request, "Recipient name and phone number are required.")
            return render(request, 'customer/checkout.html', {
                'cart': cart_obj,
                'items': items,
                'user_addresses': user_addresses,
                'default_address': default_address,
                'available_coupons': available_coupons,
                'razorpay_key_id': getattr(settings, 'RAZORPAY_KEY_ID', '')
            })

        delivery_address_text, delivery_notes, err = _extract_delivery_address(request, recipient_name, recipient_phone)
        if err:
            messages.error(request, err)
            return render(request, 'customer/checkout.html', {
                'cart': cart_obj,
                'items': items,
                'user_addresses': user_addresses,
                'default_address': default_address,
                'available_coupons': available_coupons,
                'razorpay_key_id': getattr(settings, 'RAZORPAY_KEY_ID', '')
            })

        # COD flow
        order = _process_cart_order(
            user=request.user,
            cart_obj=cart_obj,
            items=items,
            recipient_name=recipient_name,
            recipient_phone=recipient_phone,
            delivery_address_text=delivery_address_text,
            delivery_notes=delivery_notes,
            payment_method='cod',
            payment_status='pending',
            payment_transaction_id='',
        )

        messages.success(request, f"Cash on Delivery order #{order.order_number} placed successfully!")
        return redirect('customer:order_confirmation', pk=order.pk)

    context = {
        'cart': cart_obj,
        'items': items,
        'user_addresses': user_addresses,
        'default_address': default_address,
        'available_coupons': available_coupons,
        'razorpay_key_id': getattr(settings, 'RAZORPAY_KEY_ID', ''),
    }
    return render(request, 'customer/checkout.html', context)


@login_required
def razorpay_order_create(request):
    """Generates a Razorpay Order ID for online checkout."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)

    cart_obj = get_or_create_cart(request)
    items = cart_obj.items.select_related('meal').all()

    if not items.exists():
        return JsonResponse({'status': 'error', 'message': 'Your cart is empty. Please add items.'}, status=400)

    unavailable = [item.meal.name for item in items if not item.meal.is_available]
    if unavailable:
        return JsonResponse({
            'status': 'error',
            'message': f"Some items are unavailable: {', '.join(unavailable)}."
        }, status=400)

    amount_paise = int(round(cart_obj.final_total * Decimal('100.00')))
    if amount_paise <= 0:
        return JsonResponse({'status': 'error', 'message': 'Invalid order amount.'}, status=400)

    recipient_name = request.POST.get('recipient_name', '').strip() or request.user.get_full_name() or request.user.username
    recipient_phone = request.POST.get('recipient_phone', '').strip()
    if not recipient_phone and hasattr(request.user, 'customer_profile'):
        recipient_phone = getattr(request.user.customer_profile, 'phone', '')

    key_id = getattr(settings, 'RAZORPAY_KEY_ID', '')
    key_secret = getattr(settings, 'RAZORPAY_KEY_SECRET', '')

    if not key_id or not key_secret:
        return JsonResponse({'status': 'error', 'message': 'Razorpay payment keys are not configured.'}, status=500)

    try:
        client = razorpay.Client(auth=(key_id, key_secret))
        razorpay_order = client.order.create({
            'amount': amount_paise,
            'currency': 'INR',
            'payment_capture': 1,
            'notes': {
                'user_id': str(request.user.id),
                'username': request.user.username,
                'cart_id': str(cart_obj.id),
                'recipient_name': recipient_name[:40],
            }
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Razorpay order creation failed: {str(e)}'}, status=500)

    return JsonResponse({
        'status': 'success',
        'key_id': key_id,
        'razorpay_order_id': razorpay_order['id'],
        'amount': razorpay_order['amount'],
        'currency': razorpay_order.get('currency', 'INR'),
        'customer_name': recipient_name,
        'customer_email': request.user.email or '',
        'customer_phone': recipient_phone,
    })


@login_required
def razorpay_payment_verify(request):
    """Verifies Razorpay payment signature and confirms order."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)

    razorpay_payment_id = request.POST.get('razorpay_payment_id', '').strip()
    razorpay_order_id = request.POST.get('razorpay_order_id', '').strip()
    razorpay_signature = request.POST.get('razorpay_signature', '').strip()

    if not razorpay_payment_id or not razorpay_order_id or not razorpay_signature:
        return JsonResponse({'status': 'error', 'message': 'Missing payment signature credentials.'}, status=400)

    key_id = getattr(settings, 'RAZORPAY_KEY_ID', '')
    key_secret = getattr(settings, 'RAZORPAY_KEY_SECRET', '')

    try:
        client = razorpay.Client(auth=(key_id, key_secret))
        client.utility.verify_payment_signature({
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature,
        })
    except razorpay.errors.SignatureVerificationError:
        return JsonResponse({'status': 'error', 'message': 'Payment verification failed: Invalid Razorpay signature.'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Verification error: {str(e)}'}, status=400)

    cart_obj = get_or_create_cart(request)
    items = cart_obj.items.select_related('meal', 'meal__chef').all()

    if not items.exists():
        return JsonResponse({'status': 'error', 'message': 'Cart is empty or already processed.'}, status=400)

    recipient_name = request.POST.get('recipient_name', '').strip()
    recipient_phone = request.POST.get('recipient_phone', '').strip()

    if not recipient_name or not recipient_phone:
        return JsonResponse({'status': 'error', 'message': 'Recipient name and phone are required.'}, status=400)

    delivery_address_text, delivery_notes, err = _extract_delivery_address(request, recipient_name, recipient_phone)
    if err:
        return JsonResponse({'status': 'error', 'message': err}, status=400)

    order = _process_cart_order(
        user=request.user,
        cart_obj=cart_obj,
        items=items,
        recipient_name=recipient_name,
        recipient_phone=recipient_phone,
        delivery_address_text=delivery_address_text,
        delivery_notes=delivery_notes,
        payment_method='online',
        payment_status='paid',
        payment_transaction_id=razorpay_payment_id,
    )

    messages.success(request, f"Online payment verified! Order #{order.order_number} confirmed.")
    return JsonResponse({
        'status': 'success',
        'order_id': order.pk,
        'order_number': order.order_number,
        'redirect_url': reverse('customer:order_confirmation', kwargs={'pk': order.pk}),
    })


@login_required
def order_confirmation(request, pk):
    """Order confirmation and receipt summary page."""
    order = get_object_or_404(Order, pk=pk, user=request.user)
    context = {
        'order': order,
    }
    return render(request, 'customer/order_confirmation.html', context)


@login_required
def order_history(request):
    """Customer's order history page."""
    orders = Order.objects.filter(user=request.user).select_related('chef').prefetch_related('items').order_by('-created_at')
    
    paginator = Paginator(orders, 8)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'orders': page_obj.object_list,
        'page_obj': page_obj,
    }
    return render(request, 'customer/order_history.html', context)


@login_required
def order_detail(request, pk):
    """Detailed order view with tracking timeline, items, and cancellation options."""
    order = get_object_or_404(Order.objects.select_related('chef', 'chef__user'), pk=pk, user=request.user)

    if request.GET.get('format') == 'json' or request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'success',
            'order_id': order.id,
            'order_number': order.order_number,
            'order_status': order.status,
            'status_display': order.get_status_display(),
            'progress_step': order.progress_step,
            'cancellation_reason': order.cancellation_reason,
            'updated_at': order.updated_at.strftime('%I:%M %p, %b %d'),
            'can_cancel': order.can_cancel,
            'chef_name': order.chef.business_name,
        })

    items = order.items.select_related('meal')
    review = order.customer_review
    context = {
        'order': order,
        'items': items,
        'review': review,
    }
    return render(request, 'customer/order_detail.html', context)


@login_required
def submit_order_feedback(request, pk):
    """Submit or update feedback/rating for a completed (delivered) order."""
    order = get_object_or_404(Order, pk=pk, user=request.user)

    if order.status != 'delivered':
        messages.error(request, "Feedback can only be submitted after your order has been delivered.")
        return redirect('customer:order_detail', pk=order.pk)

    if request.method == 'POST':
        try:
            rating = int(request.POST.get('rating', 5))
        except (ValueError, TypeError):
            rating = 5
        rating = max(1, min(5, rating))

        comment = request.POST.get('comment', '').strip()
        if not comment:
            messages.error(request, "Please enter a short comment about your meal experience.")
            return redirect(f"{reverse('customer:order_detail', kwargs={'pk': order.pk})}#feedback")

        meal_id = request.POST.get('meal_id')
        meal = None
        if meal_id:
            meal = Meal.objects.filter(pk=meal_id).first()

        review, created = Review.objects.update_or_create(
            order=order,
            user=request.user,
            defaults={
                'chef': order.chef,
                'meal': meal,
                'rating': rating,
                'comment': comment,
            }
        )

        customer_name = request.user.get_full_name() or request.user.username
        comment_snippet = comment[:60]
        ChefNotification.objects.create(
            chef=order.chef,
            title="New Order Feedback Received",
            message=f"{customer_name} rated Order #{order.order_number}: {rating}★ (\"{comment_snippet}...\")",
            notification_type='review',
            link="/chef/reviews/"
        )

        msg = f"Thank you! Your feedback for Order #{order.order_number} has been recorded." if created else "Your feedback has been updated."
        messages.success(request, msg)

    return redirect(f"{reverse('customer:order_detail', kwargs={'pk': order.pk})}#feedback")


@login_required
def order_cancel(request, pk):
    """Allows customer to cancel pending/confirmed order."""
    order = get_object_or_404(Order, pk=pk, user=request.user)
    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        if order.can_cancel:
            order.status = 'cancelled'
            order.cancellation_reason = reason or "Cancelled by customer."
            order.save(update_fields=['status', 'cancellation_reason'])

            ChefNotification.objects.create(
                chef=order.chef,
                title="Order Cancelled by Customer",
                message=f"Order #{order.order_number} was cancelled by {order.recipient_name}. Reason: {order.cancellation_reason}",
                notification_type='order_cancel',
                link=f"/chef/orders/{order.id}/"
            )

            messages.success(request, f"Order #{order.order_number} has been cancelled.")
        else:
            messages.error(request, "This order has already been prepared or dispatched and cannot be cancelled.")
    return redirect('customer:order_detail', pk=order.pk)


@login_required
def order_reorder(request, pk):
    """Reorder available meals from a past order into the cart."""
    order = get_object_or_404(Order, pk=pk, user=request.user)
    cart_obj = get_or_create_cart(request)

    added_count = 0
    for item in order.items.select_related('meal'):
        if item.meal and item.meal.is_available:
            cart_item, created = CartItem.objects.get_or_create(cart=cart_obj, meal=item.meal)
            if not created:
                cart_item.quantity += item.quantity
            else:
                cart_item.quantity = item.quantity
            cart_item.save()
            added_count += 1

    if added_count > 0:
        messages.success(request, f"Re-added {added_count} items from order #{order.order_number} to your cart.")
    else:
        messages.warning(request, "The meals from this order are currently unavailable.")

    return redirect('customer:cart')


@login_required
def reviews_view(request):
    """List customer reviews and show option to rate past chefs/meals."""
    user_reviews = Review.objects.filter(user=request.user).select_related('chef', 'meal').order_by('-created_at')

    # Eligible chefs from completed orders/subscriptions
    order_chefs = ChefProfile.objects.filter(orders__user=request.user).distinct()
    sub_chefs = ChefProfile.objects.filter(subscriptions__user=request.user).distinct()
    reviewed_chef_ids = user_reviews.values_list('chef_id', flat=True)

    eligible_chefs = (order_chefs | sub_chefs).exclude(id__in=reviewed_chef_ids).distinct()

    context = {
        'user_reviews': user_reviews,
        'eligible_chefs': eligible_chefs,
    }
    return render(request, 'customer/reviews.html', context)


@login_required
def add_review(request):
    """Submit a rating and review for a chef or meal."""
    if request.method == 'POST':
        chef_id = request.POST.get('chef_id')
        meal_id = request.POST.get('meal_id')
        rating = int(request.POST.get('rating', 5))
        comment = request.POST.get('comment', '').strip()

        chef = get_object_or_404(ChefProfile, pk=chef_id)
        meal = Meal.objects.filter(pk=meal_id).first() if meal_id else None

        if not comment:
            messages.error(request, "Please enter a comment for your review.")
            return redirect(request.POST.get('next') or 'customer:reviews')

        review, created = Review.objects.update_or_create(
            user=request.user,
            chef=chef,
            meal=meal,
            defaults={'rating': rating, 'comment': comment}
        )

        ChefNotification.objects.create(
            chef=chef,
            title="New Customer Review",
            message=f"{request.user.get_full_name() or request.user.username} rated your kitchen {rating} stars: \"{comment[:80]}...\"",
            notification_type='review',
            link="/chef/feedback/"
        )

        msg = "Thank you! Your review has been published." if created else "Your review has been updated."
        messages.success(request, msg)

    return redirect(request.POST.get('next') or 'customer:reviews')


@login_required
def delete_review(request, pk):
    """Deletes a customer's own review."""
    review = get_object_or_404(Review, pk=pk, user=request.user)
    if request.method == 'POST':
        chef_name = review.chef.business_name
        review.delete()
        messages.success(request, f"Review for {chef_name} removed.")
    return redirect('customer:reviews')


@login_required
def profile_view(request):
    """Customer profile dashboard with contact info, saved addresses, and active activity."""
    profile, _ = CustomerProfile.objects.get_or_create(user=request.user)
    addresses = request.user.addresses.all()
    recent_orders = request.user.orders.select_related('chef')[:4]
    active_subs = request.user.subscriptions.filter(status='active').select_related('chef', 'plan')

    context = {
        'profile': profile,
        'addresses': addresses,
        'recent_orders': recent_orders,
        'active_subs': active_subs,
    }
    return render(request, 'customer/profile.html', context)


@login_required
def edit_profile(request):
    """Edit customer profile details (name, email, phone, avatar)."""
    profile, _ = CustomerProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = CustomerProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('customer:profile')
    else:
        form = CustomerProfileForm(instance=profile)

    return render(request, 'customer/edit_profile.html', {'form': form, 'profile': profile})


@login_required
def change_password(request):
    """Allow customer to safely change their password."""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Your password was successfully updated!")
            return redirect('customer:profile')
        else:
            messages.error(request, "Please correct the error below.")
    else:
        form = PasswordChangeForm(request.user)

    return render(request, 'customer/change_password.html', {'form': form})


@login_required
def add_address(request):
    """Add a new delivery address."""
    if request.method == 'POST':
        form = DeliveryAddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.save()
            messages.success(request, f"Address '{address.title}' saved successfully.")
            return redirect('customer:profile')
    else:
        form = DeliveryAddressForm()

    return render(request, 'customer/address_form.html', {'form': form, 'title': 'Add New Address'})


@login_required
def edit_address(request, pk):
    """Edit an existing delivery address with ownership verification."""
    address = get_object_or_404(DeliveryAddress, pk=pk, user=request.user)

    if request.method == 'POST':
        form = DeliveryAddressForm(request.POST, instance=address)
        if form.is_valid():
            form.save()
            messages.success(request, f"Address '{address.title}' updated.")
            return redirect('customer:profile')
    else:
        form = DeliveryAddressForm(instance=address)

    return render(request, 'customer/address_form.html', {'form': form, 'title': 'Edit Address', 'address': address})


@login_required
def delete_address(request, pk):
    """Delete a saved delivery address."""
    address = get_object_or_404(DeliveryAddress, pk=pk, user=request.user)
    if request.method == 'POST':
        title = address.title
        address.delete()
        messages.success(request, f"Address '{title}' deleted.")
    return redirect('customer:profile')


def customer_login(request):
    """Customer login view with next redirect and session cart migration."""
    if request.user.is_authenticated:
        return redirect('customer:home')

    next_url = request.GET.get('next') or request.POST.get('next') or reverse('customer:home')

    if request.method == 'POST':
        username_or_email = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        user = None
        if '@' in username_or_email:
            matched_user = User.objects.filter(email__iexact=username_or_email).first()
            if matched_user:
                user = authenticate(request, username=matched_user.username, password=password)
        else:
            user = authenticate(request, username=username_or_email, password=password)

        if user is not None:
            login(request, user)
            # Migrate guest cart
            get_or_create_cart(request)
            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            return HttpResponseRedirect(next_url)
        else:
            messages.error(request, "Invalid username/email or password.")

    return render(request, 'customer/login.html', {'next': next_url})


def customer_register(request):
    """Customer registration view with auto-login and cart migration."""
    if request.user.is_authenticated:
        return redirect('customer:home')

    if request.method == 'POST':
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            try:
                from .emails import send_customer_welcome_email
                send_customer_welcome_email(user, async_send=True)
            except Exception as exc:
                print(f"[EMAIL ERROR] Customer welcome email failed: {exc}")
            login(request, user)
            # Migrate guest cart
            get_or_create_cart(request)
            messages.success(request, f"Welcome to TiffinTrail, {user.first_name}! Your account has been created.")
            return redirect('customer:home')
    else:
        form = CustomerRegistrationForm()

    return render(request, 'customer/register.html', {'form': form})


def customer_logout(request):
    """Logs out the customer."""
    logout(request)
    messages.info(request, "You have been logged out safely.")
    return redirect('customer:home')


def about(request):
    """About TiffinTrail page."""
    return render(request, 'customer/about.html')


def contact(request):
    """Contact page with message feedback."""
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        messages.success(request, f"Thank you {name}! Your message has been received. Our team will contact you at {email} within 24 hours.")
        return redirect('customer:contact')
    return render(request, 'customer/contact.html')



def mask_email(email):
    """Helper to mask email e.g. dharmesh@gmail.com -> dha***@gmail.com"""
    if not email or '@' not in email:
        return email
    try:
        parts = email.split('@')
        name, domain = parts[0], parts[1]
        if len(name) <= 2:
            masked = name[0] + '*'
        elif len(name) <= 4:
            masked = name[:2] + '*' * (len(name) - 2)
        else:
            masked = name[:3] + '*' * (len(name) - 3)
        return f"{masked}@{domain}"
    except Exception:
        return email


def forgot_password(request):
    """Customer forgot password request view (sends 6-digit OTP)."""
    if request.user.is_authenticated:
        return redirect('customer:home')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        if not email:
            messages.error(request, "Please enter a valid email address.")
            return render(request, 'customer/forgot_password.html')

        from django.contrib.auth import get_user_model
        import secrets
        from datetime import timedelta
        from django.utils import timezone
        from .models import PasswordResetOTP
        from .emails import send_password_reset_otp_email

        User = get_user_model()
        user = User.objects.filter(email__iexact=email).first()

        if user:
            otp = f"{secrets.randbelow(1000000):06d}"
            expires_at = timezone.now() + timedelta(minutes=10)

            PasswordResetOTP.objects.filter(
                email__iexact=email,
                user_type='customer',
                is_used=False
            ).update(is_used=True)

            PasswordResetOTP.objects.create(
                user=user,
                email=email,
                otp=otp,
                expires_at=expires_at,
                user_type='customer'
            )

            send_password_reset_otp_email(user, otp, async_send=True)
            request.session['reset_email'] = email
            messages.success(request, f"A 6-digit OTP has been sent to {email}. Please enter it below to set your new password.")
            return redirect('customer:verify_otp')
        else:
            messages.error(request, "No account was found with this email address. Please check your spelling or register.")
            return render(request, 'customer/forgot_password.html', {'email': email})

    return render(request, 'customer/forgot_password.html')


def verify_otp(request):
    """Customer OTP verification and new password setup."""
    email = request.session.get('reset_email', '').strip()

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower() or email
        otp = request.POST.get('otp', '').strip().replace(' ', '')
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if not email:
            messages.error(request, "Please provide your registered email address.")
            return render(request, 'customer/verify_otp.html', {'email': email, 'masked_email': mask_email(email)})

        if not otp:
            messages.error(request, "Please enter the 6-digit OTP sent to your email.")
            return render(request, 'customer/verify_otp.html', {'email': email, 'masked_email': mask_email(email)})

        if len(new_password) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
            return render(request, 'customer/verify_otp.html', {'email': email, 'masked_email': mask_email(email)})

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match. Please re-enter.")
            return render(request, 'customer/verify_otp.html', {'email': email, 'masked_email': mask_email(email)})

        from django.contrib.auth import get_user_model
        from .models import PasswordResetOTP

        User = get_user_model()
        user = User.objects.filter(email__iexact=email).first()

        if not user:
            messages.error(request, "No account found for this email address.")
            return render(request, 'customer/verify_otp.html', {'email': email, 'masked_email': mask_email(email)})

        otp_record = PasswordResetOTP.objects.filter(
            email__iexact=email,
            user_type='customer',
            is_used=False
        ).order_by('-created_at').first()

        if not otp_record or not otp_record.is_valid() or otp_record.otp != otp:
            messages.error(request, "Invalid or expired OTP. Please enter the correct 6-digit code or request a fresh OTP.")
            return render(request, 'customer/verify_otp.html', {'email': email, 'masked_email': mask_email(email)})

        user.set_password(new_password)
        user.save()
        otp_record.is_used = True
        otp_record.save()

        request.session.pop('reset_email', None)
        messages.success(request, "Your password has been reset successfully! You can now sign in with your new password.")
        return redirect('customer:login')

    masked_email = mask_email(email) if email else ''
    return render(request, 'customer/verify_otp.html', {'email': email, 'masked_email': masked_email})


def resend_otp(request):
    """Resend a fresh 6-digit OTP to the customer."""
    email = request.session.get('reset_email', '') or request.GET.get('email', '').strip().lower()
    if not email:
        messages.error(request, "Please enter your email to request an OTP.")
        return redirect('customer:forgot_password')

    from django.contrib.auth import get_user_model
    import secrets
    from datetime import timedelta
    from django.utils import timezone
    from .models import PasswordResetOTP
    from .emails import send_password_reset_otp_email

    User = get_user_model()
    user = User.objects.filter(email__iexact=email).first()

    if user:
        otp = f"{secrets.randbelow(1000000):06d}"
        expires_at = timezone.now() + timedelta(minutes=10)

        PasswordResetOTP.objects.filter(
            email__iexact=email,
            user_type='customer',
            is_used=False
        ).update(is_used=True)

        PasswordResetOTP.objects.create(
            user=user,
            email=email,
            otp=otp,
            expires_at=expires_at,
            user_type='customer'
        )

        send_password_reset_otp_email(user, otp, async_send=True)
        messages.success(request, f"A fresh 6-digit OTP has been sent to {email}.")
    else:
        messages.error(request, "Account not found for this email address.")

    request.session['reset_email'] = email
    return redirect('customer:verify_otp')


def password_reset_confirm(request, uidb64, token):
    """Customer password reset confirmation view."""
    from django.contrib.auth import get_user_model, logout
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.http import urlsafe_base64_decode
    from django.utils.encoding import force_str

    User = get_user_model()
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is None or not default_token_generator.check_token(user, token):
        messages.error(request, "This password reset link is invalid or has expired. Please request a new link.")
        return redirect('customer:forgot_password')

    # If another user is logged in, log them out cleanly so the target user's password can be reset
    if request.user.is_authenticated and request.user.pk != user.pk:
        logout(request)

    if request.method == 'POST':
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if len(new_password) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
        elif new_password != confirm_password:
            messages.error(request, "Passwords do not match. Please re-enter.")
        else:
            user.set_password(new_password)
            user.save()
            messages.success(request, "Your password has been reset successfully! You can now sign in with your new password.")
            return redirect('customer:login')

    return render(request, 'customer/password_reset_confirm.html', {'user': user})
