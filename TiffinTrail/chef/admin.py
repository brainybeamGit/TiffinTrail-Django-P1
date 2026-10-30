from django.contrib import admin
from .models import ChefProfile, MenuCategory, Meal, MealPlan, DailyMenu, ChefNotification


@admin.register(ChefProfile)
class ChefProfileAdmin(admin.ModelAdmin):
    list_display = ('business_name', 'user', 'cuisines', 'rating', 'review_count', 'is_approved', 'is_active', 'is_accepting_orders', 'starting_price')
    list_filter = ('is_approved', 'is_active', 'is_accepting_orders')
    search_fields = ('business_name', 'user__username', 'user__email', 'cuisines', 'service_areas')
    prepopulated_fields = {'slug': ('business_name',)}


@admin.register(MenuCategory)
class MenuCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'display_order')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Meal)
class MealAdmin(admin.ModelAdmin):
    list_display = ('name', 'chef', 'category', 'meal_type', 'price', 'is_veg', 'available_quantity', 'is_available', 'is_featured', 'rating')
    list_filter = ('is_veg', 'is_available', 'is_featured', 'meal_type', 'category')
    search_fields = ('name', 'chef__business_name', 'description')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(MealPlan)
class MealPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'chef', 'plan_type', 'duration_days', 'meals_per_day', 'price', 'original_price', 'is_active')
    list_filter = ('plan_type', 'is_active', 'is_veg')
    search_fields = ('name', 'chef__business_name', 'description')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(DailyMenu)
class DailyMenuAdmin(admin.ModelAdmin):
    list_display = ('date', 'chef', 'meal', 'slot', 'available_quantity', 'is_available')
    list_filter = ('slot', 'is_available', 'date')
    search_fields = ('chef__business_name', 'meal__name')


@admin.register(ChefNotification)
class ChefNotificationAdmin(admin.ModelAdmin):
    list_display = ('chef', 'title', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('chef__business_name', 'title', 'message')
