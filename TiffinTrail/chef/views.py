from datetime import timedelta
from decimal import Decimal
from functools import wraps
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.core.paginator import Paginator
from django.db import models, transaction
from django.db.models import Sum, Count, Q
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone

from customer.models import Order, OrderItem, Subscription, Review, CustomerProfile
from .models import ChefProfile, Meal, MealPlan, MenuCategory, DailyMenu, ChefNotification
from .forms import ChefRegistrationForm, ChefProfileForm, MealForm, MealPlanForm, DailyMenuForm, MenuCategoryForm


def chef_required(view_func):
    """
    Ensures the user is authenticated and is an active/approved chef.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, "Please log in to access the Chef Studio.")
            return redirect(f"{reverse('chef:login')}?next={request.path}")
        
        if not hasattr(request.user, 'chef_profile'):
            messages.error(request, "Access restricted. You do not have a registered Chef account.")
            return redirect('customer:home')

        chef = request.user.chef_profile
        if not chef.is_active:
            messages.error(request, "Your chef account has been deactivated. Please contact support.")
            return redirect('customer:home')

        return view_func(request, *args, **kwargs)
    return _wrapped_view


def chef_login(request):
    if request.user.is_authenticated:
        if hasattr(request.user, 'chef_profile'):
            return redirect('chef:dashboard')
        return redirect('customer:home')

    next_url = request.GET.get('next') or request.POST.get('next') or reverse('chef:dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            if hasattr(user, 'chef_profile'):
                login(request, user)
                messages.success(request, f"Welcome back, Chef {user.chef_profile.business_name}!")
                return redirect(next_url)
            else:
                messages.error(request, "Account found, but it is not registered as a Chef profile.")
        else:
            messages.error(request, "Invalid username or password. Please try again.")

    return render(request, 'chef/login.html', {'next': next_url})


def chef_logout(request):
    logout(request)
    messages.info(request, "You have been logged out of the Chef Studio.")
    return redirect('customer:home')


def chef_register(request):
    if request.user.is_authenticated:
        if hasattr(request.user, 'chef_profile'):
            return redirect('chef:dashboard')
        return redirect('customer:home')

    if request.method == 'POST':
        form = ChefRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            try:
                from customer.emails import send_chef_welcome_email
                send_chef_welcome_email(user.chef_profile, async_send=True)
            except Exception as exc:
                print(f"[EMAIL ERROR] Chef welcome email failed: {exc}")
            login(request, user)
            messages.success(
                request,
                f"Welcome to TiffinTrail, Chef {user.chef_profile.business_name}! Your kitchen profile has been created and submitted for verification."
            )
            return redirect('chef:dashboard')
        else:
            messages.error(request, "Please correct the errors below to register your kitchen.")
    else:
        form = ChefRegistrationForm()

    return render(request, 'chef/register.html', {'form': form})


@chef_required
def dashboard(request):
    chef = request.user.chef_profile
    today = timezone.now().date()

    date_filter = request.GET.get('range', '7days')
    orders_qs = Order.objects.filter(chef=chef)

    if date_filter == 'today':
        filtered_orders = orders_qs.filter(created_at__date=today)
    elif date_filter == '7days':
        filtered_orders = orders_qs.filter(created_at__date__gte=today - timedelta(days=7))
    elif date_filter == 'month':
        filtered_orders = orders_qs.filter(created_at__date__gte=today - timedelta(days=30))
    else:
        filtered_orders = orders_qs

    # Core Metrics
    total_orders_count = orders_qs.count()
    pending_orders_count = orders_qs.filter(status='pending').count()
    preparing_orders_count = orders_qs.filter(status__in=['confirmed', 'preparing']).count()
    completed_orders_count = orders_qs.filter(status='delivered').count()
    cancelled_orders_count = orders_qs.filter(status='cancelled').count()
    active_subscriptions_count = Subscription.objects.filter(chef=chef, status='active').count()
    total_meals_count = Meal.objects.filter(chef=chef).count()

    # Revenue & Commission calculations
    # Completed orders represent fulfilled and recognized sales
    delivered_orders = orders_qs.filter(status='delivered')
    gross_revenue = delivered_orders.aggregate(Sum('final_amount'))['final_amount__sum'] or Decimal('0.00')
    gross_revenue = round(Decimal(str(gross_revenue)), 2)
    commission_rate = chef.commission_rate
    platform_commission = round((gross_revenue * commission_rate) / Decimal('100.00'), 2)
    net_earnings = round(gross_revenue - platform_commission, 2)

    # Filtered metrics for current selected view
    filter_gross = filtered_orders.filter(status='delivered').aggregate(Sum('final_amount'))['final_amount__sum'] or Decimal('0.00')
    filter_gross = round(Decimal(str(filter_gross)), 2)
    filter_commission = round((filter_gross * commission_rate) / Decimal('100.00'), 2)
    filter_net = round(filter_gross - filter_commission, 2)

    # Recent Orders (last 6)
    recent_orders = orders_qs.select_related('user').prefetch_related('items')[:6]

    # Active Subscriptions snapshot
    recent_subscriptions = Subscription.objects.filter(chef=chef).select_related('user', 'plan')[:5]

    # Today's Scheduled Daily Menus
    today_menus = DailyMenu.objects.filter(chef=chef, date=today).select_related('meal')

    # Popular Dishes (Top 5 ordered items)
    popular_items = (
        OrderItem.objects.filter(order__chef=chef)
        .values('meal_name')
        .annotate(total_ordered=Sum('quantity'), total_sales=Sum('subtotal'))
        .order_by('-total_ordered')[:5]
    )

    # 7-day trend data for offline visualization
    days_data = []
    max_day_val = Decimal('1.00')
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        day_orders = orders_qs.filter(created_at__date=d)
        cnt = day_orders.count()
        rev = day_orders.filter(status='delivered').aggregate(Sum('final_amount'))['final_amount__sum'] or Decimal('0.00')
        if rev > max_day_val:
            max_day_val = rev
        days_data.append({
            'date': d.strftime('%a, %d %b'),
            'short_date': d.strftime('%d %b'),
            'orders': cnt,
            'revenue': float(rev),
        })

    # Status distribution for donut/bar display
    status_distribution = [
        {'label': 'Pending', 'count': pending_orders_count, 'color': '#f59e0b', 'code': 'pending'},
        {'label': 'In Prep', 'count': preparing_orders_count, 'color': '#3b82f6', 'code': 'preparing'},
        {'label': 'Delivered', 'count': completed_orders_count, 'color': '#10b981', 'code': 'delivered'},
        {'label': 'Cancelled', 'count': cancelled_orders_count, 'color': '#ef4444', 'code': 'cancelled'},
    ]

    context = {
        'chef': chef,
        'date_filter': date_filter,
        'total_orders_count': total_orders_count,
        'pending_orders_count': pending_orders_count,
        'preparing_orders_count': preparing_orders_count,
        'completed_orders_count': completed_orders_count,
        'active_subscriptions_count': active_subscriptions_count,
        'total_meals_count': total_meals_count,
        'gross_revenue': gross_revenue,
        'platform_commission': platform_commission,
        'net_earnings': net_earnings,
        'filter_gross': filter_gross,
        'filter_net': filter_net,
        'recent_orders': recent_orders,
        'recent_subscriptions': recent_subscriptions,
        'today_menus': today_menus,
        'popular_items': popular_items,
        'days_data': days_data,
        'status_distribution': status_distribution,
        'today': today,
    }
    return render(request, 'chef/dashboard.html', context)


@chef_required
def profile_view(request):
    chef = request.user.chef_profile
    return render(request, 'chef/profile.html', {'chef': chef})


@chef_required
def profile_edit(request):
    chef = request.user.chef_profile

    if request.method == 'POST':
        form = ChefProfileForm(request.POST, request.FILES, instance=chef)
        if form.is_valid():
            form.save(commit=True)
            messages.success(request, "Your chef profile has been updated successfully!")
            return redirect('chef:profile')
        else:
            messages.error(request, "Please correct the errors in the form below.")
    else:
        form = ChefProfileForm(instance=chef)

    return render(request, 'chef/profile_edit.html', {'form': form, 'chef': chef})


@chef_required
def chef_upload_images(request):
    chef = request.user.chef_profile
    if request.method == 'POST':
        updated = False
        if 'cover_image' in request.FILES:
            chef.cover_image = request.FILES['cover_image']
            updated = True
        if 'profile_image' in request.FILES:
            chef.profile_image = request.FILES['profile_image']
            updated = True
        if updated:
            chef.save()
            messages.success(request, "Kitchen branding images updated successfully!")
        else:
            messages.warning(request, "Please select an image file to upload.")
    return redirect('chef:profile')



@chef_required
def meal_list(request):
    chef = request.user.chef_profile
    meals = Meal.objects.filter(chef=chef).select_related('category')

    # Filtering
    category_slug = request.GET.get('category')
    meal_type = request.GET.get('meal_type')
    diet = request.GET.get('diet')
    query = request.GET.get('q', '').strip()

    if category_slug:
        meals = meals.filter(category__slug=category_slug)
    if meal_type:
        meals = meals.filter(meal_type=meal_type)
    if diet == 'veg':
        meals = meals.filter(is_veg=True)
    elif diet == 'non_veg':
        meals = meals.filter(is_veg=False)
    if query:
        meals = meals.filter(Q(name__icontains=query) | Q(description__icontains=query))

    categories = MenuCategory.objects.all()

    return render(request, 'chef/meal_list.html', {
        'chef': chef,
        'meals': meals,
        'categories': categories,
        'selected_category': category_slug,
        'selected_meal_type': meal_type,
        'selected_diet': diet,
        'search_query': query,
    })


@chef_required
def meal_add(request):
    chef = request.user.chef_profile

    if request.method == 'POST':
        form = MealForm(request.POST, request.FILES)
        if form.is_valid():
            meal = form.save(commit=False)
            meal.chef = chef
            meal.save()
            messages.success(request, f"Meal '{meal.name}' added to your kitchen menu!")
            return redirect('chef:meals')
        else:
            messages.error(request, "Failed to add meal. Please check form inputs.")
    else:
        form = MealForm()

    return render(request, 'chef/meal_form.html', {
        'form': form,
        'title': 'Add New Homestyle Meal',
        'is_edit': False,
    })


@chef_required
def meal_edit(request, meal_id):
    chef = request.user.chef_profile
    meal = get_object_or_404(Meal, id=meal_id, chef=chef)

    if request.method == 'POST':
        form = MealForm(request.POST, request.FILES, instance=meal)
        if form.is_valid():
            form.save()
            messages.success(request, f"Meal '{meal.name}' updated successfully.")
            return redirect('chef:meals')
        else:
            messages.error(request, "Failed to update meal. Please check the errors.")
    else:
        form = MealForm(instance=meal)

    return render(request, 'chef/meal_form.html', {
        'form': form,
        'meal': meal,
        'title': f"Edit Meal: {meal.name}",
        'is_edit': True,
    })


@chef_required
def meal_delete(request, meal_id):
    chef = request.user.chef_profile
    meal = get_object_or_404(Meal, id=meal_id, chef=chef)

    if request.method == 'POST':
        name = meal.name
        meal.delete()
        messages.success(request, f"Meal '{name}' was deleted successfully.")
        return redirect('chef:meals')

    return render(request, 'chef/meal_confirm_delete.html', {'meal': meal})


@chef_required
def meal_toggle(request, meal_id):
    chef = request.user.chef_profile
    meal = get_object_or_404(Meal, id=meal_id, chef=chef)
    meal.is_available = not meal.is_available
    meal.save()
    status_str = "Available" if meal.is_available else "Unavailable"
    messages.success(request, f"Meal '{meal.name}' is now marked as {status_str}.")
    return redirect(request.META.get('HTTP_REFERER') or 'chef:meals')


@chef_required
def category_list(request):
    chef = request.user.chef_profile
    categories = MenuCategory.objects.annotate(meals_count=Count('meals', filter=Q(meals__chef=chef)))

    if request.method == 'POST':
        form = MenuCategoryForm(request.POST)
        if form.is_valid():
            cat = form.save()
            messages.success(request, f"Category '{cat.name}' created.")
            return redirect('chef:categories')
        else:
            messages.error(request, "Could not create category. Please check form values.")
    else:
        form = MenuCategoryForm()

    return render(request, 'chef/category_list.html', {
        'chef': chef,
        'categories': categories,
        'form': form,
    })


@chef_required
def daily_menu_view(request):
    chef = request.user.chef_profile
    today = timezone.now().date()

    # Selected date
    date_str = request.GET.get('date')
    if date_str:
        try:
            selected_date = timezone.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            selected_date = today
    else:
        selected_date = today

    scheduled_menus = DailyMenu.objects.filter(chef=chef, date=selected_date).select_related('meal')
    chef_meals = Meal.objects.filter(chef=chef, is_available=True)

    # Next 7 days schedule preview
    next_7_days = []
    for i in range(7):
        d = today + timedelta(days=i)
        count = DailyMenu.objects.filter(chef=chef, date=d, is_available=True).count()
        next_7_days.append({
            'date': d,
            'is_selected': d == selected_date,
            'day_name': d.strftime('%a'),
            'date_str': d.strftime('%d %b'),
            'iso_date': d.strftime('%Y-%m-%d'),
            'count': count,
        })

    form = DailyMenuForm(chef=chef, initial={'date': selected_date})

    return render(request, 'chef/daily_menu.html', {
        'chef': chef,
        'today': today,
        'selected_date': selected_date,
        'scheduled_menus': scheduled_menus,
        'chef_meals': chef_meals,
        'next_7_days': next_7_days,
        'form': form,
    })


@chef_required
def daily_menu_add(request):
    chef = request.user.chef_profile
    if request.method == 'POST':
        form = DailyMenuForm(chef, request.POST)
        if form.is_valid():
            menu = form.save(commit=False)
            menu.chef = chef
            # Ensure meal belongs to chef
            if menu.meal.chef != chef:
                messages.error(request, "Security error: You cannot schedule another chef's meal.")
                return redirect('chef:daily_menu')
            
            # Check for existing duplicate schedule
            existing = DailyMenu.objects.filter(chef=chef, date=menu.date, meal=menu.meal, slot=menu.slot).first()
            if existing:
                existing.available_quantity = menu.available_quantity
                existing.is_available = menu.is_available
                existing.special_notes = menu.special_notes
                existing.save()
                messages.info(request, f"Updated existing schedule for {menu.meal.name} on {menu.date}.")
            else:
                menu.save()
                messages.success(request, f"Scheduled '{menu.meal.name}' for {menu.date} ({menu.get_slot_display()}).")
            return redirect(f"{reverse('chef:daily_menu')}?date={menu.date}")
        else:
            messages.error(request, "Failed to schedule meal. Please check form inputs.")

    return redirect('chef:daily_menu')


@chef_required
def daily_menu_delete(request, menu_id):
    chef = request.user.chef_profile
    menu = get_object_or_404(DailyMenu, id=menu_id, chef=chef)
    date_str = menu.date.strftime('%Y-%m-%d')
    name = menu.meal.name
    menu.delete()
    messages.success(request, f"Removed '{name}' from daily schedule.")
    return redirect(f"{reverse('chef:daily_menu')}?date={date_str}")


@chef_required
def daily_menu_toggle(request, menu_id):
    chef = request.user.chef_profile
    menu = get_object_or_404(DailyMenu, id=menu_id, chef=chef)
    menu.is_available = not menu.is_available
    menu.save()
    status_str = "Available" if menu.is_available else "Sold Out / Unavailable"
    messages.success(request, f"Menu item '{menu.meal.name}' marked as {status_str}.")
    return redirect(f"{reverse('chef:daily_menu')}?date={menu.date.strftime('%Y-%m-%d')}")


@chef_required
def order_list(request):
    chef = request.user.chef_profile
    orders_qs = Order.objects.filter(chef=chef).select_related('user').prefetch_related('items')

    # Status filter
    status_filter = request.GET.get('status', 'all')
    if status_filter != 'all' and status_filter in dict(Order.STATUS_CHOICES):
        orders_qs = orders_qs.filter(status=status_filter)

    # Date filter
    date_filter = request.GET.get('date_range')
    today = timezone.now().date()
    if date_filter == 'today':
        orders_qs = orders_qs.filter(created_at__date=today)
    elif date_filter == '7days':
        orders_qs = orders_qs.filter(created_at__date__gte=today - timedelta(days=7))
    elif date_filter == 'month':
        orders_qs = orders_qs.filter(created_at__date__gte=today - timedelta(days=30))

    # Search
    search_q = request.GET.get('q', '').strip()
    if search_q:
        orders_qs = orders_qs.filter(
            Q(order_number__icontains=search_q) |
            Q(recipient_name__icontains=search_q) |
            Q(recipient_phone__icontains=search_q)
        )

    # Status counts for tabs
    all_chef_orders = Order.objects.filter(chef=chef)
    status_counts = {
        'all': all_chef_orders.count(),
        'pending': all_chef_orders.filter(status='pending').count(),
        'confirmed': all_chef_orders.filter(status='confirmed').count(),
        'preparing': all_chef_orders.filter(status='preparing').count(),
        'out_for_delivery': all_chef_orders.filter(status='out_for_delivery').count(),
        'delivered': all_chef_orders.filter(status='delivered').count(),
        'cancelled': all_chef_orders.filter(status='cancelled').count(),
    }

    paginator = Paginator(orders_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'chef/order_list.html', {
        'chef': chef,
        'page_obj': page_obj,
        'status_filter': status_filter,
        'date_filter': date_filter,
        'search_query': search_q,
        'status_counts': status_counts,
        'today': today,
    })


@chef_required
def order_detail(request, order_id):
    chef = request.user.chef_profile
    order = get_object_or_404(Order, id=order_id, chef=chef)
    items = order.items.all()

    # Allowed status transitions
    allowed_transitions = []
    if order.status == 'pending':
        allowed_transitions = [('confirmed', 'Confirm Order'), ('cancelled', 'Decline / Cancel Order')]
    elif order.status == 'confirmed':
        allowed_transitions = [('preparing', 'Start Cooking (In Progress)'), ('cancelled', 'Cancel Order')]
    elif order.status == 'preparing':
        allowed_transitions = [('out_for_delivery', 'Hand Over to Delivery Partner')]
    elif order.status == 'out_for_delivery':
        allowed_transitions = [('delivered', 'Mark as Delivered')]

    # Earnings breakdown for this order
    commission_rate = chef.commission_rate
    order_commission = round((order.final_amount * commission_rate) / Decimal('100.00'), 2)
    order_net_earning = order.final_amount - order_commission

    return render(request, 'chef/order_detail.html', {
        'chef': chef,
        'order': order,
        'items': items,
        'allowed_transitions': allowed_transitions,
        'commission_rate': commission_rate,
        'order_commission': order_commission,
        'order_net_earning': order_net_earning,
    })


@chef_required
def order_status_update(request, order_id):
    chef = request.user.chef_profile
    order = get_object_or_404(Order, id=order_id, chef=chef)

    if request.method == 'POST':
        new_status = request.POST.get('new_status')
        valid_transitions = {
            'pending': ['confirmed', 'cancelled'],
            'confirmed': ['preparing', 'cancelled'],
            'preparing': ['out_for_delivery'],
            'out_for_delivery': ['delivered'],
            'delivered': [],
            'cancelled': [],
        }

        if new_status in valid_transitions.get(order.status, []):
            order.status = new_status
            if new_status == 'cancelled':
                reason = request.POST.get('cancellation_reason', 'Cancelled by chef')
                order.cancellation_reason = reason
            elif new_status == 'delivered':
                # Mark payment status paid if it was COD or pending upon verified delivery
                if order.payment_status == 'pending':
                    order.payment_status = 'paid'
            order.save()

            # Send Email notification on Order Confirmation & Status Updates
            try:
                from customer.emails import send_order_status_update_email
                send_order_status_update_email(order, new_status, async_send=True)
            except Exception as _em_err:
                pass

            messages.success(request, f"Order {order.order_number} status updated to '{order.get_status_display()}'.")
        else:
            messages.error(request, f"Invalid status transition from {order.get_status_display()} to {new_status}.")

    return redirect('chef:order_detail', order_id=order.id)


@chef_required
def subscription_list(request):
    chef = request.user.chef_profile
    subs_qs = Subscription.objects.filter(chef=chef).select_related('user', 'plan')

    status_filter = request.GET.get('status', 'all')
    if status_filter != 'all' and status_filter in dict(Subscription.STATUS_CHOICES):
        subs_qs = subs_qs.filter(status=status_filter)

    search_q = request.GET.get('q', '').strip()
    if search_q:
        subs_qs = subs_qs.filter(
            Q(subscription_number__icontains=search_q) |
            Q(recipient_name__icontains=search_q) |
            Q(recipient_phone__icontains=search_q)
        )

    all_subs = Subscription.objects.filter(chef=chef)
    status_counts = {
        'all': all_subs.count(),
        'active': all_subs.filter(status='active').count(),
        'paused': all_subs.filter(status='paused').count(),
        'completed': all_subs.filter(status='completed').count(),
        'cancelled': all_subs.filter(status='cancelled').count(),
    }

    paginator = Paginator(subs_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'chef/subscription_list.html', {
        'chef': chef,
        'page_obj': page_obj,
        'status_filter': status_filter,
        'search_query': search_q,
        'status_counts': status_counts,
        'today': timezone.now().date(),
    })


@chef_required
def subscription_detail(request, subscription_id):
    chef = request.user.chef_profile
    subscription = get_object_or_404(Subscription, id=subscription_id, chef=chef)

    # Commission breakdown
    commission_rate = chef.commission_rate
    sub_commission = round((subscription.total_amount * commission_rate) / Decimal('100.00'), 2)
    sub_net_earning = subscription.total_amount - sub_commission

    # Associated customer orders
    customer_orders = Order.objects.filter(chef=chef, user=subscription.user).order_by('-created_at')[:5]

    return render(request, 'chef/subscription_detail.html', {
        'chef': chef,
        'subscription': subscription,
        'sub_commission': sub_commission,
        'sub_net_earning': sub_net_earning,
        'customer_orders': customer_orders,
        'today': timezone.now().date(),
    })


@chef_required
def subscription_delete(request, subscription_id):
    chef = request.user.chef_profile
    subscription = get_object_or_404(Subscription, id=subscription_id, chef=chef)
    if request.method == 'POST':
        sub_num = subscription.subscription_number
        subscription.delete()
        messages.success(request, f"Subscription #{sub_num} has been deleted successfully.")
    return redirect('chef:subscriptions')


@chef_required
def plan_list(request):
    chef = request.user.chef_profile
    plans = MealPlan.objects.filter(chef=chef)

    return render(request, 'chef/plan_list.html', {
        'chef': chef,
        'plans': plans,
    })


@chef_required
def plan_add(request):
    chef = request.user.chef_profile

    if request.method == 'POST':
        form = MealPlanForm(request.POST)
        if form.is_valid():
            plan = form.save(commit=False)
            plan.chef = chef
            plan.save()
            messages.success(request, f"Subscription plan '{plan.name}' created successfully!")
            return redirect('chef:plans')
        else:
            messages.error(request, "Could not save subscription plan. Please check inputs.")
    else:
        form = MealPlanForm()

    return render(request, 'chef/plan_form.html', {
        'form': form,
        'title': 'Create New Subscription Plan',
        'is_edit': False,
    })


@chef_required
def plan_edit(request, plan_id):
    chef = request.user.chef_profile
    plan = get_object_or_404(MealPlan, id=plan_id, chef=chef)

    if request.method == 'POST':
        form = MealPlanForm(request.POST, instance=plan)
        if form.is_valid():
            form.save()
            messages.success(request, f"Subscription plan '{plan.name}' updated successfully.")
            return redirect('chef:plans')
        else:
            messages.error(request, "Failed to update subscription plan. Check errors below.")
    else:
        form = MealPlanForm(instance=plan)

    return render(request, 'chef/plan_form.html', {
        'form': form,
        'plan': plan,
        'title': f"Edit Plan: {plan.name}",
        'is_edit': True,
    })


@chef_required
def plan_toggle(request, plan_id):
    chef = request.user.chef_profile
    plan = get_object_or_404(MealPlan, id=plan_id, chef=chef)
    plan.is_active = not plan.is_active
    plan.save()
    status_str = "Active" if plan.is_active else "Inactive"
    messages.success(request, f"Plan '{plan.name}' is now {status_str}.")
    return redirect('chef:plans')


@chef_required
def plan_delete(request, plan_id):
    chef = request.user.chef_profile
    plan = get_object_or_404(MealPlan, id=plan_id, chef=chef)
    if request.method == 'POST':
        name = plan.name
        active_subs = plan.subscriptions.filter(status='active').count()
        if active_subs > 0:
            plan.is_active = False
            plan.save()
            messages.warning(request, f"Plan '{name}' has {active_subs} active subscriber(s). It has been deactivated instead of deleted.")
        else:
            plan.delete()
            messages.success(request, f"Meal plan '{name}' has been deleted successfully.")
    return redirect('chef:plans')


@chef_required
def earnings_view(request):
    chef = request.user.chef_profile
    today = timezone.now().date()
    orders_qs = Order.objects.filter(chef=chef)

    date_filter = request.GET.get('range', 'month')
    if date_filter == 'today':
        filtered = orders_qs.filter(created_at__date=today)
        filter_label = "Today"
    elif date_filter == '7days':
        filtered = orders_qs.filter(created_at__date__gte=today - timedelta(days=7))
        filter_label = "Last 7 Days"
    elif date_filter == 'month':
        filtered = orders_qs.filter(created_at__date__gte=today - timedelta(days=30))
        filter_label = "Last 30 Days"
    elif date_filter == 'prev_month':
        first_of_month = today.replace(day=1)
        prev_month_end = first_of_month - timedelta(days=1)
        prev_month_start = prev_month_end.replace(day=1)
        filtered = orders_qs.filter(created_at__date__gte=prev_month_start, created_at__date__lte=prev_month_end)
        filter_label = prev_month_start.strftime('%B %Y')
    else:
        filtered = orders_qs
        filter_label = "All Time"

    commission_rate = chef.commission_rate

    # Completed orders are eligible for net earnings
    completed_orders = filtered.filter(status='delivered').order_by('-created_at')
    all_completed = orders_qs.filter(status='delivered')

    gross_order_value = all_completed.aggregate(Sum('final_amount'))['final_amount__sum'] or Decimal('0.00')
    gross_order_value = round(Decimal(str(gross_order_value)), 2)
    platform_commission = round((gross_order_value * commission_rate) / Decimal('100.00'), 2)
    net_earnings = round(gross_order_value - platform_commission, 2)

    # Filtered window totals
    filtered_gross = completed_orders.aggregate(Sum('final_amount'))['final_amount__sum'] or Decimal('0.00')
    filtered_gross = round(Decimal(str(filtered_gross)), 2)
    filtered_commission = round((filtered_gross * commission_rate) / Decimal('100.00'), 2)
    filtered_net = round(filtered_gross - filtered_commission, 2)
    completed_sales_count = completed_orders.count()

    # Build earnings list for table
    earnings_rows = []
    for order in completed_orders:
        comm = round((order.final_amount * commission_rate) / Decimal('100.00'), 2)
        net = round(order.final_amount - comm, 2)
        earnings_rows.append({
            'order': order,
            'completion_date': order.updated_at,
            'gross_amount': round(order.final_amount, 2),
            'commission': comm,
            'refund_amount': Decimal('0.00'),
            'net_earnings': net,
            'payout_status': 'Pending Settlement' if order.payment_status == 'paid' else 'Processing',
        })

    paginator = Paginator(earnings_rows, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'chef/earnings.html', {
        'chef': chef,
        'page_obj': page_obj,
        'date_filter': date_filter,
        'filter_label': filter_label,
        'gross_order_value': gross_order_value,
        'platform_commission': platform_commission,
        'net_earnings': net_earnings,
        'filtered_gross': filtered_gross,
        'filtered_commission': filtered_commission,
        'filtered_net': filtered_net,
        'completed_sales_count': completed_sales_count,
        'commission_rate': commission_rate,
    })


@chef_required
def reviews_view(request):
    chef = request.user.chef_profile
    reviews_qs = Review.objects.filter(chef=chef).select_related('user', 'meal')

    rating_filter = request.GET.get('rating')
    if rating_filter and rating_filter in ['1', '2', '3', '4', '5']:
        reviews_qs = reviews_qs.filter(rating=int(rating_filter))

    total_reviews = Review.objects.filter(chef=chef).count()
    avg_rating = chef.rating

    # Breakdown by stars
    star_breakdown = {}
    for star in [5, 4, 3, 2, 1]:
        cnt = Review.objects.filter(chef=chef, rating=star).count()
        pct = int(round((cnt / total_reviews * 100))) if total_reviews > 0 else 0
        star_breakdown[star] = {'count': cnt, 'percent': pct}

    paginator = Paginator(reviews_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'chef/reviews.html', {
        'chef': chef,
        'page_obj': page_obj,
        'total_reviews': total_reviews,
        'avg_rating': avg_rating,
        'star_breakdown': star_breakdown,
        'selected_rating': rating_filter,
    })


@chef_required
def notifications_view(request):
    chef = request.user.chef_profile
    notifications_qs = ChefNotification.objects.filter(chef=chef)

    paginator = Paginator(notifications_qs, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'chef/notifications.html', {
        'chef': chef,
        'page_obj': page_obj,
    })


@chef_required
def notification_mark_read(request, notif_id):
    chef = request.user.chef_profile
    notif = get_object_or_404(ChefNotification, id=notif_id, chef=chef)
    notif.is_read = True
    notif.save()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'ok'})
    return redirect(notif.link or 'chef:notifications')


@chef_required
def notifications_mark_all_read(request):
    chef = request.user.chef_profile
    ChefNotification.objects.filter(chef=chef, is_read=False).update(is_read=True)
    messages.success(request, "All notifications marked as read.")
    return redirect('chef:notifications')


@chef_required
def chef_settings(request):
    chef = request.user.chef_profile

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'toggle_orders':
            chef.is_accepting_orders = not chef.is_accepting_orders
            chef.save()
            status_text = "now accepting orders" if chef.is_accepting_orders else "temporarily paused / closed"
            messages.success(request, f"Kitchen ordering status updated: You are {status_text}.")
            return redirect('chef:settings')
        elif action == 'change_password':
            form = PasswordChangeForm(user=request.user, data=request.POST)
            if form.is_valid():
                form.save()
                update_session_auth_hash(request, form.user)
                messages.success(request, "Your password has been changed successfully.")
                return redirect('chef:settings')
            else:
                messages.error(request, "Password change failed. Please check form errors.")
                return render(request, 'chef/settings.html', {'chef': chef, 'password_form': form})

    password_form = PasswordChangeForm(user=request.user)
    return render(request, 'chef/settings.html', {
        'chef': chef,
        'password_form': password_form,
    })



def chef_forgot_password(request):
    """Chef Studio forgot password request view (sends 6-digit OTP)."""
    if request.user.is_authenticated and hasattr(request.user, 'chef_profile'):
        return redirect('chef:dashboard')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        if not email:
            messages.error(request, "Please enter a valid chef email address.")
            return render(request, 'chef/forgot_password.html')

        import secrets
        from datetime import timedelta
        from django.utils import timezone
        from customer.models import PasswordResetOTP
        from customer.emails import send_chef_password_reset_otp_email

        chef = ChefProfile.objects.filter(user__email__iexact=email).first()
        if chef:
            user = chef.user
            otp = f"{secrets.randbelow(1000000):06d}"
            expires_at = timezone.now() + timedelta(minutes=10)

            PasswordResetOTP.objects.filter(
                email__iexact=email,
                user_type='chef',
                is_used=False
            ).update(is_used=True)

            PasswordResetOTP.objects.create(
                user=user,
                email=email,
                otp=otp,
                expires_at=expires_at,
                user_type='chef'
            )

            send_chef_password_reset_otp_email(chef, otp, async_send=True)
            request.session['chef_reset_email'] = email
            messages.success(request, f"A 6-digit OTP has been sent to {email}. Enter it below to set your new Chef password.")
            return redirect('chef:verify_otp')
        else:
            messages.error(request, "No Chef Studio account found for this email address. Please check your email.")
            return render(request, 'chef/forgot_password.html', {'email': email})

    return render(request, 'chef/forgot_password.html')


def chef_verify_otp(request):
    """Chef Studio OTP verification and password reset."""
    email = request.session.get('chef_reset_email', '').strip()

    def mask_chef_email(e):
        if not e or '@' not in e:
            return e
        p = e.split('@')
        n, d = p[0], p[1]
        m = n[:2] + '*' * max(1, len(n) - 2)
        return f"{m}@{d}"

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower() or email
        otp = request.POST.get('otp', '').strip().replace(' ', '')
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if not email:
            messages.error(request, "Please provide your registered chef email.")
            return render(request, 'chef/verify_otp.html', {'email': email, 'masked_email': mask_chef_email(email)})

        if not otp:
            messages.error(request, "Please enter the 6-digit OTP sent to your email.")
            return render(request, 'chef/verify_otp.html', {'email': email, 'masked_email': mask_chef_email(email)})

        if len(new_password) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
            return render(request, 'chef/verify_otp.html', {'email': email, 'masked_email': mask_chef_email(email)})

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match. Please re-enter.")
            return render(request, 'chef/verify_otp.html', {'email': email, 'masked_email': mask_chef_email(email)})

        from customer.models import PasswordResetOTP

        chef = ChefProfile.objects.filter(user__email__iexact=email).first()
        if not chef:
            messages.error(request, "No Chef Studio account found for this email address.")
            return render(request, 'chef/verify_otp.html', {'email': email, 'masked_email': mask_chef_email(email)})

        user = chef.user
        otp_record = PasswordResetOTP.objects.filter(
            email__iexact=email,
            user_type='chef',
            is_used=False
        ).order_by('-created_at').first()

        if not otp_record or not otp_record.is_valid() or otp_record.otp != otp:
            messages.error(request, "Invalid or expired OTP. Please check the code or request a fresh OTP.")
            return render(request, 'chef/verify_otp.html', {'email': email, 'masked_email': mask_chef_email(email)})

        user.set_password(new_password)
        user.save()
        otp_record.is_used = True
        otp_record.save()

        request.session.pop('chef_reset_email', None)
        messages.success(request, "Chef Studio password reset successfully! You can now sign in with your new password.")
        return redirect('chef:login')

    masked_email = mask_chef_email(email) if email else ''
    return render(request, 'chef/verify_otp.html', {'email': email, 'masked_email': masked_email})


def chef_resend_otp(request):
    """Resend fresh 6-digit OTP to the chef."""
    email = request.session.get('chef_reset_email', '') or request.GET.get('email', '').strip().lower()
    if not email:
        messages.error(request, "Please enter your email to request an OTP.")
        return redirect('chef:forgot_password')

    import secrets
    from datetime import timedelta
    from django.utils import timezone
    from customer.models import PasswordResetOTP
    from customer.emails import send_chef_password_reset_otp_email

    chef = ChefProfile.objects.filter(user__email__iexact=email).first()
    if chef:
        user = chef.user
        otp = f"{secrets.randbelow(1000000):06d}"
        expires_at = timezone.now() + timedelta(minutes=10)

        PasswordResetOTP.objects.filter(
            email__iexact=email,
            user_type='chef',
            is_used=False
        ).update(is_used=True)

        PasswordResetOTP.objects.create(
            user=user,
            email=email,
            otp=otp,
            expires_at=expires_at,
            user_type='chef'
        )

        send_chef_password_reset_otp_email(chef, otp, async_send=True)
        messages.success(request, f"A fresh 6-digit OTP has been sent to {email}.")
    else:
        messages.error(request, "No Chef Studio account found for this email address.")

    request.session['chef_reset_email'] = email
    return redirect('chef:verify_otp')


def chef_password_reset_confirm(request, uidb64, token):
    """Chef Studio password reset confirmation view."""
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

    if user is None or not default_token_generator.check_token(user, token) or not hasattr(user, 'chef_profile'):
        messages.error(request, "This password reset link is invalid or has expired. Please request a new link.")
        return redirect('chef:forgot_password')

    # If another user is logged in, log them out cleanly so the chef account password can be reset
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
            messages.success(request, "Chef Studio password reset successfully! You can now sign in with your new password.")
            return redirect('chef:login')

    return render(request, 'chef/password_reset_confirm.html', {'user': user, 'chef': user.chef_profile})
