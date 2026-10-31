from django.urls import path
from . import views

app_name = 'adminpanel'

urlpatterns = [
    # Dashboard & Auth
    path('', views.dashboard, name='dashboard'),
    path('login/', views.admin_login, name='login'),
    path('logout/', views.admin_logout, name='logout'),

    # Customers
    path('customers/', views.customer_list, name='customers'),
    path('customers/<int:user_id>/', views.customer_detail, name='customer_detail'),
    path('customers/<int:user_id>/toggle/', views.customer_toggle_status, name='customer_toggle_status'),
    path('customers/<int:user_id>/delete/', views.customer_delete, name='customer_delete'),

    # Chefs & Verification
    path('chefs/', views.chef_list, name='chefs'),
    path('chefs/approvals/', views.chef_list, name='chef_list'),  # Alias
    path('chefs/<int:chef_id>/', views.chef_detail, name='chef_detail'),
    path('chefs/<int:chef_id>/verify/', views.chef_verify_action, name='chef_verify_action'),
    path('chefs/<int:chef_id>/toggle/', views.chef_toggle_status, name='chef_toggle_status'),
    path('chefs/<int:chef_id>/delete/', views.chef_delete, name='chef_delete'),
    path('chefs/<int:chef_id>/images/', views.chef_update_images, name='chef_update_images'),

    # Meals
    path('meals/', views.meal_list, name='meals'),
    path('meals/<int:meal_id>/', views.meal_detail, name='meal_detail'),
    path('meals/<int:meal_id>/toggle/', views.meal_toggle_status, name='meal_toggle_status'),
    path('meals/<int:meal_id>/delete/', views.meal_delete, name='meal_delete'),

    # Meal Plans
    path('plans/', views.meal_plan_list, name='plans'),
    path('plans/add/', views.meal_plan_add, name='plan_add'),
    path('plans/<int:plan_id>/edit/', views.meal_plan_edit, name='plan_edit'),
    path('plans/<int:plan_id>/toggle/', views.meal_plan_toggle, name='plan_toggle'),
    path('plans/<int:plan_id>/delete/', views.meal_plan_delete, name='plan_delete'),

    # Subscriptions
    path('subscriptions/', views.subscription_list, name='subscriptions'),
    path('subscriptions/<int:sub_id>/', views.subscription_detail, name='subscription_detail'),
    path('subscriptions/<int:sub_id>/delete/', views.subscription_delete, name='subscription_delete'),

    # Orders
    path('orders/', views.order_list, name='orders'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('orders/<int:order_id>/delete/', views.order_delete, name='order_delete'),

    # Payments
    path('payments/', views.payment_list, name='payments'),
    path('payments/<int:order_id>/', views.payment_detail, name='payment_detail'),

    # Complaints & Support
    path('complaints/', views.complaint_list, name='complaints'),
    path('complaints/add/', views.complaint_add, name='complaint_add'),
    path('complaints/<int:complaint_id>/', views.complaint_detail, name='complaint_detail'),

    # Coupons
    path('coupons/', views.coupon_list, name='coupons'),
    path('coupons/add/', views.coupon_add, name='coupon_add'),
    path('coupons/<int:coupon_id>/edit/', views.coupon_edit, name='coupon_edit'),
    path('coupons/<int:coupon_id>/toggle/', views.coupon_toggle, name='coupon_toggle'),

    # Reviews Moderation
    path('reviews/', views.review_list, name='reviews'),
    path('reviews/<int:review_id>/toggle/', views.review_toggle_hide, name='review_toggle_hide'),
    path('reviews/<int:review_id>/delete/', views.review_delete, name='review_delete'),

    # Reports & Analytics
    path('reports/', views.reports_view, name='reports'),
    path('analytics/', views.analytics_view, name='analytics'),

    # Notifications & Settings
    path('notifications/', views.notifications_view, name='notifications'),
    path('notices/', views.notifications_view, name='notices'),  # Alias
    path('notifications/<int:notif_id>/read/', views.notification_mark_read, name='notification_mark_read'),
    path('notifications/read-all/', views.notifications_mark_all_read, name='notifications_mark_all_read'),
    path('profile/', views.admin_profile, name='profile'),
    path('settings/', views.admin_settings, name='settings'),
]
