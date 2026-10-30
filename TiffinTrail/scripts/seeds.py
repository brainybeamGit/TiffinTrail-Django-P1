"""
TiffinTrail - Original User Data Seeder (seeds.py)
Location: docs/seeds.py

This script populates the database with the exact original production/user data
created by the project owner:
- Users: admin, amrita (Chef), dklakum (Chef), dk (Customer)
- Customer Profile & Delivery Address for 'dk'
- Chef Profiles: 'Amrita punjabi rasoi' & 'Annapurna Ghar Ka Khana'
- Menu Categories: Gujarati Specials, Homestyle Thalis, Punjabi Delights,
                   Rice & Biryani Bowls, Healthy Meal Boxes
- Meals: Dal Makhani & Phulka Thali, Kathiyawadi Gujarati Thali,
         Punjabi Chole & Rice, Homemade Veg Pulao Bowl, Healthy Veg Meal Box
- Meal Plans: Daily Ghar Ka Tiffin, Weekly Family Veg Plan,
              Premium Weekly Meal Box, Monthly Gujarati Special, Monthly Healthy Tiffin
- Active Coupon: FESTIVE50 (with dynamic promotional description)
- Orders: Real customer orders placed by 'dk'
- Subscriptions: Active weekly subscriptions placed by 'dk'
- Notifications & Admin Logs

How to run:
    1) Directly via Python:
       python docs/seeds.py

    2) Via Django manage.py command (if configured):
       python manage.py seed
"""

import os
import sys
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone

# -----------------------------------------------------------------------------
# 1. Django Setup (Allows running standalone directly: python docs/seeds.py)
# -----------------------------------------------------------------------------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(CURRENT_DIR)

if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "TiffinTrail.settings")

try:
    import django
    django.setup()
except Exception as e:
    print(f"[ERROR] Failed to initialize Django: {e}")
    sys.exit(1)

from django.db import transaction
from django.contrib.auth import get_user_model
from customer.models import (
    CustomerProfile, DeliveryAddress, Coupon, Order, OrderItem, Subscription
)
from chef.models import ChefProfile, MenuCategory, Meal, MealPlan, ChefNotification
from adminpanel.models import AdminNotification, AdminActivityLog

User = get_user_model()


# -----------------------------------------------------------------------------
# 2. Seeding Functions
# -----------------------------------------------------------------------------

def seed_users():
    """
    Seeds the 4 original accounts:
    1. admin (Superuser)
    2. amrita (Home Chef)
    3. dklakum (Home Chef)
    4. dk (Customer)
    """
    print(">>> Seeding Users...")

    users_data = [
        {
            "username": "admin",
            "email": "admin123@gmail.com",
            "first_name": "",
            "last_name": "",
            "is_staff": True,
            "is_superuser": True,
            "password_hash": "pbkdf2_sha256$1500000$9xPW8PohwQWzuCEccRzBkS$ER/SHfW/bvGmui6txPKeqsLCfCF7cNGPPEG9BuZ/ykQ=",
            "default_raw_password": "admin"
        },
        {
            "username": "amrita",
            "email": "chef@example.com",
            "first_name": "Amrita",
            "last_name": "vora",
            "is_staff": False,
            "is_superuser": False,
            "password_hash": "pbkdf2_sha256$1500000$sRy93GyLV8McNlW7nGPhX1$gYfdj84WVdLbH3JnAbht6/Ixf1ExePe453P4Pj9yW0Y=",
            "default_raw_password": "chef"
        },
        {
            "username": "dklakum",
            "email": "lakumdharmesh799@gmail.com",
            "first_name": "Dharmesh",
            "last_name": "Lakum",
            "is_staff": False,
            "is_superuser": False,
            "password_hash": "pbkdf2_sha256$1500000$ajNcVmc56gbB4BqUjlpo67$yg1Zwqv1A0SAnqSmq4Z3D3nBToDtqxtLalIa3GbmVPo=",
            "default_raw_password": "chef"
        },
        {
            "username": "dk",
            "email": "lakumdharmesh798@gmail.com",
            "first_name": "Dharmesh",
            "last_name": "Lakum",
            "is_staff": False,
            "is_superuser": False,
            "password_hash": "pbkdf2_sha256$1500000$Tic1aqFwyYksSlsj4dzHoy$DA4rGjG3TVB6vWFYsoTiokGhRFXM8ZQYsv4WdmfNBcs=",
            "default_raw_password": "customer"
        },
    ]

    users = {}
    for item in users_data:
        user, created = User.objects.get_or_create(
            username=item["username"],
            defaults={
                "email": item["email"],
                "first_name": item["first_name"],
                "last_name": item["last_name"],
                "is_staff": item["is_staff"],
                "is_superuser": item["is_superuser"],
                "is_active": True,
            }
        )
        if created:
            # Set the exact existing PBKDF2 hash so existing login credentials work
            user.password = item["password_hash"]
            user.save()
            print(f"  [CREATED] User: {user.username} ({user.email})")
        else:
            # Update fields while preserving user's current password
            user.email = item["email"]
            user.first_name = item["first_name"]
            user.last_name = item["last_name"]
            user.is_staff = item["is_staff"]
            user.is_superuser = item["is_superuser"]
            user.is_active = True
            user.save()
            print(f"  [EXISTS]  User: {user.username}")

        users[item["username"]] = user

    return users


