from django.urls import path
from . import views

app_name = 'chef'

urlpatterns = [
    # Dashboard & Auth
    path('', views.dashboard, name='dashboard'),
    path('login/', views.chef_login, name='login'),
    path('register/', views.chef_register, name='register'),
    path('logout/', views.chef_logout, name='logout'),
    path('forgot-password/', views.chef_forgot_password, name='forgot_password'),
    path('verify-otp/', views.chef_verify_otp, name='verify_otp'),
    path('resend-otp/', views.chef_resend_otp, name='resend_otp'),
    path('reset-password/<str:uidb64>/<str:token>/', views.chef_password_reset_confirm, name='password_reset_confirm'),
    path('reset/<str:uidb64>/<str:token>/', views.chef_password_reset_confirm, name='password_reset_confirm_alt'),

    # Profile Management
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('profile/upload-images/', views.chef_upload_images, name='upload_images'),

    # Daily Menu & Scheduling
    path('menu/', views.daily_menu_view, name='daily_menu'),
    path('menu/add/', views.daily_menu_add, name='daily_menu_add'),
    path('menu/<int:menu_id>/delete/', views.daily_menu_delete, name='daily_menu_delete'),
    path('menu/<int:menu_id>/toggle/', views.daily_menu_toggle, name='daily_menu_toggle'),

    # Meal Management
    path('meals/', views.meal_list, name='meals'),
    path('meals/add/', views.meal_add, name='meal_add'),
    path('meals/<int:meal_id>/edit/', views.meal_edit, name='meal_edit'),
    path('meals/<int:meal_id>/delete/', views.meal_delete, name='meal_delete'),
    path('meals/<int:meal_id>/toggle/', views.meal_toggle, name='meal_toggle'),

    # Categories
    path('categories/', views.category_list, name='categories'),

    # Orders Management
    path('orders/', views.order_list, name='orders'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('orders/<int:order_id>/status/', views.order_status_update, name='order_status_update'),
    path('deliveries/', views.order_list, name='deliveries'),

    # Subscription Customers & Plans
    path('subscriptions/', views.subscription_list, name='subscriptions'),
    path('subscriptions/<int:subscription_id>/', views.subscription_detail, name='subscription_detail'),
    path('subscriptions/<int:subscription_id>/delete/', views.subscription_delete, name='subscription_delete'),
    path('plans/', views.plan_list, name='plans'),
    path('plans/add/', views.plan_add, name='plan_add'),
    path('plans/<int:plan_id>/edit/', views.plan_edit, name='plan_edit'),
    path('plans/<int:plan_id>/toggle/', views.plan_toggle, name='plan_toggle'),
    path('plans/<int:plan_id>/delete/', views.plan_delete, name='plan_delete'),

    # Financials & Feedback
    path('earnings/', views.earnings_view, name='earnings'),
    path('reviews/', views.reviews_view, name='reviews'),
    path('feedback/', views.reviews_view, name='feedback'),

    # Notifications & Settings
    path('notifications/', views.notifications_view, name='notifications'),
    path('notifications/<int:notif_id>/read/', views.notification_mark_read, name='notification_mark_read'),
    path('notifications/read-all/', views.notifications_mark_all_read, name='notifications_mark_all_read'),
    path('settings/', views.chef_settings, name='settings'),
]
