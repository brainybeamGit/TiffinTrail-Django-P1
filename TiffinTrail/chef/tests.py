from datetime import timedelta
from decimal import Decimal
from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from chef.models import ChefProfile, Meal, MealPlan, MenuCategory, DailyMenu, ChefNotification
from customer.models import Order, OrderItem, Subscription, Review


class ChefDashboardTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Chef 1
        self.chef1_user = User.objects.create_user(
            username='chef_amrita',
            password='password123',
            email='amrita@example.com',
            first_name='Amrita',
            last_name='Kaur'
        )
        self.chef1 = ChefProfile.objects.create(
            user=self.chef1_user,
            business_name="Amrita's Punjabi Rasoi",
            cuisines="North Indian, Punjabi",
            specialties="Dal Makhani, Phulka Thali",
            service_areas="Indiranagar, Koramangala",
            phone="+91 98765 43210",
            commission_rate=Decimal('10.00'),
            is_approved=True,
            is_active=True
        )

        # Chef 2 (for cross-chef security checks)
        self.chef2_user = User.objects.create_user(
            username='chef_rajeshwari',
            password='password123',
            email='rajeshwari@example.com',
            first_name='Rajeshwari',
            last_name='Iyer'
        )
        self.chef2 = ChefProfile.objects.create(
            user=self.chef2_user,
            business_name="Rajeshwari's South Kitchen",
            cuisines="South Indian, Tamil",
            commission_rate=Decimal('10.00'),
            is_approved=True,
            is_active=True
        )

        # Regular Customer
        self.customer_user = User.objects.create_user(
            username='priya_customer',
            password='password123',
            email='priya@example.com'
        )

        # Category
        self.category = MenuCategory.objects.create(name='North Indian Thalis', slug='north-indian-thalis')

        # Meals for Chef 1
        self.meal1 = Meal.objects.create(
            chef=self.chef1,
            category=self.category,
            name='Dal Makhani Thali',
            price=Decimal('180.00'),
            is_veg=True,
            meal_type='lunch',
            available_quantity=25,
            is_available=True
        )

        # Meal for Chef 2
        self.meal2 = Meal.objects.create(
            chef=self.chef2,
            name='Sambar Rice Combo',
            price=Decimal('120.00'),
            is_veg=True,
            meal_type='lunch',
            is_available=True
        )

        # Meal Plan for Chef 1
        self.plan1 = MealPlan.objects.create(
            chef=self.chef1,
            name='Weekly Punjabi Lunch Plan',
            plan_type='weekly',
            duration_days=7,
            meals_per_day=1,
            price=Decimal('1150.00'),
            features='Daily varied Dal\n3 Soft Phulkas\nSalad & Raita',
            is_active=True
        )

        # Orders for Chef 1
        self.order1 = Order.objects.create(
            user=self.customer_user,
            chef=self.chef1,
            recipient_name='Priya Sharma',
            recipient_phone='9876500000',
            delivery_address_text='Flat 204, Indiranagar, Bengaluru',
            status='pending',
            total_amount=Decimal('180.00'),
            delivery_fee=Decimal('35.00'),
            tax_amount=Decimal('9.00'),
            final_amount=Decimal('224.00'),
            payment_status='paid'
        )
        self.order_item1 = OrderItem.objects.create(
            order=self.order1,
            meal=self.meal1,
            meal_name=self.meal1.name,
            unit_price=self.meal1.price,
            quantity=1,
            subtotal=Decimal('180.00')
        )

        # Completed order for earnings calculation
        self.delivered_order = Order.objects.create(
            user=self.customer_user,
            chef=self.chef1,
            recipient_name='Priya Sharma',
            recipient_phone='9876500000',
            delivery_address_text='Flat 204, Indiranagar, Bengaluru',
            status='delivered',
            total_amount=Decimal('360.00'),
            delivery_fee=Decimal('0.00'),
            tax_amount=Decimal('18.00'),
            final_amount=Decimal('378.00'),
            payment_status='paid'
        )

        # Subscription for Chef 1
        self.sub1 = Subscription.objects.create(
            user=self.customer_user,
            chef=self.chef1,
            plan=self.plan1,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=7),
            recipient_name='Priya Sharma',
            recipient_phone='9876500000',
            delivery_address_text='Indiranagar, Bengaluru',
            status='active',
            total_amount=Decimal('1150.00'),
            payment_status='paid'
        )

        # Notification for Chef 1
        self.notif1 = ChefNotification.objects.create(
            chef=self.chef1,
            title='New Order Received',
            message='Order TT-ORD-123 has been placed.',
            notification_type='order'
        )

    def test_unauthenticated_redirect(self):
        """Unauthenticated user is redirected to chef login."""
        response = self.client.get(reverse('chef:dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('chef:login'), response.url)

    def test_non_chef_access_restricted(self):
        """Regular customer cannot access chef dashboard."""
        self.client.login(username='priya_customer', password='password123')
        response = self.client.get(reverse('chef:dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('customer:home'))

    def test_chef_login_success(self):
        """Chef logs in and sees dashboard."""
        login_res = self.client.post(reverse('chef:login'), {
            'username': 'chef_amrita',
            'password': 'password123'
        })
        self.assertEqual(login_res.status_code, 302)
        self.assertRedirects(login_res, reverse('chef:dashboard'))

        dash_res = self.client.get(reverse('chef:dashboard'))
        self.assertEqual(dash_res.status_code, 200)
        self.assertContains(dash_res, "Amrita")
        self.assertContains(dash_res, "Total Orders")

    def test_dashboard_earnings_math(self):
        """Verify accurate net revenue calculation (Gross - 10% platform commission)."""
        self.client.login(username='chef_amrita', password='password123')
        response = self.client.get(reverse('chef:dashboard'))
        self.assertEqual(response.status_code, 200)

        # Gross from delivered order is 378.00
        # 10% commission = 37.80, Net earnings = 340.20
        self.assertEqual(response.context['gross_revenue'], Decimal('378.00'))
        self.assertEqual(response.context['platform_commission'], Decimal('37.80'))
        self.assertEqual(response.context['net_earnings'], Decimal('340.20'))

    def test_meal_crud_and_ownership(self):
        """Chef can create and edit their meals, but cannot edit another chef's meal."""
        self.client.login(username='chef_amrita', password='password123')

        # Add meal
        add_res = self.client.post(reverse('chef:meal_add'), {
            'name': 'Paneer Bhurji Combo',
            'category': self.category.id,
            'meal_type': 'dinner',
            'price': '195.00',
            'is_veg': True,
            'cuisine': 'Punjabi',
            'calories': 480,
            'preparation_time': 20,
            'available_quantity': 15,
            'is_available': True,
            'description': 'Fresh crumbled paneer sauteed with onions and tomatoes.'
        })
        self.assertEqual(add_res.status_code, 302)
        new_meal = Meal.objects.filter(name='Paneer Bhurji Combo', chef=self.chef1).first()
        self.assertIsNotNone(new_meal)

        # Edit meal
        edit_res = self.client.post(reverse('chef:meal_edit', args=[new_meal.id]), {
            'name': 'Paneer Bhurji Combo (Updated)',
            'category': self.category.id,
            'meal_type': 'dinner',
            'price': '210.00',
            'is_veg': True,
            'cuisine': 'Punjabi',
            'calories': 500,
            'preparation_time': 25,
            'available_quantity': 20,
            'is_available': True,
            'description': 'Updated description.'
        })
        self.assertEqual(edit_res.status_code, 302)
        new_meal.refresh_from_db()
        self.assertEqual(new_meal.name, 'Paneer Bhurji Combo (Updated)')
        self.assertEqual(new_meal.price, Decimal('210.00'))

        # Security: Chef 1 cannot edit Chef 2's meal (should return 404)
        cross_res = self.client.get(reverse('chef:meal_edit', args=[self.meal2.id]))
        self.assertEqual(cross_res.status_code, 404)

    def test_daily_menu_scheduling(self):
        """Chef can schedule meals for specific dates and slots."""
        self.client.login(username='chef_amrita', password='password123')
        target_date = timezone.now().date() + timedelta(days=1)

        post_res = self.client.post(reverse('chef:daily_menu_add'), {
            'meal': self.meal1.id,
            'date': target_date.strftime('%Y-%m-%d'),
            'slot': 'lunch',
            'available_quantity': 30,
            'is_available': True,
            'special_notes': 'Served with hot phulkas'
        })
        self.assertEqual(post_res.status_code, 302)

        scheduled = DailyMenu.objects.filter(chef=self.chef1, meal=self.meal1, date=target_date, slot='lunch').first()
        self.assertIsNotNone(scheduled)
        self.assertEqual(scheduled.available_quantity, 30)

    def test_order_status_workflow(self):
        """Chef can advance order status through permitted transitions."""
        self.client.login(username='chef_amrita', password='password123')

        # 1. Pending -> Confirmed
        res1 = self.client.post(reverse('chef:order_status_update', args=[self.order1.id]), {
            'new_status': 'confirmed'
        })
        self.assertEqual(res1.status_code, 302)
        self.order1.refresh_from_db()
        self.assertEqual(self.order1.status, 'confirmed')

        # 2. Confirmed -> Preparing
        res2 = self.client.post(reverse('chef:order_status_update', args=[self.order1.id]), {
            'new_status': 'preparing'
        })
        self.assertEqual(res2.status_code, 302)
        self.order1.refresh_from_db()
        self.assertEqual(self.order1.status, 'preparing')

        # 3. Invalid transition test: Preparing directly to Delivered is not allowed
        res_invalid = self.client.post(reverse('chef:order_status_update', args=[self.order1.id]), {
            'new_status': 'delivered'
        })
        self.order1.refresh_from_db()
        self.assertEqual(self.order1.status, 'preparing')  # Unchanged

        # 4. Preparing -> Out for Delivery
        res3 = self.client.post(reverse('chef:order_status_update', args=[self.order1.id]), {
            'new_status': 'out_for_delivery'
        })
        self.order1.refresh_from_db()
        self.assertEqual(self.order1.status, 'out_for_delivery')

        # 5. Out for Delivery -> Delivered
        res4 = self.client.post(reverse('chef:order_status_update', args=[self.order1.id]), {
            'new_status': 'delivered'
        })
        self.order1.refresh_from_db()
        self.assertEqual(self.order1.status, 'delivered')

    def test_cross_chef_order_isolation(self):
        """Chef 2 cannot access or modify Chef 1's orders."""
        self.client.login(username='chef_rajeshwari', password='password123')

        # Chef 2 trying to view Chef 1's order -> 404
        res = self.client.get(reverse('chef:order_detail', args=[self.order1.id]))
        self.assertEqual(res.status_code, 404)

        # Chef 2 trying to update Chef 1's order -> 404
        update_res = self.client.post(reverse('chef:order_status_update', args=[self.order1.id]), {
            'new_status': 'confirmed'
        })
        self.assertEqual(update_res.status_code, 404)

    def test_notifications_read(self):
        """Chef can mark notifications as read."""
        self.client.login(username='chef_amrita', password='password123')
        self.assertFalse(self.notif1.is_read)

        mark_res = self.client.post(reverse('chef:notification_mark_read', args=[self.notif1.id]))
        self.assertEqual(mark_res.status_code, 302)
        self.notif1.refresh_from_db()
        self.assertTrue(self.notif1.is_read)

    def test_kitchen_settings_order_toggle(self):
        """Chef can pause or open kitchen ordering."""
        self.client.login(username='chef_amrita', password='password123')
        self.assertTrue(self.chef1.is_accepting_orders)

        res = self.client.post(reverse('chef:settings'), {'action': 'toggle_orders'})
        self.assertEqual(res.status_code, 302)
        self.chef1.refresh_from_db()
        self.assertFalse(self.chef1.is_accepting_orders)

    def test_chef_meal_delete(self):
        """Chef can delete their meal."""
        self.client.login(username='chef_amrita', password='password123')
        meal_id = self.meal1.id
        del_res = self.client.post(reverse('chef:meal_delete', args=[meal_id]))
        self.assertEqual(del_res.status_code, 302)
        self.assertFalse(Meal.objects.filter(id=meal_id).exists())

    def test_chef_subscription_delete(self):
        """Chef can delete a subscription assigned to their kitchen."""
        self.client.login(username='chef_amrita', password='password123')
        sub_id = self.sub1.id
        del_res = self.client.post(reverse('chef:subscription_delete', args=[sub_id]))
        self.assertEqual(del_res.status_code, 302)
        self.assertFalse(Subscription.objects.filter(id=sub_id).exists())

    def test_chef_plan_delete(self):
        """Chef can delete their meal plan."""
        self.client.login(username='chef_amrita', password='password123')
        plan = MealPlan.objects.create(
            chef=self.chef1,
            name='Temporary Plan',
            description='Test Plan',
            price=Decimal('500.00'),
            duration_days=5
        )
        del_res = self.client.post(reverse('chef:plan_delete', args=[plan.id]))
        self.assertEqual(del_res.status_code, 302)
        self.assertFalse(MealPlan.objects.filter(id=plan.id).exists())