def seed_customer_profile_and_address(users):
    """
    Seeds customer profile and delivery address for user 'dk'.
    """
    print("\n>>> Seeding Customer Profile and Delivery Address...")
    customer_user = users.get("dk")
    if not customer_user:
        return

    # 1. CustomerProfile
    profile, created = CustomerProfile.objects.get_or_create(
        user=customer_user,
        defaults={
            "phone": "7779009972",
            "bio": ""
        }
    )
    status_str = "[CREATED]" if created else "[EXISTS]"
    print(f"  {status_str} Customer Profile for: {customer_user.username}")

    # 2. DeliveryAddress
    addr, created = DeliveryAddress.objects.get_or_create(
        user=customer_user,
        title="Home",
        defaults={
            "recipient_name": "Dharmesh Lakum",
            "phone_number": "7779009972",
            "street_address": "Flat 204, Royal Palms Apartment",
            "area": "Indiranagar",
            "city": "Bengaluru",
            "pincode": "560038",
            "delivery_notes": "",
            "is_default": True
        }
    )
    status_str = "[CREATED]" if created else "[EXISTS]"
    print(f"  {status_str} Delivery Address for: {customer_user.username}")


def seed_chefs(users):
    """
    Seeds the 2 original home chef profiles:
    - Amrita punjabi rasoi (user: amrita)
    - Annapurna Ghar Ka Khana (user: dklakum)
    """
    print("\n>>> Seeding Chef Profiles...")

    chefs_data = [
        {
            "username": "amrita",
            "business_name": "Amrita punjabi rasoi",
            "slug": "amrita-punjabi-rasoi",
            "bio": "",
            "profile_image": "chefs/rasoi_gahr.png",
            "cover_image": "chefs/covers/cover.png",
            "specialties": "Dal Makhani",
            "cuisines": "punjabi",
            "phone": "9723700320",
            "kitchen_address": "Ahemdabad",
            "service_areas": "Ahemdabad",
            "starting_price": Decimal("120.00"),
            "experience_years": 5,
            "working_days": "Monday - Saturday",
            "working_hours": "8:00 AM - 8:00 PM",
            "preparation_preferences": "Fresh daily batch cooking, zero artificial food additives, food-grade thermal packaging.",
            "commission_rate": Decimal("10.00"),
            "is_accepting_orders": True,
            "rating": Decimal("4.80"),
            "review_count": 0,
            "verification_status": "approved",
            "verification_document": "chefs/documents/Google_Shopping_Ads_Shopify_Guide.png",
            "is_approved": True,
            "is_active": True,
            "fssai_license": "FSSAI-REG-2024-98412"
        },
        {
            "username": "dklakum",
            "business_name": "Annapurna Ghar Ka Khana",
            "slug": "annapurna-ghar-ka-khana",
            "bio": "",
            "profile_image": "chefs/profile.png",
            "cover_image": "chefs/covers/cover_benner.png",
            "specialties": "Dal Baati Churma, Gujarati Thali, Paneer Butter Masala",
            "cuisines": "North Indian, Punjabi, Gujarati, Jain",
            "phone": "7779009972",
            "kitchen_address": "Shop No. 12, Shreeji Residency, Satellite Road, Ahmedabad, Gujarat",
            "service_areas": "Satellite, Vastrapur, Prahlad Nagar, Bodakdev",
            "starting_price": Decimal("120.00"),
            "experience_years": 5,
            "working_days": "Monday - Saturday",
            "working_hours": "8:00 AM - 8:00 PM",
            "preparation_preferences": "Fresh daily batch cooking, zero artificial food additives, food-grade thermal packaging.",
            "commission_rate": Decimal("10.00"),
            "is_accepting_orders": True,
            "rating": Decimal("4.80"),
            "review_count": 0,
            "verification_status": "approved",
            "verification_document": "chefs/documents/Google_Ads_Performance_Dashboard.png",
            "is_approved": True,
            "is_active": True,
            "fssai_license": "FSSAI-REG-2024-98412"
        }
    ]

    chefs = {}
    for cdata in chefs_data:
        chef_user = users.get(cdata["username"])
        if not chef_user:
            continue

        chef, created = ChefProfile.objects.update_or_create(
            user=chef_user,
            defaults={
                "business_name": cdata["business_name"],
                "slug": cdata["slug"],
                "bio": cdata["bio"],
                "profile_image": cdata["profile_image"],
                "cover_image": cdata["cover_image"],
                "specialties": cdata["specialties"],
                "cuisines": cdata["cuisines"],
                "phone": cdata["phone"],
                "kitchen_address": cdata["kitchen_address"],
                "service_areas": cdata["service_areas"],
                "starting_price": cdata["starting_price"],
                "experience_years": cdata["experience_years"],
                "working_days": cdata["working_days"],
                "working_hours": cdata["working_hours"],
                "preparation_preferences": cdata["preparation_preferences"],
                "commission_rate": cdata["commission_rate"],
                "is_accepting_orders": cdata["is_accepting_orders"],
                "rating": cdata["rating"],
                "review_count": cdata["review_count"],
                "verification_status": cdata["verification_status"],
                "verification_document": cdata["verification_document"],
                "is_approved": cdata["is_approved"],
                "is_active": cdata["is_active"],
                "fssai_license": cdata["fssai_license"],
            }
        )
        status_str = "[CREATED]" if created else "[UPDATED]"
        print(f"  {status_str} Chef: {chef.business_name} (User: {chef_user.username})")
        chefs[cdata["username"]] = chef

    return chefs


