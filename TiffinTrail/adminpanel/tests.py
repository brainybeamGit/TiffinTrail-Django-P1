from datetime import timedelta
from decimal import Decimal
from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from chef.models import ChefProfile, Meal, MealPlan, MenuCategory, ChefNotification
from customer.models import Order, OrderItem, Subscription, Review, Coupon, CustomerProfile
from adminpanel.models import Complaint, AdminNotification, ChefVerificationLog, AdminActivityLog


class AdminPanelTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Admin superuser
        self.admin_user = User.objects.create_superuser(
            username='admin_boss',
            password='adminpassword123',
            email='admin@tiffintrail.com',
            first_name='Admin',
            last_name='Officer'
        )

        # Normal Customer
        self.customer_user = User.objects.create_user(
            username='customer_arun',
            password='password123',
            email='arun@example.com',
            first_name='Arun',
            last_name='Kumar'
        )
        self.customer_profile = CustomerProfile.objects.create(
            user=self.customer_user,
            phone='+91 91234 56789'
        )

        # Chef User & Profile
        self.chef_user = User.objects.create_user(
            username='chef_kavita',
            password='password123',
            email='kavita@example.com',
            first_name='Kavita',
            last_name='Singh'
        )
        self.chef = ChefProfile.objects.create(
            user=self.chef_user,
            business_name="Kavita's Rasoi",
            cuisines="North Indian, Awadhi",
            commission_rate=Decimal('10.00'),
            verification_status='pending',
            is_approved=False,
            is_active=True
        )

        # Category & Meal
        self.category = MenuCategory.objects.create(name='North Indian Thali', slug='north-indian-thali')
        self.meal = Meal.objects.create(
            chef=self.chef,
            category=self.category,
            name='Special Paneer Thali',
            price=Decimal('200.00'),
            is_veg=True,
            meal_type='lunch',
            is_available=True
        )

        # Meal Plan
        self.plan = MealPlan.objects.create(
            chef=self.chef,
            name='Weekly Executive Lunch',
            plan_type='weekly',
            duration_days=7,
            meals_per_day=1,
            price=Decimal('1200.00'),
            features='Hot daily lunch\nFree delivery',
            is_active=True
        )

        # Order
        self.order = Order.objects.create(
            user=self.customer_user,
            chef=self.chef,
            recipient_name='Arun Kumar',
            recipient_phone='9123456789',
            delivery_address_text='Indiranagar, Bengaluru',
            status='delivered',
            total_amount=Decimal('400.00'),
            delivery_fee=Decimal('0.00'),
            tax_amount=Decimal('20.00'),
            final_amount=Decimal('420.00'),
            payment_status='paid'
        )
        OrderItem.objects.create(
            order=self.order,
            meal=self.meal,
            meal_name=self.meal.name,
            unit_price=self.meal.price,
            quantity=2,
            subtotal=Decimal('400.00')
        )

        # Subscription
        self.sub = Subscription.objects.create(
            user=self.customer_user,
            chef=self.chef,
            plan=self.plan,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=7),
            recipient_name='Arun Kumar',
            recipient_phone='9123456789',
            delivery_address_text='Indiranagar, Bengaluru',
            status='active',
            total_amount=Decimal('1200.00'),
            payment_status='paid'
        )

        # Coupon
        self.coupon = Coupon.objects.create(
            code='WELCOME10',
            discount_type='percent',
            discount_value=Decimal('10.00'),
            min_order_amount=Decimal('100.00'),
            usage_limit=50,
            times_used=2,
            is_active=True
        )

        # Complaint
        self.complaint = Complaint.objects.create(
            customer=self.customer_user,
            chef=self.chef,
            order=self.order,
            category='delivery_delay',
            subject='Late Delivery on Thursday',
            description='Lunch meal reached at 2:30 PM instead of 1:00 PM.',
            priority='medium',
            status='open'
        )

        # Review
        self.review = Review.objects.create(
            user=self.customer_user,
            chef=self.chef,
            meal=self.meal,
            rating=5,
            comment='Excellent food, fresh and steaming hot!'
        )

    def test_unauthenticated_admin_redirect(self):
        """Unauthenticated user is redirected to admin login."""
        response = self.client.get(reverse('adminpanel:dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('adminpanel:login'), response.url)

    def test_non_staff_access_forbidden(self):
        """Normal customer cannot access the admin panel."""
        self.client.login(username='customer_arun', password='password123')
        response = self.client.get(reverse('adminpanel:dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('customer:home'))

    def test_admin_login_and_dashboard(self):
        """Administrator logs in and views dashboard metrics."""
        login_res = self.client.post(reverse('adminpanel:login'), {
            'username': 'admin_boss',
            'password': 'adminpassword123'
        })
        self.assertEqual(login_res.status_code, 302)
        self.assertRedirects(login_res, reverse('adminpanel:dashboard'))

        dash_res = self.client.get(reverse('adminpanel:dashboard'))
        self.assertEqual(dash_res.status_code, 200)
        self.assertContains(dash_res, "Total Customers")
        self.assertContains(dash_res, "Total Chefs")
        self.assertContains(dash_res, "Total Collected")

        # Check calculated metrics
        # Order: 420.00, Subscription: 1200.00 -> Total Collected = 1620.00
        self.assertEqual(dash_res.context['total_collected_amount'], Decimal('1620.00'))
        self.assertEqual(dash_res.context['pending_verifications'], 1)
        self.assertEqual(dash_res.context['pending_complaints_count'], 1)

    def test_customer_management(self):
        """Admin can list customers, view details, and toggle active status."""
        self.client.login(username='admin_boss', password='adminpassword123')

        # List
        list_res = self.client.get(reverse('adminpanel:customers'))
        self.assertEqual(list_res.status_code, 200)
        self.assertContains(list_res, "Arun")

        # Detail
        detail_res = self.client.get(reverse('adminpanel:customer_detail', args=[self.customer_user.id]))
        self.assertEqual(detail_res.status_code, 200)
        self.assertContains(detail_res, "Arun Kumar")

        # Toggle status
        toggle_res = self.client.post(reverse('adminpanel:customer_toggle_status', args=[self.customer_user.id]))
        self.assertEqual(toggle_res.status_code, 302)
        self.customer_user.refresh_from_db()
        self.assertFalse(self.customer_user.is_active)

    def test_chef_verification_workflow(self):
        """Admin can approve a pending chef application, which creates audit log and notifies chef."""
        self.client.login(username='admin_boss', password='adminpassword123')
        self.assertEqual(self.chef.verification_status, 'pending')
        self.assertFalse(self.chef.is_approved)

        verify_res = self.client.post(reverse('adminpanel:chef_verify_action', args=[self.chef.id]), {
            'action': 'approve',
            'notes': 'All FSSAI documents verified and approved.',
            'commission_rate': '10.00'
        })
        self.assertEqual(verify_res.status_code, 302)

        self.chef.refresh_from_db()
        self.assertEqual(self.chef.verification_status, 'approved')
        self.assertTrue(self.chef.is_approved)

        # Verify audit log created
        log = ChefVerificationLog.objects.filter(chef=self.chef, action='approved').first()
        self.assertIsNotNone(log)
        self.assertEqual(log.admin, self.admin_user)

        # Verify chef received notification
        notif = ChefNotification.objects.filter(chef=self.chef).first()
        self.assertIsNotNone(notif)
        self.assertIn("approved", notif.message.lower())

    def test_chef_delete_by_admin(self):
        """Admin can permanently delete a chef and associated account."""
        self.client.login(username='admin_boss', password='adminpassword123')
        chef_id = self.chef.id
        chef_user_id = self.chef_user.id

        delete_res = self.client.post(reverse('adminpanel:chef_delete', args=[chef_id]))
        self.assertEqual(delete_res.status_code, 302)
        self.assertRedirects(delete_res, reverse('adminpanel:chefs'))

        # Verify ChefProfile and User are deleted
        self.assertFalse(ChefProfile.objects.filter(id=chef_id).exists())
        self.assertFalse(User.objects.filter(id=chef_user_id).exists())

        # Verify activity log created
        log = AdminActivityLog.objects.filter(action="Chef Deleted", target_id=str(chef_id)).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.admin, self.admin_user)

    def test_chef_delete_requires_admin(self):
        """Non-admin / customer cannot delete a chef."""
        self.client.login(username='customer_arun', password='password123')
        chef_id = self.chef.id

        delete_res = self.client.post(reverse('adminpanel:chef_delete', args=[chef_id]))
        # Customer should be redirected away
        self.assertEqual(delete_res.status_code, 302)
        self.assertTrue(ChefProfile.objects.filter(id=chef_id).exists())

    def test_order_status_override(self):
        """Admin can override order fulfillment status with audit logging."""
        self.client.login(username='admin_boss', password='adminpassword123')

        res = self.client.post(reverse('adminpanel:order_detail', args=[self.order.id]), {
            'action': 'override_status',
            'new_status': 'confirmed',
            'reason': 'Customer requested delay in delivery window'
        })
        self.assertEqual(res.status_code, 302)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'confirmed')

        # Check activity log
        activity = AdminActivityLog.objects.filter(target_model='Order', target_id=str(self.order.id)).first()
        self.assertIsNotNone(activity)
        self.assertEqual(activity.admin, self.admin_user)

    def test_subscription_status_override(self):
        """Admin can override subscription status with audit justification."""
        self.client.login(username='admin_boss', password='adminpassword123')

        res = self.client.post(reverse('adminpanel:subscription_detail', args=[self.sub.id]), {
            'status': 'paused',
            'reason': 'Diner requested 3-day hold for out-of-town travel'
        })
        self.assertEqual(res.status_code, 302)
        self.sub.refresh_from_db()
        self.assertEqual(self.sub.status, 'paused')

    def test_complaint_resolution_workflow(self):
        """Admin can update ticket status, record internal notes, and customer response."""
        self.client.login(username='admin_boss', password='adminpassword123')

        update_res = self.client.post(reverse('adminpanel:complaint_detail', args=[self.complaint.id]), {
            'status': 'resolved',
            'priority': 'high',
            'assigned_admin': self.admin_user.id,
            'admin_notes': 'Spoke with delivery partner; traffic bottleneck resolved.',
            'customer_response': 'We deeply apologize for the delay. We have credited your account with a ₹50 discount.'
        })
        self.assertEqual(update_res.status_code, 302)
        self.complaint.refresh_from_db()
        self.assertEqual(self.complaint.status, 'resolved')
        self.assertIsNotNone(self.complaint.resolved_at)
        self.assertEqual(self.complaint.admin_notes, 'Spoke with delivery partner; traffic bottleneck resolved.')

    def test_coupon_crud_and_validation(self):
        """Admin can create new coupon and toggle active status."""
        self.client.login(username='admin_boss', password='adminpassword123')

        # Create coupon
        create_res = self.client.post(reverse('adminpanel:coupon_add'), {
            'code': 'FESTIVE25',
            'description': 'Festive discount',
            'discount_type': 'percent',
            'discount_value': '25.00',
            'min_order_amount': '250.00',
            'usage_limit': 100,
            'is_active': True
        })
        self.assertEqual(create_res.status_code, 302)
        new_cpn = Coupon.objects.filter(code='FESTIVE25').first()
        self.assertIsNotNone(new_cpn)

        # Toggle coupon status
        toggle_res = self.client.post(reverse('adminpanel:coupon_toggle', args=[new_cpn.id]))
        self.assertEqual(toggle_res.status_code, 302)
        new_cpn.refresh_from_db()
        self.assertFalse(new_cpn.is_active)

    def test_review_moderation(self):
        """Admin can hide inappropriate review from public display and restore it."""
        self.client.login(username='admin_boss', password='adminpassword123')
        self.assertFalse(self.review.is_hidden)

        # Hide review
        hide_res = self.client.post(reverse('adminpanel:review_toggle_hide', args=[self.review.id]), {
            'moderation_notes': 'Flagged for moderation check'
        })
        self.assertEqual(hide_res.status_code, 302)
        self.review.refresh_from_db()
        self.assertTrue(self.review.is_hidden)

    def test_reports_csv_generation(self):
        """Admin can generate date-filtered CSV report."""
        self.client.login(username='admin_boss', password='adminpassword123')
        today_str = timezone.now().strftime('%Y-%m-%d')

        res = self.client.get(reverse('adminpanel:reports'), {
            'report_type': 'orders',
            'start_date': today_str,
            'end_date': today_str,
            'export': 'csv'
        })
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'text/csv')
        self.assertIn('attachment;', res['Content-Disposition'])
        content = res.content.decode('utf-8')
        self.assertIn(self.order.order_number, content)

    def test_order_delete_by_admin(self):
        """Admin can permanently delete an order."""
        self.client.login(username='admin_boss', password='adminpassword123')
        order_id = self.order.id
        order_num = self.order.order_number

        delete_res = self.client.post(reverse('adminpanel:order_delete', args=[order_id]))
        self.assertEqual(delete_res.status_code, 302)
        self.assertRedirects(delete_res, reverse('adminpanel:orders'))

        # Verify Order is deleted
        self.assertFalse(Order.objects.filter(id=order_id).exists())

        # Verify activity log created
        log = AdminActivityLog.objects.filter(action="Order Deleted", target_id=str(order_id)).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.admin, self.admin_user)
        self.assertIn(order_num, log.details)

    def test_meal_plan_admin_management_lifecycle(self):
        """Admin can list, search, add, edit, toggle and delete subscription meal plans."""
        self.client.login(username='admin_boss', password='adminpassword123')

        # 1. List view & search
        list_res = self.client.get(reverse('adminpanel:plans'), {'q': self.plan.name})
        self.assertEqual(list_res.status_code, 200)
        self.assertContains(list_res, self.plan.name)

        # 2. Add plan
        create_res = self.client.post(reverse('adminpanel:plan_add'), {
            'name': 'Corporate Deluxe Weekly Plan',
            'description': 'Executive lunch plan with healthy dessert',
            'plan_type': 'weekly',
            'duration_days': 7,
            'meals_per_day': 1,
            'price': '1499.00',
            'original_price': '1800.00',
            'is_veg': True,
            'is_active': True,
            'features': "Fresh Chapatis\nPaneer Gravy\nOrganic Salad",
            'delivery_schedule': 'Lunch: 12:30 PM – 1:30 PM',
            'service_conditions': 'Cancel anytime',
        })
        self.assertEqual(create_res.status_code, 302)
        new_plan = MealPlan.objects.filter(name='Corporate Deluxe Weekly Plan').first()
        self.assertIsNotNone(new_plan)
        self.assertEqual(new_plan.price, Decimal('1499.00'))

        # 3. Edit plan
        edit_res = self.client.post(reverse('adminpanel:plan_edit', args=[new_plan.id]), {
            'name': 'Corporate Deluxe Weekly Plan Updated',
            'description': 'Executive lunch plan with healthy dessert and soup',
            'plan_type': 'weekly',
            'duration_days': 7,
            'meals_per_day': 1,
            'price': '1599.00',
            'original_price': '1800.00',
            'is_veg': True,
            'is_active': True,
            'features': "Fresh Chapatis\nPaneer Gravy\nOrganic Salad\nDaily Soup",
            'delivery_schedule': 'Lunch: 12:30 PM – 1:30 PM',
            'service_conditions': 'Cancel anytime',
        })
        self.assertEqual(edit_res.status_code, 302)
        new_plan.refresh_from_db()
        self.assertEqual(new_plan.name, 'Corporate Deluxe Weekly Plan Updated')
        self.assertEqual(new_plan.price, Decimal('1599.00'))

        # 4. Toggle plan status
        self.assertTrue(new_plan.is_active)
        toggle_res = self.client.post(reverse('adminpanel:plan_toggle', args=[new_plan.id]))
        self.assertEqual(toggle_res.status_code, 302)
        new_plan.refresh_from_db()
        self.assertFalse(new_plan.is_active)

        # 5. Delete plan (without active subscriptions) -> should be deleted
        delete_res = self.client.post(reverse('adminpanel:plan_delete', args=[new_plan.id]))
        self.assertEqual(delete_res.status_code, 302)
        self.assertFalse(MealPlan.objects.filter(id=new_plan.id).exists())

        # 6. Delete plan with active subscriptions (self.plan has self.sub which is active)
        # Should NOT delete, but deactivate to protect active customer orders
        del_active_res = self.client.post(reverse('adminpanel:plan_delete', args=[self.plan.id]))
        self.assertEqual(del_active_res.status_code, 302)
        self.assertTrue(MealPlan.objects.filter(id=self.plan.id).exists())
        self.plan.refresh_from_db()
        self.assertFalse(self.plan.is_active)

    def test_admin_meal_delete(self):
        """Admin can permanently delete any meal."""
        self.client.login(username='admin_boss', password='adminpassword123')
        meal_id = self.meal.id
        del_res = self.client.post(reverse('adminpanel:meal_delete', args=[meal_id]))
        self.assertEqual(del_res.status_code, 302)
        self.assertFalse(Meal.objects.filter(id=meal_id).exists())

        # Verify activity log
        log = AdminActivityLog.objects.filter(action="Meal Deleted", target_id=str(meal_id)).first()
        self.assertIsNotNone(log)

    def test_admin_subscription_delete(self):
        """Admin can permanently delete any customer subscription."""
        self.client.login(username='admin_boss', password='adminpassword123')
        sub_id = self.sub.id
        sub_num = self.sub.subscription_number
        del_res = self.client.post(reverse('adminpanel:subscription_delete', args=[sub_id]))
        self.assertEqual(del_res.status_code, 302)
        self.assertFalse(Subscription.objects.filter(id=sub_id).exists())

        # Verify activity log
        log = AdminActivityLog.objects.filter(action="Subscription Deleted", target_id=str(sub_id)).first()
        self.assertIsNotNone(log)
        self.assertIn(sub_num, log.details)


