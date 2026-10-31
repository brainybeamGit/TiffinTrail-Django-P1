import csv
from datetime import timedelta
from decimal import Decimal
from functools import wraps
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db import models, transaction
from django.db.models import Sum, Count, Q, Avg
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone

from chef.models import ChefProfile, Meal, MealPlan, MenuCategory, DailyMenu, ChefNotification
from customer.models import Order, OrderItem, Subscription, Review, Coupon, CustomerProfile
from .models import Complaint, AdminNotification, ChefVerificationLog, AdminActivityLog
from .forms import (
    ChefVerificationForm, ComplaintUpdateForm, ComplaintCreateForm,
    AdminCouponForm, AdminMealPlanForm, AdminMealForm, AdminProfileForm
)


def admin_required(view_func):
    """
    Ensures the user is authenticated and is a staff member or superuser.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, "Please log in to access the Admin Console.")
            return redirect(f"{reverse('adminpanel:login')}?next={request.path}")
        if not (request.user.is_staff or request.user.is_superuser):
            messages.error(request, "Access restricted to authorized platform administrators only.")
            return redirect('customer:home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def admin_login(request):
    if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
        return redirect('adminpanel:dashboard')

    next_url = request.GET.get('next') or request.POST.get('next') or reverse('adminpanel:dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            if user.is_staff or user.is_superuser:
                login(request, user)
                messages.success(request, f"Welcome back, Administrator {user.get_full_name() or user.username}!")
                return redirect(next_url)
            else:
                messages.error(request, "Access denied. Your account does not have administrative privileges.")
        else:
            messages.error(request, "Invalid administrator credentials.")

    return render(request, 'adminpanel/login.html', {'next': next_url})


def admin_logout(request):
    logout(request)
    messages.info(request, "You have been securely logged out of the Admin Console.")
    return redirect('customer:home')


@admin_required
def dashboard(request):
    today = timezone.now().date()

    # Core Database Aggregations
    total_customers = User.objects.filter(is_staff=False, chef_profile__isnull=True).count()
    total_chefs = ChefProfile.objects.count()
    pending_verifications = ChefProfile.objects.filter(verification_status='pending').count()
    active_plans = MealPlan.objects.filter(is_active=True).count()

    # Orders
    orders_qs = Order.objects.all()
    total_orders = orders_qs.count()
    pending_orders = orders_qs.filter(status='pending').count()
    in_prep_orders = orders_qs.filter(status__in=['confirmed', 'preparing']).count()
    completed_orders = orders_qs.filter(status='delivered').count()

    # Subscriptions & Revenue
    active_subscriptions = Subscription.objects.filter(status='active').count()
    total_subscriptions = Subscription.objects.count()

    # Revenue calculation: Paid delivered orders + Paid subscriptions
    delivered_orders_rev = orders_qs.filter(status='delivered', payment_status='paid').aggregate(Sum('final_amount'))['final_amount__sum'] or Decimal('0.00')
    subs_rev = Subscription.objects.filter(payment_status='paid').aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
    total_collected_amount = delivered_orders_rev + subs_rev

    successful_payments_count = orders_qs.filter(payment_status='paid').count() + Subscription.objects.filter(payment_status='paid').count()
    pending_complaints_count = Complaint.objects.filter(status__in=['open', 'in_progress']).count()

    # 7-Day Order & Revenue Activity Data for Offline Visualization
    days_data = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        day_orders = orders_qs.filter(created_at__date=d)
        cnt = day_orders.count()
        rev = day_orders.filter(status='delivered').aggregate(Sum('final_amount'))['final_amount__sum'] or Decimal('0.00')
        days_data.append({
            'date': d.strftime('%a, %d %b'),
            'short_date': d.strftime('%d %b'),
            'orders': cnt,
            'revenue': float(rev),
        })

    # Order Status Breakdown
    status_distribution = [
        {'label': 'Pending', 'count': pending_orders, 'color': '#f59e0b'},
        {'label': 'In Prep', 'count': in_prep_orders, 'color': '#3b82f6'},
        {'label': 'Delivered', 'count': completed_orders, 'color': '#10b981'},
        {'label': 'Cancelled', 'count': orders_qs.filter(status='cancelled').count(), 'color': '#ef4444'},
    ]

    # Recent Records
    recent_orders = orders_qs.select_related('user', 'chef').order_by('-created_at')[:6]
    pending_chef_apps = ChefProfile.objects.filter(verification_status='pending').order_by('-created_at')[:5]
    recent_complaints = Complaint.objects.select_related('customer', 'chef').order_by('-created_at')[:5]

    context = {
        'total_customers': total_customers,
        'total_chefs': total_chefs,
        'pending_verifications': pending_verifications,
        'active_plans': active_plans,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'completed_orders': completed_orders,
        'active_subscriptions': active_subscriptions,
        'total_subscriptions': total_subscriptions,
        'successful_payments_count': successful_payments_count,
        'total_collected_amount': total_collected_amount,
        'pending_complaints_count': pending_complaints_count,
        'days_data': days_data,
        'status_distribution': status_distribution,
        'recent_orders': recent_orders,
        'pending_chef_apps': pending_chef_apps,
        'recent_complaints': recent_complaints,
        'today': today,
    }
    return render(request, 'adminpanel/dashboard.html', context)


# ==============================================================================
# Customer Management
# ==============================================================================

@admin_required
def customer_list(request):
    customers = User.objects.filter(is_staff=False, chef_profile__isnull=True).order_by('-date_joined')

    # Search
    search_q = request.GET.get('q', '').strip()
    if search_q:
        customers = customers.filter(
            Q(username__icontains=search_q) |
            Q(first_name__icontains=search_q) |
            Q(last_name__icontains=search_q) |
            Q(email__icontains=search_q)
        )

    # Status filter
    status_filter = request.GET.get('status')
    if status_filter == 'active':
        customers = customers.filter(is_active=True)
    elif status_filter == 'inactive':
        customers = customers.filter(is_active=False)

    # Annotate customers with spending, order counts
    customer_rows = []
    for u in customers:
        orders = Order.objects.filter(user=u)
        total_orders = orders.count()
        completed_orders = orders.filter(status='delivered').count()
        total_spent = orders.filter(status='delivered', payment_status='paid').aggregate(Sum('final_amount'))['final_amount__sum'] or Decimal('0.00')
        active_subs = Subscription.objects.filter(user=u, status='active').count()
        phone = getattr(u, 'customer_profile', None) and u.customer_profile.phone or '—'
        customer_rows.append({
            'user': u,
            'phone': phone,
            'total_orders': total_orders,
            'completed_orders': completed_orders,
            'total_spent': total_spent,
            'active_subs': active_subs,
        })

    paginator = Paginator(customer_rows, 15)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'adminpanel/customers.html', {
        'page_obj': page_obj,
        'search_query': search_q,
        'status_filter': status_filter,
        'total_count': len(customer_rows),
    })


@admin_required
def customer_detail(request, user_id):
    customer = get_object_or_404(User, id=user_id, is_staff=False, chef_profile__isnull=True)
    orders = Order.objects.filter(user=customer).select_related('chef').order_by('-created_at')
    subscriptions = Subscription.objects.filter(user=customer).select_related('chef', 'plan').order_by('-created_at')
    complaints = Complaint.objects.filter(customer=customer).order_by('-created_at')
    addresses = customer.addresses.all()

    total_spent = orders.filter(status='delivered', payment_status='paid').aggregate(Sum('final_amount'))['final_amount__sum'] or Decimal('0.00')
    subs_spent = subscriptions.filter(payment_status='paid').aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')

    return render(request, 'adminpanel/customer_detail.html', {
        'customer': customer,
        'orders': orders,
        'subscriptions': subscriptions,
        'complaints': complaints,
        'addresses': addresses,
        'total_spent': total_spent + subs_spent,
    })


@admin_required
def customer_toggle_status(request, user_id):
    customer = get_object_or_404(User, id=user_id, is_staff=False, chef_profile__isnull=True)
    if request.method == 'POST':
        customer.is_active = not customer.is_active
        customer.save()
        status_str = "Activated" if customer.is_active else "Deactivated"
        AdminActivityLog.objects.create(
            admin=request.user,
            action=f"Customer {status_str}",
            target_model='User',
            target_id=str(customer.id),
            details=f"Customer account {customer.username} set to {status_str}."
        )
        messages.success(request, f"Customer account {customer.username} has been {status_str}.")
    return redirect('adminpanel:customer_detail', user_id=customer.id)


@admin_required
def customer_delete(request, user_id):
    """Permanently delete a customer account and record audit log."""
    customer = get_object_or_404(User, id=user_id, is_staff=False, chef_profile__isnull=True)
    if request.method == 'POST':
        cust_username = customer.username
        cust_email = customer.email
        cust_name = customer.get_full_name() or cust_username

        if customer.is_staff or customer.is_superuser or hasattr(customer, 'chef_profile'):
            messages.error(request, "Staff and Chef accounts cannot be deleted from the customer section.")
            return redirect('adminpanel:customers')

        with transaction.atomic():
            chef_ids = list(customer.reviews.values_list('chef_id', flat=True))

            AdminActivityLog.objects.create(
                admin=request.user,
                action="Customer Deleted",
                target_model='User',
                target_id=str(user_id),
                details=f"Customer '{cust_name}' (@{cust_username}, {cust_email}) was permanently deleted by admin {request.user.username}."
            )

            customer.delete()

            for cid in set(chef_ids):
                c_obj = ChefProfile.objects.filter(id=cid).first()
                if c_obj:
                    c_obj.update_rating()

        messages.success(request, f"Customer account '{cust_name}' (@{cust_username}) has been permanently deleted.")
        return redirect('adminpanel:customers')

    return redirect('adminpanel:customer_detail', user_id=customer.id)


# ==============================================================================
# Chef Management & Verification
# ==============================================================================

@admin_required
def chef_list(request):
    chefs = ChefProfile.objects.select_related('user').all()

    # Search
    search_q = request.GET.get('q', '').strip()
    if search_q:
        chefs = chefs.filter(
            Q(business_name__icontains=search_q) |
            Q(user__first_name__icontains=search_q) |
            Q(user__last_name__icontains=search_q) |
            Q(cuisines__icontains=search_q) |
            Q(service_areas__icontains=search_q)
        )

    # Verification filter
    v_status = request.GET.get('verification')
    if v_status in dict(ChefProfile.VERIFICATION_STATUSES):
        chefs = chefs.filter(verification_status=v_status)

    # Account status filter
    a_status = request.GET.get('account')
    if a_status == 'active':
        chefs = chefs.filter(is_active=True)
    elif a_status == 'suspended':
        chefs = chefs.filter(is_active=False)

    # Summary counts
    all_chefs = ChefProfile.objects.all()
    counts = {
        'all': all_chefs.count(),
        'pending': all_chefs.filter(verification_status='pending').count(),
        'approved': all_chefs.filter(verification_status='approved').count(),
        'rejected': all_chefs.filter(verification_status='rejected').count(),
        'under_review': all_chefs.filter(verification_status='under_review').count(),
    }

    paginator = Paginator(chefs, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'adminpanel/chefs.html', {
        'page_obj': page_obj,
        'search_query': search_q,
        'v_status': v_status,
        'a_status': a_status,
        'counts': counts,
    })


@admin_required
def chef_detail(request, chef_id):
    chef = get_object_or_404(ChefProfile, id=chef_id)
    meals = Meal.objects.filter(chef=chef).order_by('-is_featured', 'name')
    orders = Order.objects.filter(chef=chef).order_by('-created_at')
    subscriptions = Subscription.objects.filter(chef=chef).select_related('user', 'plan').order_by('-created_at')
    reviews = Review.objects.filter(chef=chef).order_by('-created_at')
    verification_logs = chef.verification_logs.select_related('admin').order_by('-created_at')

    # Earnings calculation
    completed_orders = orders.filter(status='delivered')
    gross_sales = completed_orders.aggregate(Sum('final_amount'))['final_amount__sum'] or Decimal('0.00')
    gross_sales = round(Decimal(str(gross_sales)), 2)
    platform_fee = round((gross_sales * chef.commission_rate) / Decimal('100.00'), 2)
    net_earnings = round(gross_sales - platform_fee, 2)

    verification_form = ChefVerificationForm(instance=chef)

    return render(request, 'adminpanel/chef_detail.html', {
        'chef': chef,
        'meals': meals,
        'orders': orders[:10],
        'total_orders_count': orders.count(),
        'completed_orders_count': completed_orders.count(),
        'subscriptions': subscriptions[:10],
        'reviews': reviews,
        'verification_logs': verification_logs,
        'gross_sales': gross_sales,
        'platform_fee': platform_fee,
        'net_earnings': net_earnings,
        'verification_form': verification_form,
    })


@admin_required
def chef_verify_action(request, chef_id):
    chef = get_object_or_404(ChefProfile, id=chef_id)

    if request.method == 'POST':
        action = request.POST.get('action')
        notes = request.POST.get('notes', '').strip()
        commission = request.POST.get('commission_rate')

        if commission:
            try:
                chef.commission_rate = Decimal(str(commission))
            except Exception:
                pass

        if action == 'approve':
            chef.verification_status = 'approved'
            chef.is_approved = True
            log_action = 'approved'
            msg = f"Chef {chef.business_name} has been verified and approved."
            notif_msg = "Congratulations! Your home kitchen application has been approved by TiffinTrail administrators."
        elif action == 'reject':
            reason = request.POST.get('rejection_reason', notes)
            chef.verification_status = 'rejected'
            chef.is_approved = False
            chef.rejection_reason = reason
            log_action = 'rejected'
            msg = f"Chef {chef.business_name} application was rejected."
            notif_msg = f"Your chef application was reviewed and rejected. Reason: {reason or 'Did not meet criteria'}"
        elif action == 'under_review':
            chef.verification_status = 'under_review'
            log_action = 'under_review'
            msg = f"Chef {chef.business_name} status set to Under Review."
            notif_msg = "Your kitchen verification documents are currently under administrative review."
        elif action == 'resubmission':
            reason = request.POST.get('rejection_reason', notes)
            chef.verification_status = 'resubmission'
            chef.is_approved = False
            chef.rejection_reason = reason
            log_action = 'resubmission'
            msg = f"Requested document resubmission from {chef.business_name}."
            notif_msg = f"Additional information or resubmission is required for your kitchen verification: {reason}"
        else:
            messages.error(request, "Invalid verification action.")
            return redirect('adminpanel:chef_detail', chef_id=chef.id)

        chef.save()

        # Create verification log
        ChefVerificationLog.objects.create(
            chef=chef,
            admin=request.user,
            action=log_action,
            notes=notes or chef.rejection_reason
        )

        # Notify Chef
        ChefNotification.objects.create(
            chef=chef,
            title='Kitchen Verification Status Updated',
            message=notif_msg,
            notification_type='system',
            link=reverse('chef:profile')
        )

        AdminActivityLog.objects.create(
            admin=request.user,
            action=f"Chef Verification: {log_action}",
            target_model='ChefProfile',
            target_id=str(chef.id),
            details=f"Verification status set to {chef.get_verification_status_display()}."
        )

        messages.success(request, msg)

    return redirect('adminpanel:chef_detail', chef_id=chef.id)


@admin_required
def chef_toggle_status(request, chef_id):
    chef = get_object_or_404(ChefProfile, id=chef_id)
    if request.method == 'POST':
        chef.is_active = not chef.is_active
        chef.save()
        status_str = "Activated" if chef.is_active else "Suspended"
        AdminActivityLog.objects.create(
            admin=request.user,
            action=f"Chef {status_str}",
            target_model='ChefProfile',
            target_id=str(chef.id),
            details=f"Chef account {chef.business_name} set to {status_str}."
        )
        messages.success(request, f"Chef {chef.business_name} has been {status_str}.")
    return redirect('adminpanel:chef_detail', chef_id=chef.id)


@admin_required
def chef_delete(request, chef_id):
    chef = get_object_or_404(ChefProfile, id=chef_id)
    if request.method == 'POST':
        business_name = chef.business_name
        user = chef.user
        username = user.username if user else "Unknown"

        with transaction.atomic():
            AdminActivityLog.objects.create(
                admin=request.user,
                action="Chef Deleted",
                target_model='ChefProfile',
                target_id=str(chef.id),
                details=f"Chef '{business_name}' (Username: {username}) and associated kitchen data were permanently deleted by administrator {request.user.username}."
            )
            # If user is not superuser/staff, delete user which cascades to chef profile and related items.
            # If user is staff/superuser (e.g. testing admin account), only delete the ChefProfile.
            if user and not (user.is_staff or user.is_superuser):
                user.delete()
            else:
                chef.delete()

        messages.success(request, f"Chef '{business_name}' and all associated records have been permanently deleted.")
        return redirect('adminpanel:chefs')

    return redirect('adminpanel:chef_detail', chef_id=chef.id)


@admin_required
def chef_update_images(request, chef_id):
    chef = get_object_or_404(ChefProfile, id=chef_id)
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
            AdminActivityLog.objects.create(
                admin=request.user,
                action="Chef Images Updated",
                target_model='ChefProfile',
                target_id=str(chef.id),
                details=f"Kitchen cover/profile image updated for {chef.business_name}."
            )
            messages.success(request, f"Images updated successfully for {chef.business_name}.")
        else:
            messages.warning(request, "Please choose an image file to upload.")

    return redirect('adminpanel:chef_detail', chef_id=chef.id)




# ==============================================================================
# Meal & Category Management
# ==============================================================================

@admin_required
def meal_list(request):
    meals = Meal.objects.select_related('chef', 'category').all()

    # Search
    search_q = request.GET.get('q', '').strip()
    if search_q:
        meals = meals.filter(
            Q(name__icontains=search_q) |
            Q(cuisine__icontains=search_q) |
            Q(chef__business_name__icontains=search_q)
        )

    # Filters
    chef_id = request.GET.get('chef')
    if chef_id:
        meals = meals.filter(chef_id=chef_id)

    cat_id = request.GET.get('category')
    if cat_id:
        meals = meals.filter(category_id=cat_id)

    avail = request.GET.get('available')
    if avail == '1':
        meals = meals.filter(is_available=True)
    elif avail == '0':
        meals = meals.filter(is_available=False)

    chefs = ChefProfile.objects.all()
    categories = MenuCategory.objects.all()

    paginator = Paginator(meals, 15)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'adminpanel/meals.html', {
        'page_obj': page_obj,
        'chefs': chefs,
        'categories': categories,
        'search_query': search_q,
        'selected_chef': chef_id,
        'selected_cat': cat_id,
        'selected_avail': avail,
    })


@admin_required
def meal_detail(request, meal_id):
    meal = get_object_or_404(Meal, id=meal_id)
    orders_count = OrderItem.objects.filter(meal=meal).count()

    if request.method == 'POST':
        form = AdminMealForm(request.POST, instance=meal)
        if form.is_valid():
            form.save()
            messages.success(request, f"Meal '{meal.name}' updated successfully.")
            return redirect('adminpanel:meal_detail', meal_id=meal.id)
    else:
        form = AdminMealForm(instance=meal)

    return render(request, 'adminpanel/meal_detail.html', {
        'meal': meal,
        'form': form,
        'orders_count': orders_count,
    })


@admin_required
def meal_toggle_status(request, meal_id):
    meal = get_object_or_404(Meal, id=meal_id)
    if request.method == 'POST':
        meal.is_available = not meal.is_available
        meal.save()
        status_str = "Available" if meal.is_available else "Unavailable"
        messages.success(request, f"Meal '{meal.name}' marked as {status_str}.")
    return redirect(request.META.get('HTTP_REFERER') or 'adminpanel:meals')


@admin_required
def meal_delete(request, meal_id):
    meal = get_object_or_404(Meal, id=meal_id)
    if request.method == 'POST':
        name = meal.name
        chef_name = meal.chef.business_name if meal.chef else "Unknown"
        meal.delete()
        AdminActivityLog.objects.create(
            admin=request.user,
            action="Meal Deleted",
            target_model='Meal',
            target_id=str(meal_id),
            details=f"Permanently deleted meal '{name}' from chef {chef_name}."
        )
        messages.success(request, f"Meal '{name}' was permanently deleted.")
    return redirect('adminpanel:meals')


# ==============================================================================
# Meal Plan Management
# ==============================================================================

@admin_required
def meal_plan_list(request):
    plans = MealPlan.objects.select_related('chef').annotate(
        subs_count=Count('subscriptions'),
        active_subs=Count('subscriptions', filter=Q(subscriptions__status='active'))
    )

    # Search by plan name, description, or chef name
    search_q = request.GET.get('q', '').strip()
    if search_q:
        plans = plans.filter(
            Q(name__icontains=search_q) |
            Q(description__icontains=search_q) |
            Q(chef__business_name__icontains=search_q)
        )

    # Filter by plan type
    plan_type = request.GET.get('plan_type', '').strip()
    if plan_type and plan_type != 'all':
        plans = plans.filter(plan_type=plan_type)

    # Filter by status
    status = request.GET.get('status', '').strip()
    if status == 'active':
        plans = plans.filter(is_active=True)
    elif status == 'inactive':
        plans = plans.filter(is_active=False)

    # Filter by chef
    chef_filter = request.GET.get('chef', '').strip()
    if chef_filter == 'platform':
        plans = plans.filter(chef__isnull=True)
    elif chef_filter and chef_filter != 'all' and chef_filter.isdigit():
        plans = plans.filter(chef_id=int(chef_filter))

    # Aggregates & stats
    all_plans = MealPlan.objects.all()
    total_plans = all_plans.count()
    active_plans = all_plans.filter(is_active=True).count()
    total_active_subs = Subscription.objects.filter(status='active').count()
    weekly_plans = all_plans.filter(plan_type='weekly').count()
    monthly_plans = all_plans.filter(plan_type='monthly').count()

    available_chefs = ChefProfile.objects.filter(is_approved=True).order_by('business_name')

    return render(request, 'adminpanel/meal_plans.html', {
        'plans': plans,
        'chefs': available_chefs,
        'search_q': search_q,
        'current_plan_type': plan_type or 'all',
        'current_status': status or 'all',
        'current_chef': chef_filter or 'all',
        'total_plans': total_plans,
        'active_plans': active_plans,
        'total_active_subs': total_active_subs,
        'weekly_plans': weekly_plans,
        'monthly_plans': monthly_plans,
    })


@admin_required
def meal_plan_add(request):
    if request.method == 'POST':
        form = AdminMealPlanForm(request.POST)
        if form.is_valid():
            plan = form.save()
            AdminActivityLog.objects.create(
                admin=request.user,
                action="Meal Plan Created",
                target_model='MealPlan',
                target_id=str(plan.id),
                details=f"Created meal plan '{plan.name}' (Price: ₹{plan.price}, Type: {plan.get_plan_type_display()})."
            )
            messages.success(request, f"Subscription plan '{plan.name}' created successfully.")
            return redirect('adminpanel:plans')
    else:
        form = AdminMealPlanForm()

    return render(request, 'adminpanel/plan_form.html', {
        'form': form,
        'title': 'Create New Meal Plan',
        'is_edit': False,
    })


@admin_required
def meal_plan_edit(request, plan_id):
    plan = get_object_or_404(MealPlan, id=plan_id)
    if request.method == 'POST':
        form = AdminMealPlanForm(request.POST, instance=plan)
        if form.is_valid():
            form.save()
            AdminActivityLog.objects.create(
                admin=request.user,
                action="Meal Plan Updated",
                target_model='MealPlan',
                target_id=str(plan.id),
                details=f"Updated meal plan '{plan.name}'."
            )
            messages.success(request, f"Subscription plan '{plan.name}' updated successfully.")
            return redirect('adminpanel:plans')
    else:
        form = AdminMealPlanForm(instance=plan)

    return render(request, 'adminpanel/plan_form.html', {
        'form': form,
        'plan': plan,
        'title': f"Edit Plan: {plan.name}",
        'is_edit': True,
    })


@admin_required
def meal_plan_toggle(request, plan_id):
    plan = get_object_or_404(MealPlan, id=plan_id)
    if request.method == 'POST':
        plan.is_active = not plan.is_active
        plan.save()
        status_str = "Active" if plan.is_active else "Inactive"
        AdminActivityLog.objects.create(
            admin=request.user,
            action=f"Meal Plan {status_str}",
            target_model='MealPlan',
            target_id=str(plan.id),
            details=f"Toggled plan '{plan.name}' to {status_str}."
        )
        messages.success(request, f"Plan '{plan.name}' is now {status_str}.")
    return redirect('adminpanel:plans')


@admin_required
def meal_plan_delete(request, plan_id):
    plan = get_object_or_404(MealPlan, id=plan_id)
    if request.method == 'POST':
        active_subs = plan.subscriptions.filter(status='active').count()
        plan_name = plan.name
        if active_subs > 0:
            plan.is_active = False
            plan.save()
            AdminActivityLog.objects.create(
                admin=request.user,
                action="Meal Plan Deactivated (Has Active Subs)",
                target_model='MealPlan',
                target_id=str(plan.id),
                details=f"Plan '{plan_name}' has {active_subs} active subscriptions; deactivated instead of deletion."
            )
            messages.warning(request, f"Plan '{plan_name}' has {active_subs} active customer subscription(s). It has been deactivated instead of deleted to protect active deliveries.")
        else:
            plan.delete()
            AdminActivityLog.objects.create(
                admin=request.user,
                action="Meal Plan Deleted",
                target_model='MealPlan',
                target_id=str(plan_id),
                details=f"Deleted meal plan '{plan_name}'."
            )
            messages.success(request, f"Subscription plan '{plan_name}' has been deleted successfully.")
    return redirect('adminpanel:plans')


# ==============================================================================
# Subscription Management
# ==============================================================================

@admin_required
def subscription_list(request):
    subs = Subscription.objects.select_related('user', 'chef', 'plan').all()

    # Search
    search_q = request.GET.get('q', '').strip()
    if search_q:
        subs = subs.filter(
            Q(subscription_number__icontains=search_q) |
            Q(recipient_name__icontains=search_q) |
            Q(recipient_phone__icontains=search_q) |
            Q(chef__business_name__icontains=search_q)
        )

    # Status filter
    status_filter = request.GET.get('status')
    if status_filter in dict(Subscription.STATUS_CHOICES):
        subs = subs.filter(status=status_filter)

    chefs = ChefProfile.objects.all()

    paginator = Paginator(subs, 15)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'adminpanel/subscriptions.html', {
        'page_obj': page_obj,
        'search_query': search_q,
        'status_filter': status_filter,
        'chefs': chefs,
    })


@admin_required
def subscription_detail(request, sub_id):
    subscription = get_object_or_404(Subscription, id=sub_id)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        reason = request.POST.get('reason', '').strip()
        if new_status in dict(Subscription.STATUS_CHOICES):
            old = subscription.get_status_display()
            subscription.status = new_status
            if reason:
                subscription.cancellation_reason = f"Admin override ({request.user.username}): {reason}"
            subscription.save()

            AdminActivityLog.objects.create(
                admin=request.user,
                action="Subscription Status Override",
                target_model='Subscription',
                target_id=str(subscription.id),
                details=f"Status changed from {old} to {subscription.get_status_display()}. Note: {reason}"
            )
            messages.success(request, f"Subscription status updated to {subscription.get_status_display()}.")
            return redirect('adminpanel:subscription_detail', sub_id=subscription.id)

    return render(request, 'adminpanel/subscription_detail.html', {
        'sub': subscription,
    })


@admin_required
def subscription_delete(request, sub_id):
    subscription = get_object_or_404(Subscription, id=sub_id)
    if request.method == 'POST':
        sub_num = subscription.subscription_number
        recipient = subscription.recipient_name
        subscription.delete()
        AdminActivityLog.objects.create(
            admin=request.user,
            action="Subscription Deleted",
            target_model='Subscription',
            target_id=str(sub_id),
            details=f"Permanently deleted subscription #{sub_num} for customer {recipient}."
        )
        messages.success(request, f"Subscription #{sub_num} has been permanently deleted.")
    return redirect('adminpanel:subscriptions')


# ==============================================================================
# Order Management
# ==============================================================================

@admin_required
def order_list(request):
    orders = Order.objects.select_related('user', 'chef').prefetch_related('items').all()

    # Search
    search_q = request.GET.get('q', '').strip()
    if search_q:
        orders = orders.filter(
            Q(order_number__icontains=search_q) |
            Q(recipient_name__icontains=search_q) |
            Q(recipient_phone__icontains=search_q) |
            Q(chef__business_name__icontains=search_q)
        )

    # Status filter
    status_filter = request.GET.get('status')
    if status_filter in dict(Order.STATUS_CHOICES):
        orders = orders.filter(status=status_filter)

    # Payment filter
    payment_filter = request.GET.get('payment')
    if payment_filter in dict(Order.PAYMENT_STATUSES):
        orders = orders.filter(payment_status=payment_filter)

    paginator = Paginator(orders, 15)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'adminpanel/orders.html', {
        'page_obj': page_obj,
        'search_query': search_q,
        'status_filter': status_filter,
        'payment_filter': payment_filter,
    })


@admin_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    items = order.items.all()

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'override_status':
            new_status = request.POST.get('new_status')
            reason = request.POST.get('reason', '').strip()
            if new_status in dict(Order.STATUS_CHOICES):
                order.status = new_status
                if reason:
                    order.cancellation_reason = f"Admin override: {reason}"
                order.save()
                try:
                    from customer.emails import send_order_status_update_email
                    send_order_status_update_email(order, new_status, async_send=True)
                except Exception:
                    pass
                AdminActivityLog.objects.create(
                    admin=request.user,
                    action="Order Status Override",
                    target_model='Order',
                    target_id=str(order.id),
                    details=f"Status set to {new_status}. Reason: {reason}"
                )
                messages.success(request, f"Order status updated to {order.get_status_display()}.")
                return redirect('adminpanel:order_detail', order_id=order.id)

    return render(request, 'adminpanel/order_detail.html', {
        'order': order,
        'items': items,
    })


@admin_required
def order_delete(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if request.method == 'POST':
        order_num = order.order_number
        order.delete()
        AdminActivityLog.objects.create(
            admin=request.user,
            action="Order Deleted",
            target_model='Order',
            target_id=str(order_id),
            details=f"Order #{order_num} was permanently deleted by admin {request.user.username}."
        )
        messages.success(request, f"Order #{order_num} has been successfully deleted.")
        return redirect('adminpanel:orders')

    return redirect('adminpanel:order_detail', order_id=order.id)


# ==============================================================================
# Payment Management
# ==============================================================================

@admin_required
def payment_list(request):
    # Collect payments across Orders and Subscriptions
    orders_qs = Order.objects.select_related('user', 'chef').order_by('-created_at')

    status_filter = request.GET.get('status')
    if status_filter in dict(Order.PAYMENT_STATUSES):
        orders_qs = orders_qs.filter(payment_status=status_filter)

    search_q = request.GET.get('q', '').strip()
    if search_q:
        orders_qs = orders_qs.filter(
            Q(order_number__icontains=search_q) |
            Q(recipient_name__icontains=search_q) |
            Q(payment_transaction_id__icontains=search_q)
        )

    # Financial sums
    total_paid_orders = Order.objects.filter(payment_status='paid').aggregate(Sum('final_amount'))['final_amount__sum'] or Decimal('0.00')
    total_paid_subs = Subscription.objects.filter(payment_status='paid').aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
    total_collected = total_paid_orders + total_paid_subs

    paginator = Paginator(orders_qs, 15)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'adminpanel/payments.html', {
        'page_obj': page_obj,
        'search_query': search_q,
        'status_filter': status_filter,
        'total_collected': total_collected,
        'total_paid_orders': total_paid_orders,
        'total_paid_subs': total_paid_subs,
    })


@admin_required
def payment_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'adminpanel/payment_detail.html', {'order': order})


# ==============================================================================
# Complaints & Customer Support
# ==============================================================================

@admin_required
def complaint_list(request):
    complaints = Complaint.objects.select_related('customer', 'chef', 'assigned_admin').all()

    # Status filter
    status_filter = request.GET.get('status')
    if status_filter in dict(Complaint.STATUS_CHOICES):
        complaints = complaints.filter(status=status_filter)

    # Priority filter
    priority_filter = request.GET.get('priority')
    if priority_filter in dict(Complaint.PRIORITY_CHOICES):
        complaints = complaints.filter(priority=priority_filter)

    # Search
    search_q = request.GET.get('q', '').strip()
    if search_q:
        complaints = complaints.filter(
            Q(ticket_number__icontains=search_q) |
            Q(subject__icontains=search_q) |
            Q(customer__username__icontains=search_q) |
            Q(customer__first_name__icontains=search_q)
        )

    # Counts
    all_cmp = Complaint.objects.all()
    counts = {
        'all': all_cmp.count(),
        'open': all_cmp.filter(status='open').count(),
        'in_progress': all_cmp.filter(status='in_progress').count(),
        'resolved': all_cmp.filter(status='resolved').count(),
        'closed': all_cmp.filter(status='closed').count(),
    }

    paginator = Paginator(complaints, 15)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'adminpanel/complaints.html', {
        'page_obj': page_obj,
        'search_query': search_q,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'counts': counts,
    })


@admin_required
def complaint_detail(request, complaint_id):
    complaint = get_object_or_404(Complaint, id=complaint_id)

    if request.method == 'POST':
        form = ComplaintUpdateForm(request.POST, instance=complaint)
        if form.is_valid():
            cmp = form.save(commit=False)
            if cmp.status in ['resolved', 'closed'] and not cmp.resolved_at:
                cmp.resolved_at = timezone.now()
            cmp.save()

            AdminActivityLog.objects.create(
                admin=request.user,
                action="Complaint Updated",
                target_model='Complaint',
                target_id=str(cmp.id),
                details=f"Complaint {cmp.ticket_number} status updated to {cmp.get_status_display()}."
            )
            messages.success(request, f"Ticket {cmp.ticket_number} updated.")
            return redirect('adminpanel:complaint_detail', complaint_id=cmp.id)
    else:
        form = ComplaintUpdateForm(instance=complaint)

    return render(request, 'adminpanel/complaint_detail.html', {
        'complaint': complaint,
        'form': form,
    })


@admin_required
def complaint_add(request):
    if request.method == 'POST':
        form = ComplaintCreateForm(request.POST)
        if form.is_valid():
            cmp = form.save()
            messages.success(request, f"Support ticket {cmp.ticket_number} created.")
            return redirect('adminpanel:complaint_detail', complaint_id=cmp.id)
    else:
        form = ComplaintCreateForm()

    return render(request, 'adminpanel/complaint_form.html', {'form': form})


# ==============================================================================
# Coupon & Discount Management
# ==============================================================================

@admin_required
def coupon_list(request):
    coupons = Coupon.objects.all().order_by('-is_active', 'code')

    search_q = request.GET.get('q', '').strip()
    if search_q:
        coupons = coupons.filter(Q(code__icontains=search_q) | Q(description__icontains=search_q))

    return render(request, 'adminpanel/coupons.html', {
        'coupons': coupons,
        'search_query': search_q,
    })


@admin_required
def coupon_add(request):
    if request.method == 'POST':
        form = AdminCouponForm(request.POST)
        if form.is_valid():
            cpn = form.save()
            messages.success(request, f"Coupon code '{cpn.code}' created successfully!")
            return redirect('adminpanel:coupons')
    else:
        form = AdminCouponForm()

    return render(request, 'adminpanel/coupon_form.html', {
        'form': form,
        'title': 'Create New Coupon',
        'is_edit': False,
    })


@admin_required
def coupon_edit(request, coupon_id):
    coupon = get_object_or_404(Coupon, id=coupon_id)
    if request.method == 'POST':
        form = AdminCouponForm(request.POST, instance=coupon)
        if form.is_valid():
            form.save()
            messages.success(request, f"Coupon '{coupon.code}' updated.")
            return redirect('adminpanel:coupons')
    else:
        form = AdminCouponForm(instance=coupon)

    return render(request, 'adminpanel/coupon_form.html', {
        'form': form,
        'coupon': coupon,
        'title': f"Edit Coupon: {coupon.code}",
        'is_edit': True,
    })


@admin_required
def coupon_toggle(request, coupon_id):
    coupon = get_object_or_404(Coupon, id=coupon_id)
    if request.method == 'POST':
        coupon.is_active = not coupon.is_active
        coupon.save()
        status_str = "Active" if coupon.is_active else "Inactive"
        messages.success(request, f"Coupon '{coupon.code}' is now {status_str}.")
    return redirect('adminpanel:coupons')


# ==============================================================================
# Reviews Moderation
# ==============================================================================

@admin_required
def review_list(request):
    reviews = Review.objects.select_related('user', 'chef', 'meal').all()

    # Rating filter
    rating_filter = request.GET.get('rating')
    if rating_filter in ['1', '2', '3', '4', '5']:
        reviews = reviews.filter(rating=int(rating_filter))

    # Moderation filter
    mod_filter = request.GET.get('moderation')
    if mod_filter == 'hidden':
        reviews = reviews.filter(is_hidden=True)
    elif mod_filter == 'visible':
        reviews = reviews.filter(is_hidden=False)

    search_q = request.GET.get('q', '').strip()
    if search_q:
        reviews = reviews.filter(
            Q(comment__icontains=search_q) |
            Q(user__username__icontains=search_q) |
            Q(chef__business_name__icontains=search_q)
        )

    paginator = Paginator(reviews, 15)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'adminpanel/reviews.html', {
        'page_obj': page_obj,
        'rating_filter': rating_filter,
        'mod_filter': mod_filter,
        'search_query': search_q,
    })


@admin_required
def review_toggle_hide(request, review_id):
    review = get_object_or_404(Review, id=review_id)
    if request.method == 'POST':
        review.is_hidden = not review.is_hidden
        note = request.POST.get('moderation_notes', '')
        if note:
            review.moderation_notes = note
        review.save()
        review.chef.update_rating()
        status_str = "Hidden from public view" if review.is_hidden else "Restored to public view"
        messages.success(request, f"Review #{review.id} has been {status_str}.")
    return redirect('adminpanel:reviews')

@admin_required
def review_delete(request, review_id):
    review = get_object_or_404(Review, id=review_id)
    if request.method == 'POST':
        chef = review.chef
        reviewer_name = review.user.get_full_name() or review.user.username
        rating_val = review.rating

        with transaction.atomic():
            AdminActivityLog.objects.create(
                admin=request.user,
                action="Review Deleted",
                target_model='Review',
                target_id=str(review_id),
                details=f"Review #{review_id} ({rating_val} stars) by '{reviewer_name}' for Chef '{chef.business_name}' was permanently deleted by admin {request.user.username}."
            )
            # review.delete() calls chef.update_rating() internally
            review.delete()

        messages.success(request, f"Review #{review_id} by {reviewer_name} has been permanently deleted.")
        next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
        if next_url and next_url != request.build_absolute_uri():
            return redirect(next_url)
        return redirect('adminpanel:reviews')
    return redirect('adminpanel:reviews')



# ==============================================================================
# Reports Module with Filters & CSV Export
# ==============================================================================

@admin_required
def reports_view(request):
    report_type = request.GET.get('report_type', 'orders')
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    today = timezone.now().date()
    # Default date range: Last 30 days
    if start_date_str:
        try:
            start_date = timezone.datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            start_date = today - timedelta(days=30)
    else:
        start_date = today - timedelta(days=30)

    if end_date_str:
        try:
            end_date = timezone.datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            end_date = today
    else:
        end_date = today

    # Validate range
    if start_date > end_date:
        start_date = end_date - timedelta(days=30)
        messages.warning(request, "Start date cannot be after end date. Adjusted to last 30 days.")

    export_format = request.GET.get('export')

    # Data dispatch based on report_type
    summary = {}
    rows = []
    headers = []

    if report_type == 'orders':
        qs = Order.objects.filter(created_at__date__gte=start_date, created_at__date__lte=end_date).select_related('user', 'chef')
        total_val = qs.aggregate(Sum('final_amount'))['final_amount__sum'] or Decimal('0.00')
        delivered_val = qs.filter(status='delivered').aggregate(Sum('final_amount'))['final_amount__sum'] or Decimal('0.00')
        total_val = round(Decimal(str(total_val)), 2)
        delivered_val = round(Decimal(str(delivered_val)), 2)
        summary = {
            'records_count': qs.count(),
            'total_order_value': total_val,
            'delivered_value': delivered_val,
            'completed_count': qs.filter(status='delivered').count(),
            'pending_count': qs.filter(status='pending').count(),
        }
        headers = ['Order #', 'Date', 'Customer', 'Chef', 'Items Count', 'Amount (₹)', 'Payment Status', 'Order Status']
        for o in qs:
            rows.append([
                o.order_number,
                o.created_at.strftime('%Y-%m-%d %H:%M'),
                o.recipient_name,
                o.chef.business_name,
                o.items.count(),
                f"{Decimal(str(o.final_amount)):.2f}",
                o.get_payment_status_display(),
                o.get_status_display()
            ])

    elif report_type == 'revenue':
        orders_paid = Order.objects.filter(created_at__date__gte=start_date, created_at__date__lte=end_date, status='delivered')
        subs_paid = Subscription.objects.filter(created_at__date__gte=start_date, created_at__date__lte=end_date, payment_status='paid')
        order_gross = orders_paid.aggregate(Sum('final_amount'))['final_amount__sum'] or Decimal('0.00')
        sub_gross = subs_paid.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
        total_rev = order_gross + sub_gross
        platform_fee = round(total_rev * Decimal('0.10'), 2)
        chef_payout = total_rev - platform_fee
        summary = {
            'records_count': orders_paid.count() + subs_paid.count(),
            'gross_revenue': total_rev,
            'order_revenue': order_gross,
            'subscription_revenue': sub_gross,
            'platform_commission': platform_fee,
            'chef_payout': chef_payout,
        }
        headers = ['Transaction Ref', 'Date', 'Category', 'Diner', 'Chef', 'Gross Amount (₹)', 'Est. Platform Fee (10%)', 'Net Chef Share']
        for o in orders_paid:
            comm = round(o.final_amount * Decimal('0.10'), 2)
            rows.append([
                o.order_number,
                o.created_at.strftime('%Y-%m-%d'),
                'Meal Order',
                o.recipient_name,
                o.chef.business_name,
                f"{Decimal(str(o.final_amount)):.2f}",
                f"{comm:.2f}",
                f"{(o.final_amount - comm):.2f}"
            ])
        for s in subs_paid:
            comm = round(s.total_amount * Decimal('0.10'), 2)
            rows.append([
                s.subscription_number,
                s.created_at.strftime('%Y-%m-%d'),
                f"Subscription ({s.plan.name})",
                s.recipient_name,
                s.chef.business_name,
                f"{Decimal(str(s.total_amount)):.2f}",
                f"{comm:.2f}",
                f"{(s.total_amount - comm):.2f}"
            ])

    elif report_type == 'subscriptions':
        qs = Subscription.objects.filter(created_at__date__gte=start_date, created_at__date__lte=end_date).select_related('user', 'chef', 'plan')
        total_sub_val = qs.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
        summary = {
            'records_count': qs.count(),
            'active_count': qs.filter(status='active').count(),
            'total_value': round(Decimal(str(total_sub_val)), 2),
        }
        headers = ['Subscription #', 'Start Date', 'End Date', 'Diner', 'Chef', 'Plan', 'Slot', 'Diet', 'Amount (₹)', 'Status']
        for s in qs:
            rows.append([
                s.subscription_number,
                s.start_date.strftime('%Y-%m-%d'),
                s.end_date.strftime('%Y-%m-%d'),
                s.recipient_name,
                s.chef.business_name,
                s.plan.name,
                s.get_delivery_slot_display(),
                s.get_dietary_preference_display(),
                f"{Decimal(str(s.total_amount)):.2f}",
                s.get_status_display()
            ])

    elif report_type == 'customers':
        qs = User.objects.filter(is_staff=False, chef_profile__isnull=True, date_joined__date__gte=start_date, date_joined__date__lte=end_date)
        summary = {
            'records_count': qs.count(),
            'active_count': qs.filter(is_active=True).count(),
        }
        headers = ['User ID', 'Username', 'Name', 'Email', 'Joined Date', 'Account Status']
        for u in qs:
            rows.append([
                u.id,
                u.username,
                u.get_full_name() or '—',
                u.email or '—',
                u.date_joined.strftime('%Y-%m-%d'),
                'Active' if u.is_active else 'Inactive'
            ])

    elif report_type == 'chefs':
        qs = ChefProfile.objects.filter(created_at__date__gte=start_date, created_at__date__lte=end_date).select_related('user')
        summary = {
            'records_count': qs.count(),
            'approved_count': qs.filter(verification_status='approved').count(),
            'pending_count': qs.filter(verification_status='pending').count(),
        }
        headers = ['Chef ID', 'Kitchen Name', 'Chef Full Name', 'Phone', 'Verification Status', 'Account Status', 'Rating', 'Joined Date']
        for c in qs:
            rows.append([
                c.id,
                c.business_name,
                c.user.get_full_name() or c.user.username,
                c.phone or '—',
                c.get_verification_status_display(),
                'Active' if c.is_active else 'Suspended',
                f"{c.rating}★",
                c.created_at.strftime('%Y-%m-%d')
            ])

    elif report_type == 'complaints':
        qs = Complaint.objects.filter(created_at__date__gte=start_date, created_at__date__lte=end_date).select_related('customer', 'chef')
        summary = {
            'records_count': qs.count(),
            'resolved_count': qs.filter(status='resolved').count(),
            'open_count': qs.filter(status__in=['open', 'in_progress']).count(),
        }
        headers = ['Ticket #', 'Date', 'Customer', 'Related Chef', 'Category', 'Priority', 'Status']
        for cmp in qs:
            rows.append([
                cmp.ticket_number,
                cmp.created_at.strftime('%Y-%m-%d'),
                cmp.customer.username,
                cmp.chef.business_name if cmp.chef else '—',
                cmp.get_category_display(),
                cmp.get_priority_display(),
                cmp.get_status_display()
            ])

    elif report_type == 'coupons':
        qs = Coupon.objects.all()
        summary = {
            'records_count': qs.count(),
            'active_count': qs.filter(is_active=True).count(),
            'total_redemptions': sum(c.times_used for c in qs),
        }
        headers = ['Coupon Code', 'Description', 'Discount', 'Min Order', 'Limit', 'Redeemed', 'Status']
        for cpn in qs:
            rows.append([
                cpn.code,
                cpn.description or '—',
                f"{cpn.discount_value}{'%' if cpn.discount_type == 'percent' else '₹'}",
                f"₹{cpn.min_order_amount}",
                cpn.usage_limit,
                cpn.times_used,
                'Active' if cpn.is_active else 'Inactive'
            ])

    # Handle CSV Export
    if export_format == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="TiffinTrail_Report_{report_type}_{start_date}_{end_date}.csv"'
        writer = csv.writer(response)
        writer.writerow([f"TiffinTrail Report: {report_type.upper()} ({start_date} to {end_date})"])
        writer.writerow([])
        writer.writerow(headers)
        for r in rows:
            writer.writerow(r)
        return response

    # Handle Printable format
    if export_format == 'print':
        return render(request, 'adminpanel/report_printable.html', {
            'report_type': report_type,
            'start_date': start_date,
            'end_date': end_date,
            'summary': summary,
            'headers': headers,
            'rows': rows,
            'now': timezone.now(),
        })

    paginator = Paginator(rows, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'adminpanel/reports.html', {
        'report_type': report_type,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'summary': summary,
        'headers': headers,
        'page_obj': page_obj,
    })


# ==============================================================================
# Analytics & Charts
# ==============================================================================

@admin_required
def analytics_view(request):
    today = timezone.now().date()

    # Timeframe selection
    days_span = int(request.GET.get('days', 30))
    start_d = today - timedelta(days=days_span)

    orders_qs = Order.objects.filter(created_at__date__gte=start_d)
    subs_qs = Subscription.objects.filter(created_at__date__gte=start_d)

    # 1. Daily order trend
    order_trend = []
    for i in range(min(days_span, 14) - 1, -1, -1):
        d = today - timedelta(days=i)
        cnt = orders_qs.filter(created_at__date=d).count()
        rev = orders_qs.filter(created_at__date=d, status='delivered').aggregate(Sum('final_amount'))['final_amount__sum'] or Decimal('0.00')
        order_trend.append({
            'date': d.strftime('%d %b'),
            'orders': cnt,
            'revenue': float(rev),
        })

    # 2. Top Performing Chefs (by order volume & revenue)
    top_chefs = (
        ChefProfile.objects.annotate(
            orders_count=Count('orders', filter=Q(orders__status='delivered')),
            total_rev=Sum('orders__final_amount', filter=Q(orders__status='delivered'))
        )
        .order_by('-orders_count')[:6]
    )

    # 3. Top Ordered Meals
    top_meals = (
        OrderItem.objects.filter(order__created_at__date__gte=start_d)
        .values('meal_name')
        .annotate(total_qty=Sum('quantity'), total_val=Sum('subtotal'))
        .order_by('-total_qty')[:6]
    )

    # 4. Plan Popularity
    plan_popularity = (
        MealPlan.objects.annotate(subs_count=Count('subscriptions'))
        .order_by('-subs_count')[:5]
    )

    # 5. Customer & Chef growth
    customers_growth = User.objects.filter(is_staff=False, chef_profile__isnull=True, date_joined__date__gte=start_d).count()
    chefs_growth = ChefProfile.objects.filter(created_at__date__gte=start_d).count()

    context = {
        'days_span': days_span,
        'order_trend': order_trend,
        'top_chefs': top_chefs,
        'top_meals': top_meals,
        'plan_popularity': plan_popularity,
        'customers_growth': customers_growth,
        'chefs_growth': chefs_growth,
        'total_orders_period': orders_qs.count(),
        'delivered_period': orders_qs.filter(status='delivered').count(),
    }
    return render(request, 'adminpanel/analytics.html', context)


# ==============================================================================
# Admin Notifications
# ==============================================================================

@admin_required
def notifications_view(request):
    notifications = AdminNotification.objects.all()
    paginator = Paginator(notifications, 15)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'adminpanel/notifications.html', {'page_obj': page_obj})


@admin_required
def notification_mark_read(request, notif_id):
    notif = get_object_or_404(AdminNotification, id=notif_id)
    notif.is_read = True
    notif.save()
    return redirect(notif.link or 'adminpanel:notifications')


@admin_required
def notifications_mark_all_read(request):
    AdminNotification.objects.filter(is_read=False).update(is_read=True)
    messages.success(request, "All notifications marked as read.")
    return redirect('adminpanel:notifications')


# ==============================================================================
# Profile & Settings
# ==============================================================================

@admin_required
def admin_profile(request):
    if request.method == 'POST':
        form = AdminProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile details have been updated.")
            return redirect('adminpanel:profile')
    else:
        form = AdminProfileForm(instance=request.user)

    return render(request, 'adminpanel/profile.html', {'form': form})


@admin_required
def admin_settings(request):
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, form.user)
            messages.success(request, "Your administrator password has been changed successfully.")
            return redirect('adminpanel:settings')
        else:
            messages.error(request, "Failed to change password. Please check the errors below.")
    else:
        form = PasswordChangeForm(user=request.user)

    return render(request, 'adminpanel/settings.html', {'password_form': form})