def seed_categories():
    """
    Seeds the 5 original menu categories.
    """
    print("\n>>> Seeding Menu Categories...")

    categories_data = [
        {
            "name": "Gujarati Specials",
            "slug": "gujarati-specials",
            "description": "Authentic Gujarati homemade meals including Gujarati thali, thepla, rotli, dal, kadhi and seasonal vegetarian dishes.",
            "icon": "\U0001f37d",
            "display_order": 1
        },
        {
            "name": "Homestyle Thalis",
            "slug": "homestyle-thalis",
            "description": "Fresh, wholesome homemade thali meals featuring roti, seasonal sabzi, dal, rice, salad and traditional Indian flavors.",
            "icon": "\U0001f371",
            "display_order": 1
        },
        {
            "name": "Punjabi Delights",
            "slug": "punjabi-delights",
            "description": "Rich and flavorful Punjabi dishes including dal makhani, chole, paneer curries, parathas and wholesome North Indian meals.",
            "icon": "\U0001f35b",
            "display_order": 1
        },
        {
            "name": "Rice & Biryani Bowls",
            "slug": "rice-biryani-bowls",
            "description": "Delicious rice-based meals featuring vegetable pulao, jeera rice, homemade biryani and comforting rice bowls served with accompaniments.",
            "icon": "\U0001f35a",
            "display_order": 1
        },
        {
            "name": "Healthy Meal Boxes",
            "slug": "healthy-meal-boxes",
            "description": "Balanced everyday meals prepared with fresh ingredients, seasonal vegetables, whole grains and nutritious homemade recipes.",
            "icon": "\U0001f957",
            "display_order": 5
        }
    ]

    categories = {}
    for cat_data in categories_data:
        cat, created = MenuCategory.objects.update_or_create(
            slug=cat_data["slug"],
            defaults={
                "name": cat_data["name"],
                "description": cat_data["description"],
                "icon": cat_data["icon"],
                "display_order": cat_data["display_order"]
            }
        )
        status_str = "[CREATED]" if created else "[UPDATED]"
        print(f"  {status_str} Category: {cat.name} ({cat.slug})")
        categories[cat.slug] = cat

    return categories


