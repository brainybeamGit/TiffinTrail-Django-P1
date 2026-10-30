from django.urls import path
from . import views

app_name = 'customer'

urlpatterns = [
    # Homepage
    path('', views.home, name='home'),

    # Chefs
    path('chefs/', views.chef_list, name='chefs'),
    path('chefs/<int:pk>/', views.chef_detail, name='chef_detail'),
    path('chefs/<slug:slug>/', views.chef_detail, name='chef_detail_slug'),

    # Menu & Meals
    path('menu/', views.menu, name='menu'),
    path('meals/<int:pk>/', views.meal_detail, name='meal_detail'),

    # Meal Plans & Subscriptions
    path('meal-plans/', views.meal_plans, name='plans'),
    path('subscribe/razorpay/create/', views.razorpay_subscription_create, name='razorpay_subscription_create'),
    path('subscribe/razorpay/verify/', views.razorpay_subscription_verify, name='razorpay_subscription_verify'),
    path('subscribe/<int:chef_id>/<int:plan_id>/', views.subscribe, name='subscribe_direct'),
    path('subscribe/', views.subscribe, name='subscribe'),
    path('subscriptions/', views.my_subscriptions, name='my_subscriptions'),
    path('subscriptions/<int:pk>/', views.subscription_detail, name='subscription_detail'),
    path('subscriptions/<int:pk>/cancel/', views.subscription_cancel, name='subscription_cancel'),
    path('subscriptions/<int:pk>/pause/', views.subscription_pause, name='subscription_pause'),
    path('subscriptions/<int:pk>/resume/', views.subscription_resume, name='subscription_resume'),

    # Cart
    path('cart/', views.cart, name='cart'),
    path('cart/add/<int:meal_id>/', views.cart_add, name='cart_add'),
    path('cart/update/<int:item_id>/', views.cart_update, name='cart_update'),
    path('cart/remove/<int:item_id>/', views.cart_remove, name='cart_remove'),
    path('cart/clear/', views.cart_clear, name='cart_clear'),
    path('cart/apply-coupon/', views.cart_apply_coupon, name='cart_apply_coupon'),
    path('cart/remove-coupon/', views.cart_remove_coupon, name='cart_remove_coupon'),

    # Checkout & Orders
    path('checkout/', views.checkout, name='checkout'),
    path('checkout/razorpay/create/', views.razorpay_order_create, name='razorpay_order_create'),
    path('checkout/razorpay/verify/', views.razorpay_payment_verify, name='razorpay_payment_verify'),
    path('orders/<int:pk>/confirmation/', views.order_confirmation, name='order_confirmation'),
    path('orders/', views.order_history, name='order_history'),
    path('delivery-history/', views.order_history, name='delivery_history'),  # Alias for base.html link
    path('orders/<int:pk>/', views.order_detail, name='order_detail'),
    path('orders/<int:pk>/cancel/', views.order_cancel, name='order_cancel'),
    path('orders/<int:pk>/reorder/', views.order_reorder, name='order_reorder'),

    # Reviews
    path('reviews/', views.reviews_view, name='reviews'),
    path('reviews/add/', views.add_review, name='add_review'),
    path('reviews/<int:pk>/delete/', views.delete_review, name='delete_review'),

    # Profile & Account
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/password/', views.change_password, name='change_password'),
    path('profile/address/add/', views.add_address, name='add_address'),
    path('profile/address/<int:pk>/edit/', views.edit_address, name='edit_address'),
    path('profile/address/<int:pk>/delete/', views.delete_address, name='delete_address'),

    # Auth
    path('login/', views.customer_login, name='login'),
    path('register/', views.customer_register, name='register'),
    path('logout/', views.customer_logout, name='logout'),

    # Static Informational
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
]