def seed_meals(chefs, categories):
    """
    Seeds the 5 original homemade meals.
    """
    print("\n>>> Seeding Meals...")

    meals_data = [
        {
            "chef_key": "dklakum",
            "category_slug": "homestyle-thalis",
            "name": "Dal Makhani & Phulka Thali",
            "slug": "dal-makhani-phulka-thali-annapurna-ghar-ka-khana",
            "description": "Creamy homemade dal makhani served with 3 soft whole-wheat phulkas, fresh onion salad and homemade pickle. Prepared with traditional Indian spices.",
            "image": "meals/Dal_Makhani_and_Phulka_Thali_Feast.png",
            "price": Decimal("149.00"),
            "is_veg": True,
            "cuisine": "Homestyle Indian",
            "meal_type": "lunch",
            "calories": 450,
            "preparation_time": 30,
            "available_quantity": 25,
            "is_available": True,
            "is_featured": False,
            "ingredients": "Black urad dal, rajma, tomatoes, butter, cream, whole-wheat flour and spices",
            "allergen_info": "Contains dairy and gluten",
            "rating": Decimal("4.80")
        },
        {
            "chef_key": "dklakum",
            "category_slug": "gujarati-specials",
            "name": "Kathiyawadi Gujarati Thali",
            "slug": "kathiyawadi-gujarati-thali-annapurna-ghar-ka-khana",
            "description": "Traditional Gujarati meal with fresh rotli, seasonal shaak, Gujarati dal, steamed rice, salad and homemade kadhi. A comforting everyday meal prepared with authentic Gujarati flavors.",
            "image": "meals/gujarati_thali.png",
            "price": Decimal("179.00"),
            "is_veg": True,
            "cuisine": "Gujarati Kathiyawadi",
            "meal_type": "lunch",
            "calories": 600,
            "preparation_time": 35,
            "available_quantity": 20,
            "is_available": True,
            "is_featured": False,
            "ingredients": "Wheat flour, seasonal vegetables, toor dal, rice, curd and Gujarati spices",
            "allergen_info": "Contains gluten and dairy; check for other allergens based on ingredients",
            "rating": Decimal("4.80")
        },
        {
            "chef_key": "dklakum",
            "category_slug": "punjabi-delights",
            "name": "Punjabi Chole & Rice",
            "slug": "punjabi-chole-rice-annapurna-ghar-ka-khana",
            "description": "Flavorful chickpeas simmered in a rich onion-tomato gravy with Punjabi spices, served with steamed basmati rice, sliced onion and lemon.",
            "image": "meals/punjabi_thali.png",
            "price": Decimal("119.00"),
            "is_veg": True,
            "cuisine": "Punjabi",
            "meal_type": "lunch",
            "calories": 450,
            "preparation_time": 30,
            "available_quantity": 20,
            "is_available": True,
            "is_featured": False,
            "ingredients": "Chickpeas, basmati rice, tomatoes, onions, ginger, garlic and chole masala",
            "allergen_info": "Check spice blends for gluten and possible cross-contact",
            "rating": Decimal("4.80")
        },
        {
            "chef_key": "amrita",
            "category_slug": "rice-biryani-bowls",
            "name": "Homemade Veg Pulao Bowl",
            "slug": "homemade-veg-pulao-bowl-amrita-punjabi-rasoi",
            "description": "Aromatic basmati rice cooked with seasonal vegetables and whole spices, served with refreshing cucumber raita and fresh salad.",
            "image": "meals/pulao.png",
            "price": Decimal("129.00"),
            "is_veg": True,
            "cuisine": "Homestyle Indian",
            "meal_type": "lunch",
            "calories": 450,
            "preparation_time": 25,
            "available_quantity": 25,
            "is_available": True,
            "is_featured": False,
            "ingredients": "Basmati rice, carrots, peas, beans, cumin, whole spices, curd and cucumber",
            "allergen_info": "Contains dairy; verify ingredients and cross-contact",
            "rating": Decimal("4.80")
        },
        {
            "chef_key": "amrita",
            "category_slug": "healthy-meal-boxes",
            "name": "Healthy Veg Meal Box",
            "slug": "healthy-veg-meal-box-amrita-punjabi-rasoi",
            "description": "A balanced homemade meal featuring 2 whole-wheat chapatis, seasonal vegetable sabzi, moong dal and fresh cucumber salad. Prepared with everyday spices and a moderate amount of oil.",
            "image": "meals/box.png",
            "price": Decimal("139.00"),
            "is_veg": True,
            "cuisine": "Healthy Homestyle Indian",
            "meal_type": "lunch",
            "calories": 400,
            "preparation_time": 30,
            "available_quantity": 20,
            "is_available": True,
            "is_featured": False,
            "ingredients": "Whole-wheat flour, seasonal vegetables, moong dal, cucumber, cumin and cooking oil",
            "allergen_info": "Contains gluten; verify all ingredients for other allergens",
            "rating": Decimal("4.80")
        }
    ]

    meals = {}
    for mdata in meals_data:
        chef = chefs.get(mdata["chef_key"])
        category = categories.get(mdata["category_slug"])
        if not chef:
            continue

        meal, created = Meal.objects.update_or_create(
            slug=mdata["slug"],
            defaults={
                "chef": chef,
                "category": category,
                "name": mdata["name"],
                "description": mdata["description"],
                "image": mdata["image"],
                "price": mdata["price"],
                "is_veg": mdata["is_veg"],
                "cuisine": mdata["cuisine"],
                "meal_type": mdata["meal_type"],
                "calories": mdata["calories"],
                "preparation_time": mdata["preparation_time"],
                "available_quantity": mdata["available_quantity"],
                "is_available": mdata["is_available"],
                "is_featured": mdata["is_featured"],
                "ingredients": mdata["ingredients"],
                "allergen_info": mdata["allergen_info"],
                "rating": mdata["rating"]
            }
        )
        status_str = "[CREATED]" if created else "[UPDATED]"
        print(f"  {status_str} Meal: {meal.name} (Chef: {chef.business_name})")
        meals[meal.name] = meal

    return meals


def seed_meal_plans(chefs):
    """
    Seeds the 5 original subscription meal plans.
    """
    print("\n>>> Seeding Meal Plans...")

    plans_data = [
        {
            "chef_key": "dklakum",
            "name": "Daily Ghar Ka Tiffin",
            "slug": "daily-ghar-ka-tiffin",
            "description": "Fresh homemade vegetarian lunch for students and office workers.",
            "plan_type": "daily",
            "duration_days": 0,
            "meals_per_day": 1,
            "price": Decimal("149.00"),
            "original_price": Decimal("169.00"),
            "is_veg": True,
            "is_active": True,
            "features": "Fresh homemade lunch\r\n4 rotis with seasonal sabzi\r\nDal and steamed rice\r\nDaily fresh preparation\r\nHygienic food packaging",
            "delivery_schedule": "Lunch delivery | 12:00 PM - 2:00 PM",
            "service_conditions": "Valid for one day from the selected start date. Cancellation requests must be submitted before meal preparation begins. Refunds depend on the cancellation policy."
        },
        {
            "chef_key": "dklakum",
            "name": "Weekly Family Veg Plan",
            "slug": "weekly-family-veg-plan",
            "description": "A full week of fresh, homestyle vegetarian lunches with a rotating menu.",
            "plan_type": "weekly",
            "duration_days": 7,
            "meals_per_day": 1,
            "price": Decimal("899.00"),
            "original_price": Decimal("1050.00"),
            "is_veg": True,
            "is_active": True,
            "features": "7 days of homemade lunch\r\nDaily rotating sabzi menu\r\nFresh roti, dal and rice\r\nSeasonal vegetables\r\nWeekly menu variety\r\nHygienic packaging",
            "delivery_schedule": "Lunch delivery | 12:00 PM - 2:00 PM, daily",
            "service_conditions": "Valid for 7 consecutive days. Pause or cancellation requests must be submitted before the next meal preparation cutoff. Refunds for unused days are subject to the chef's policy."
        },
        {
            "chef_key": "amrita",
            "name": "Premium Weekly Meal Box",
            "slug": "premium-weekly-meal-box",
            "description": "Premium lunch and dinner with special curries and a varied Indian menu.",
            "plan_type": "weekly",
            "duration_days": 7,
            "meals_per_day": 2,
            "price": Decimal("1199.00"),
            "original_price": Decimal("1399.00"),
            "is_veg": True,
            "is_active": True,
            "features": "14 fresh meals per week\r\nLunch and dinner every day\r\nPremium seasonal curries\r\nPaneer special on selected days\r\nRoti and rice with meals\r\nRotating chef-special menu\r\nSecure food packaging",
            "delivery_schedule": "Lunch: 12:00 PM - 1:30 PM | Dinner: 7:30 PM - 9:00 PM",
            "service_conditions": "Valid for 7 consecutive days. Changes to the delivery schedule must be requested before the preparation cutoff. Refunds are subject to the published cancellation terms."
        },
        {
            "chef_key": "amrita",
            "name": "Monthly Gujarati Special",
            "slug": "monthly-gujarati-special",
            "description": "A month of traditional Gujarati home-cooked lunches with regional favourites.",
            "plan_type": "monthly",
            "duration_days": 30,
            "meals_per_day": 1,
            "price": Decimal("3799.00"),
            "original_price": Decimal("4199.00"),
            "is_veg": True,
            "is_active": True,
            "features": "30 homemade Gujarati lunches\r\nGujarati shaak and rotli\r\nDal or kadhi with rice\r\nTraditional seasonal dishes\r\nVaried weekly menu\r\nFreshly prepared food\r\nHygienic packaging",
            "delivery_schedule": "Lunch delivery, 12:00 PM - 2:00 PM, daily",
            "service_conditions": "Valid for 30 consecutive days. Pause and cancellation requests must follow the chef's notice period. Refunds for unused meals are subject to the published policy."
        },
        {
            "chef_key": "dklakum",
            "name": "Monthly Healthy Tiffin",
            "slug": "monthly-healthy-tiffin",
            "description": "A convenient monthly vegetarian lunch and dinner package for busy professionals.",
            "plan_type": "weekly",
            "duration_days": 30,
            "meals_per_day": 2,
            "price": Decimal("4499.00"),
            "original_price": Decimal("4999.00"),
            "is_veg": True,
            "is_active": True,
            "features": "30 days of homemade vegetarian meals\r\nLunch and dinner daily\r\nFresh rotis and seasonal sabzi\r\nDal, rice and rotating menu\r\nBalanced everyday meals\r\nMonthly subscription convenience\r\nFood prepared fresh daily",
            "delivery_schedule": "Lunch: 12:00 PM - 1:30 PM | Dinner: 7:30 PM - 9:00 PM",
            "service_conditions": "Valid for 30 consecutive days. Any pause, skipped meal or cancellation must follow the chef's notice period. Refunds are calculated according to the published policy and consumed meals."
        }
    ]

    plans = {}
    for pdata in plans_data:
        chef = chefs.get(pdata["chef_key"])
        if not chef:
            continue

        plan, created = MealPlan.objects.update_or_create(
            slug=pdata["slug"],
            defaults={
                "chef": chef,
                "name": pdata["name"],
                "description": pdata["description"],
                "plan_type": pdata["plan_type"],
                "duration_days": pdata["duration_days"],
                "meals_per_day": pdata["meals_per_day"],
                "price": pdata["price"],
                "original_price": pdata["original_price"],
                "is_veg": pdata["is_veg"],
                "is_active": pdata["is_active"],
                "features": pdata["features"],
                "delivery_schedule": pdata["delivery_schedule"],
                "service_conditions": pdata["service_conditions"]
            }
        )
        status_str = "[CREATED]" if created else "[UPDATED]"
        print(f"  {status_str} Meal Plan: {plan.name} (Chef: {chef.business_name})")
        plans[plan.name] = plan

    return plans


def seed_coupons():
    """
    Seeds the original active coupon with dynamic promotional description.
    """
    print("\n>>> Seeding Coupons...")

    coupon, created = Coupon.objects.update_or_create(
        code="FESTIVE50",
        defaults={
            "description": "Get 50% off on your first meal order.",
            "discount_type": "percent",
            "discount_value": Decimal("50.00"),
            "min_order_amount": Decimal("200.00"),
            "max_discount_amount": Decimal("100.00"),
            "usage_limit": 100,
            "times_used": 14,
            "is_active": True,
            "valid_until": timezone.now() + timedelta(days=60)
        }
    )
    status_str = "[CREATED]" if created else "[UPDATED]"
    print(f"  {status_str} Coupon: {coupon.code} (Description: {coupon.description})")
    return {"FESTIVE50": coupon}


def seed_orders(users, chefs, meals):
    """
    Seeds the 4 original orders placed by 'dk'.
    """
    print("\n>>> Seeding Orders & Order Items...")

    customer = users.get("dk")
    if not customer:
        return {}

    orders_data = [
        {
            "order_number": "TT-ORD-202610280407-3231E7",
            "chef_key": "dklakum",
            "recipient_name": "Dharmesh Lakum",
            "recipient_phone": "7779009972",
            "delivery_address_text": "jothpur char rasta, setelite, Ahemdabad - 380001",
            "status": "pending",
            "total_amount": Decimal("358.00"),
            "delivery_fee": Decimal("0.00"),
            "tax_amount": Decimal("17.90"),
            "discount_amount": Decimal("0.00"),
            "final_amount": Decimal("375.90"),
            "payment_method": "online",
            "payment_status": "paid",
            "payment_transaction_id": "TT-SIMPAY-864537",
            "items": [
                {
                    "meal_name": "Kathiyawadi Gujarati Thali",
                    "unit_price": Decimal("179.00"),
                    "quantity": 2,
                    "subtotal": Decimal("358.00")
                }
            ]
        },
        {
            "order_number": "TT-ORD-202610280507-B7C202",
            "chef_key": "dklakum",
            "recipient_name": "Dharmesh Lakum",
            "recipient_phone": "7779009972",
            "delivery_address_text": "Flat 204, Royal Palms Apartment, Indiranagar, Bengaluru - 560038",
            "status": "cancelled",
            "total_amount": Decimal("238.00"),
            "delivery_fee": Decimal("35.00"),
            "tax_amount": Decimal("11.90"),
            "discount_amount": Decimal("0.00"),
            "final_amount": Decimal("284.90"),
            "payment_method": "online",
            "payment_status": "paid",
            "payment_transaction_id": "pay_TtCt3voaaZdU57",
            "items": [
                {
                    "meal_name": "Punjabi Chole & Rice",
                    "unit_price": Decimal("119.00"),
                    "quantity": 2,
                    "subtotal": Decimal("238.00")
                }
            ]
        },
        {
            "order_number": "TT-ORD-202610290523-5D6FCB",
            "chef_key": "dklakum",
            "recipient_name": "Dharmesh Lakum",
            "recipient_phone": "7779009972",
            "delivery_address_text": "Flat 204, Royal Palms Apartment, Indiranagar, Bengaluru - 560038",
            "status": "preparing",
            "total_amount": Decimal("476.00"),
            "delivery_fee": Decimal("0.00"),
            "tax_amount": Decimal("23.80"),
            "discount_amount": Decimal("0.00"),
            "final_amount": Decimal("499.80"),
            "payment_method": "cod",
            "payment_status": "pending",
            "payment_transaction_id": "",
            "items": [
                {
                    "meal_name": "Punjabi Chole & Rice",
                    "unit_price": Decimal("119.00"),
                    "quantity": 4,
                    "subtotal": Decimal("476.00")
                }
            ]
        },
        {
            "order_number": "TT-ORD-202610300304-14C419",
            "chef_key": "amrita",
            "recipient_name": "Dharmesh Lakum",
            "recipient_phone": "7779009972",
            "delivery_address_text": "Flat 204, Royal Palms Apartment, Indiranagar, Bengaluru - 560038",
            "status": "delivered",
            "total_amount": Decimal("278.00"),
            "delivery_fee": Decimal("35.00"),
            "tax_amount": Decimal("13.90"),
            "discount_amount": Decimal("100.00"),
            "final_amount": Decimal("226.90"),
            "payment_method": "online",
            "payment_status": "paid",
            "payment_transaction_id": "pay_TtxrO7OWanVaWO",
            "items": [
                {
                    "meal_name": "Healthy Veg Meal Box",
                    "unit_price": Decimal("139.00"),
                    "quantity": 2,
                    "subtotal": Decimal("278.00")
                }
            ]
        }
    ]

    orders = {}
    for odata in orders_data:
        chef = chefs.get(odata["chef_key"])
        if not chef:
            continue

        order, created = Order.objects.update_or_create(
            order_number=odata["order_number"],
            defaults={
                "user": customer,
                "chef": chef,
                "recipient_name": odata["recipient_name"],
                "recipient_phone": odata["recipient_phone"],
                "delivery_address_text": odata["delivery_address_text"],
                "status": odata["status"],
                "total_amount": odata["total_amount"],
                "delivery_fee": odata["delivery_fee"],
                "tax_amount": odata["tax_amount"],
                "discount_amount": odata["discount_amount"],
                "final_amount": odata["final_amount"],
                "payment_method": odata["payment_method"],
                "payment_status": odata["payment_status"],
                "payment_transaction_id": odata["payment_transaction_id"]
            }
        )
        status_str = "[CREATED]" if created else "[UPDATED]"
        print(f"  {status_str} Order: {order.order_number} ({order.status})")

        # Create/Update order items
        for item_data in odata["items"]:
            meal = meals.get(item_data["meal_name"])
            OrderItem.objects.update_or_create(
                order=order,
                meal_name=item_data["meal_name"],
                defaults={
                    "meal": meal,
                    "unit_price": item_data["unit_price"],
                    "quantity": item_data["quantity"],
                    "subtotal": item_data["subtotal"]
                }
            )

        orders[order.order_number] = order

    return orders


def seed_subscriptions(users, chefs, meal_plans):
    """
    Seeds the 2 original active subscriptions placed by 'dk'.
    """
    print("\n>>> Seeding Subscriptions...")

    customer = users.get("dk")
    if not customer:
        return {}

    subs_data = [
        {
            "subscription_number": "TT-SUB-20261029-3B9D4B",
            "chef_key": "dklakum",
            "plan_name": "Weekly Family Veg Plan",
            "start_date": date.today(),
            "end_date": date.today() + timedelta(days=7),
            "recipient_name": "Dharmesh Lakum",
            "recipient_phone": "7779009972",
            "delivery_address_text": "Flat 204, Royal Palms Apartment, Indiranagar, Bengaluru - 560038",
            "delivery_slot": "lunch",
            "dietary_preference": "veg",
            "status": "active",
            "total_amount": Decimal("899.00"),
            "payment_method": "online",
            "payment_status": "paid",
            "payment_transaction_id": "TT-SIMPAY-261745"
        },
        {
            "subscription_number": "TT-SUB-20261029-3E9E3B",
            "chef_key": "amrita",
            "plan_name": "Premium Weekly Meal Box",
            "start_date": date.today(),
            "end_date": date.today() + timedelta(days=7),
            "recipient_name": "Dharmesh Lakum",
            "recipient_phone": "7779009972",
            "delivery_address_text": "Flat 204, Royal Palms Apartment, Indiranagar, Bengaluru - 560038",
            "delivery_slot": "lunch",
            "dietary_preference": "veg",
            "status": "active",
            "total_amount": Decimal("1199.00"),
            "payment_method": "online",
            "payment_status": "paid",
            "payment_transaction_id": "pay_TtaMwSNZw0GjEv"
        }
    ]

    subscriptions = {}
    for sdata in subs_data:
        chef = chefs.get(sdata["chef_key"])
        plan = meal_plans.get(sdata["plan_name"])
        if not chef or not plan:
            continue

        sub, created = Subscription.objects.update_or_create(
            subscription_number=sdata["subscription_number"],
            defaults={
                "user": customer,
                "chef": chef,
                "plan": plan,
                "start_date": sdata["start_date"],
                "end_date": sdata["end_date"],
                "recipient_name": sdata["recipient_name"],
                "recipient_phone": sdata["recipient_phone"],
                "delivery_address_text": sdata["delivery_address_text"],
                "delivery_slot": sdata["delivery_slot"],
                "dietary_preference": sdata["dietary_preference"],
                "status": sdata["status"],
                "total_amount": sdata["total_amount"],
                "payment_method": sdata["payment_method"],
                "payment_status": sdata["payment_status"],
                "payment_transaction_id": sdata["payment_transaction_id"]
            }
        )
        status_str = "[CREATED]" if created else "[UPDATED]"
        print(f"  {status_str} Subscription: {sub.subscription_number} (Plan: {plan.name})")
        subscriptions[sub.subscription_number] = sub

    return subscriptions


def seed_notifications_and_logs(users, chefs):
    """
    Seeds original chef notifications, admin notifications, and admin logs.
    """
    print("\n>>> Seeding Notifications and Audit Logs...")

    chef_amrita = chefs.get("amrita")
    chef_dklakum = chefs.get("dklakum")
    admin_user = users.get("admin")

    # Chef notifications
    if chef_amrita:
        ChefNotification.objects.get_or_create(
            chef=chef_amrita,
            title="Kitchen Verification Status Updated",
            defaults={
                "message": "Congratulations! Your home kitchen application has been approved by TiffinTrail administrators.",
                "notification_type": "system",
                "link": "/chef/profile/",
                "is_read": False
            }
        )

    if chef_dklakum:
        ChefNotification.objects.get_or_create(
            chef=chef_dklakum,
            title="Kitchen Verification Status Updated",
            defaults={
                "message": "Congratulations! Your home kitchen application has been approved by TiffinTrail administrators.",
                "notification_type": "system",
                "link": "/chef/profile/",
                "is_read": False
            }
        )

    # Admin notifications
    admin_notifs = [
        ("New Chef Registration: Annapurna Ghar Ka Khana", "Chef Dharmesh Lakum has applied to join TiffinTrail with 'Annapurna Ghar Ka Khana'. Verification is pending.", "/adminpanel/chefs/14/"),
        ("New Chef Registration: Amrita punjabi rasoi", "Chef Amrita vora has applied to join TiffinTrail with 'Amrita punjabi rasoi'. Verification is pending.", "/adminpanel/chefs/13/"),
        ("New Chef Registration: Maa Ki Rasoi", "Chef Dharmesh Lakum has applied to join TiffinTrail with 'Maa Ki Rasoi'. Verification is pending.", "/adminpanel/chefs/7/"),
        ("New Chef Registration: Sunita Bihari Litti Rasoi", "Chef Sunita Devi has applied to join TiffinTrail with 'Sunita Bihari Litti Rasoi'. Verification is pending.", "/adminpanel/chefs/6/")
    ]

    for title, msg, link in admin_notifs:
        AdminNotification.objects.get_or_create(
            title=title,
            defaults={
                "message": msg,
                "notification_type": "chef_registration",
                "link": link,
                "is_read": False
            }
        )

    # Admin activity logs
    if admin_user:
        admin_logs = [
            ("Chef Verification: approved", "ChefProfile", "14", "Verification status set to Approved."),
            ("Chef Verification: approved", "ChefProfile", "13", "Verification status set to Approved."),
            ("Order Deleted", "Order", "5", "Order #TT-ORD-202610280502-DA9049 was permanently deleted by admin admin."),
            ("Order Deleted", "Order", "7", "Order #TT-ORD-202610280508-D117E8 was permanently deleted by admin admin.")
        ]
        for action, target_model, target_id, details in admin_logs:
            AdminActivityLog.objects.get_or_create(
                admin=admin_user,
                action=action,
                target_model=target_model,
                target_id=target_id,
                defaults={"details": details}
            )

    print("  [OK] Notifications and Logs seeded.")


# -----------------------------------------------------------------------------
# 3. Main Runner Function
# -----------------------------------------------------------------------------

def run_seed():
    """
    Executes the entire seeding workflow within an atomic database transaction.
    """
    print("=================================================================")
    print("        TIFFINTRAIL - ORIGINAL USER DATA SEEDER RUNNER           ")
    print("=================================================================")

    with transaction.atomic():
        users = seed_users()
        seed_customer_profile_and_address(users)
        chefs = seed_chefs(users)
        categories = seed_categories()
        meals = seed_meals(chefs, categories)
        meal_plans = seed_meal_plans(chefs)
        seed_coupons()
        seed_orders(users, chefs, meals)
        seed_subscriptions(users, chefs, meal_plans)
        seed_notifications_and_logs(users, chefs)

    print("\n=================================================================")
    print(" [OK] Original Data Seeding Completed Successfully!              ")
    print("=================================================================")
    print("Database summary:")
    print(f"  Users:           {User.objects.count()}")
    print(f"  Chefs:           {ChefProfile.objects.count()}")
    print(f"  Menu Categories: {MenuCategory.objects.count()}")
    print(f"  Meals:           {Meal.objects.count()}")
    print(f"  Meal Plans:      {MealPlan.objects.count()}")
    print(f"  Coupons:         {Coupon.objects.count()}")
    print(f"  Orders:          {Order.objects.count()}")
    print(f"  Subscriptions:   {Subscription.objects.count()}")
    print("=================================================================")


if __name__ == "__main__":
    run_seed()

