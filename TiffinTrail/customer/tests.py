from decimal import Decimal
from datetime import timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from unittest.mock import patch, MagicMock

from chef.models import ChefProfile, MenuCategory, Meal, MealPlan
from customer.models import (
    CustomerProfile, DeliveryAddress, Coupon,
    Cart, CartItem, Order, OrderItem,
    Subscription, Review
)


class CustomerWebsiteTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Users
        self.user = User.objects.create_user(
            username='testcustomer',
            email='test@example.com',
            password='testpassword123',
            first_name='Test',
            last_name='Customer'
        )
        self.profile = CustomerProfile.objects.create(
            user=self.user,
            phone='9876543210'
        )

        self.other_user = User.objects.create_user(
            username='othercustomer',
            email='other@example.com',
            password='otherpassword123'
        )

        self.chef_user = User.objects.create_user(
            username='testchef',
            email='chef@example.com',
            password='chefpassword123'
        )
        self.chef = ChefProfile.objects.create(
            user=self.chef_user,
            business_name="Chef Sharma's Kitchen",
            bio="Homestyle cooking specialist",
            specialties="Dal Makhani, Thali",
            cuisines="North Indian, Punjabi",
            starting_price=Decimal('120.00'),
            service_areas="Indiranagar, Koramangala",
            is_approved=True,
            is_active=True
        )

        self.category = MenuCategory.objects.create(
            name="Thalis",
            slug="thalis"
        )

        self.meal = Meal.objects.create(
            chef=self.chef,
            category=self.category,
            name="Special Punjabi Thali",
            description="Dal, Sabzi, 3 Rotis, Rice",
            price=Decimal('150.00'),
            is_veg=True,
            is_available=True,
            is_featured=True
        )

        self.plan = MealPlan.objects.create(
            chef=self.chef,
            name="Weekly Punjabi Plan",
            description="7 days of healthy lunches",
            plan_type="weekly",
            duration_days=7,
            meals_per_day=1,
            price=Decimal('899.00'),
            original_price=Decimal('1050.00'),
            is_veg=True,
            features="7 Lunches\nDaily variation\nFree delivery"
        )

        self.coupon = Coupon.objects.create(
            code="SAVE20",
            discount_type="percent",
            discount_value=Decimal('20.00'),
            min_order_amount=Decimal('100.00'),
            is_active=True
        )

        self.address = DeliveryAddress.objects.create(
            user=self.user,
            title="Home",
            recipient_name="Test Customer",
            phone_number="9876543210",
            street_address="123 Main Street",
            area="Indiranagar",
            city="Bengaluru",
            pincode="560038",
            is_default=True
        )

    def test_homepage_loads(self):
        response = self.client.get(reverse('customer:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Chef Sharma")
        self.assertContains(response, "Special Punjabi Thali")
        self.assertContains(response, "Weekly Punjabi Plan")

    def test_chef_listing_and_search(self):
        # List
        response = self.client.get(reverse('customer:chefs'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Chef Sharma")

        # Search matching
        search_res = self.client.get(reverse('customer:chefs'), {'q': 'Sharma'})
        self.assertEqual(search_res.status_code, 200)
        self.assertContains(search_res, "Chef Sharma")

        # Search non-matching
        no_res = self.client.get(reverse('customer:chefs'), {'q': 'NonExistentChefXYZ'})
        self.assertEqual(no_res.status_code, 200)
        self.assertContains(no_res, "No Home Chefs Match Your Filters")

    def test_chef_detail_view(self):
        response = self.client.get(reverse('customer:chef_detail', kwargs={'pk': self.chef.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Chef Sharma")
        self.assertContains(response, "Special Punjabi Thali")

    def test_menu_catalog_and_filtering(self):
        response = self.client.get(reverse('customer:menu'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Special Punjabi Thali")

        # Filter veg
        veg_res = self.client.get(reverse('customer:menu'), {'diet': 'veg'})
        self.assertEqual(veg_res.status_code, 200)
        self.assertContains(veg_res, "Special Punjabi Thali")

    def test_meal_detail_view(self):
        response = self.client.get(reverse('customer:meal_detail', kwargs={'pk': self.meal.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Special Punjabi Thali")
        self.assertContains(response, "₹150.00")

    def test_cart_operations(self):
        # 1. Add to cart
        add_url = reverse('customer:cart_add', kwargs={'meal_id': self.meal.pk})
        res = self.client.post(add_url, {'quantity': 2}, follow=True)
        self.assertEqual(res.status_code, 200)

        cart = Cart.objects.first()
        self.assertIsNotNone(cart)
        self.assertEqual(cart.items_count, 2)
        self.assertEqual(cart.subtotal, Decimal('300.00'))

        # 2. Update quantity (increment)
        item = cart.items.first()
        update_url = reverse('customer:cart_update', kwargs={'item_id': item.pk})
        self.client.post(update_url, {'action': 'increment'}, follow=True)
        item.refresh_from_db()
        self.assertEqual(item.quantity, 3)

        # 3. Apply coupon
        coupon_url = reverse('customer:cart_apply_coupon')
        self.client.post(coupon_url, {'coupon_code': 'SAVE20'}, follow=True)
        cart.refresh_from_db()
        self.assertEqual(cart.coupon, self.coupon)
        self.assertGreater(cart.discount_amount, Decimal('0.00'))

        # 4. Remove item
        remove_url = reverse('customer:cart_remove', kwargs={'item_id': item.pk})
        self.client.post(remove_url, follow=True)
        self.assertEqual(cart.items.count(), 0)

    def test_checkout_and_order_creation(self):
        self.client.login(username='testcustomer', password='testpassword123')

        # Add item to cart
        self.client.post(reverse('customer:cart_add', kwargs={'meal_id': self.meal.pk}), {'quantity': 2})

        # Submit checkout
        checkout_data = {
            'recipient_name': 'Test Customer',
            'recipient_phone': '9876543210',
            'address_choice': str(self.address.id),
            'payment_method': 'cod',
        }
        res = self.client.post(reverse('customer:checkout'), checkout_data, follow=True)
        self.assertEqual(res.status_code, 200)

        # Check Order created
        order = Order.objects.filter(user=self.user).first()
        self.assertIsNotNone(order)
        self.assertEqual(order.chef, self.chef)
        self.assertEqual(order.payment_method, 'cod')
        self.assertEqual(order.payment_status, 'pending')
        self.assertEqual(order.total_amount, Decimal('300.00'))
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.items.first().unit_price, Decimal('150.00'))
        self.assertEqual(order.items.first().quantity, 2)

        # Verify cart was cleared
        cart = Cart.objects.filter(user=self.user).first()
        self.assertEqual(cart.items.count(), 0)

    def test_order_ownership_restriction(self):
        # Create order for testcustomer
        order = Order.objects.create(
            user=self.user,
            chef=self.chef,
            recipient_name='Test Customer',
            recipient_phone='9876543210',
            delivery_address_text='Indiranagar',
            total_amount=Decimal('150.00'),
            final_amount=Decimal('150.00')
        )

        # Login as other customer and attempt to view order
        self.client.login(username='othercustomer', password='otherpassword123')
        res = self.client.get(reverse('customer:order_detail', kwargs={'pk': order.pk}))
        # Must return 404 for non-owners
        self.assertEqual(res.status_code, 404)

        # Owner can view
        self.client.login(username='testcustomer', password='testpassword123')
        owner_res = self.client.get(reverse('customer:order_detail', kwargs={'pk': order.pk}))
        self.assertEqual(owner_res.status_code, 200)

    def test_subscription_creation_and_lifecycle(self):
        self.client.login(username='testcustomer', password='testpassword123')

        start_date = timezone.now().date() + timedelta(days=2)
        sub_data = {
            'chef_id': str(self.chef.id),
            'plan_id': str(self.plan.id),
            'start_date': start_date.strftime('%Y-%m-%d'),
            'delivery_slot': 'lunch',
            'dietary_preference': 'veg',
            'recipient_name': 'Test Customer',
            'recipient_phone': '9876543210',
            'address_choice': str(self.address.id),
            'payment_method': 'cod',
        }
        res = self.client.post(reverse('customer:subscribe'), sub_data, follow=True)
        self.assertEqual(res.status_code, 200)

        sub = Subscription.objects.filter(user=self.user).first()
        self.assertIsNotNone(sub)
        self.assertEqual(sub.status, 'active')
        self.assertEqual(sub.total_amount, self.plan.price)

        # Pause subscription
        self.client.post(reverse('customer:subscription_pause', kwargs={'pk': sub.pk}), follow=True)
        sub.refresh_from_db()
        self.assertEqual(sub.status, 'paused')

        # Resume subscription
        self.client.post(reverse('customer:subscription_resume', kwargs={'pk': sub.pk}), follow=True)
        sub.refresh_from_db()
        self.assertEqual(sub.status, 'active')

        # Cancel subscription
        self.client.post(reverse('customer:subscription_cancel', kwargs={'pk': sub.pk}), {'reason': 'Traveling'}, follow=True)
        sub.refresh_from_db()
        self.assertEqual(sub.status, 'cancelled')
        self.assertEqual(sub.cancellation_reason, 'Traveling')

    def test_review_creation_and_rating_update(self):
        self.client.login(username='testcustomer', password='testpassword123')

        review_data = {
            'chef_id': str(self.chef.id),
            'meal_id': str(self.meal.id),
            'rating': 5,
            'comment': 'Outstanding flavours and hot delivery!'
        }
        res = self.client.post(reverse('customer:add_review'), review_data, follow=True)
        self.assertEqual(res.status_code, 200)

        review = Review.objects.filter(user=self.user, chef=self.chef).first()
        self.assertIsNotNone(review)
        self.assertEqual(review.rating, 5)

        self.chef.refresh_from_db()
        self.assertEqual(self.chef.review_count, 1)
        self.assertEqual(self.chef.rating, Decimal('5.00'))

    def test_customer_auth_registration_and_login(self):
        # Register new user
        reg_data = {
            'username': 'newuser',
            'first_name': 'New',
            'last_name': 'Person',
            'email': 'newperson@example.com',
            'phone': '9123456789',
            'password': 'ComplexPassword123',
            'confirm_password': 'ComplexPassword123'
        }
        res = self.client.post(reverse('customer:register'), reg_data, follow=True)
        self.assertEqual(res.status_code, 200)

        new_user = User.objects.filter(username='newuser').first()
        self.assertIsNotNone(new_user)
        self.assertEqual(new_user.customer_profile.phone, '9123456789')

    @patch('razorpay.Client')
    def test_razorpay_order_create_view(self, mock_razorpay_client):
        self.client.login(username='testcustomer', password='testpassword123')

        # Empty cart check
        res = self.client.post(reverse('customer:razorpay_order_create'))
        self.assertEqual(res.status_code, 400)

        # Add item to cart
        self.client.post(reverse('customer:cart_add', kwargs={'meal_id': self.meal.id}), {'quantity': 2})

        # Mock razorpay order creation
        mock_instance = MagicMock()
        mock_instance.order.create.return_value = {
            'id': 'order_rzptest123456',
            'amount': 35000,
            'currency': 'INR',
            'status': 'created'
        }
        mock_razorpay_client.return_value = mock_instance

        create_data = {
            'recipient_name': 'Test Recipient',
            'recipient_phone': '9876543210'
        }
        res = self.client.post(reverse('customer:razorpay_order_create'), create_data)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['razorpay_order_id'], 'order_rzptest123456')
        self.assertEqual(data['key_id'], 'rzp_test_TBNsUzgbC9Y6kK')

    @patch('razorpay.Client')
    def test_razorpay_payment_verify_view(self, mock_razorpay_client):
        self.client.login(username='testcustomer', password='testpassword123')

        # Add item to cart
        self.client.post(reverse('customer:cart_add', kwargs={'meal_id': self.meal.id}), {'quantity': 1})

        # Mock razorpay verify
        mock_instance = MagicMock()
        mock_instance.utility.verify_payment_signature.return_value = True
        mock_razorpay_client.return_value = mock_instance

        verify_payload = {
            'recipient_name': 'Aarav Kumar',
            'recipient_phone': '9876543210',
            'street_address': 'Flat 204, Green Palms Apt',
            'area': 'Indiranagar',
            'city': 'Bengaluru',
            'pincode': '560038',
            'delivery_notes': 'Leave at door',
            'razorpay_payment_id': 'pay_test_99887766',
            'razorpay_order_id': 'order_rzptest123456',
            'razorpay_signature': 'test_signature_abc_123',
        }

        res = self.client.post(reverse('customer:razorpay_payment_verify'), verify_payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('redirect_url', data)

        # Check Order was created in DB
        order = Order.objects.filter(payment_transaction_id='pay_test_99887766').first()
        self.assertIsNotNone(order)
        self.assertEqual(order.payment_method, 'online')
        self.assertEqual(order.payment_status, 'paid')
        self.assertEqual(order.recipient_name, 'Aarav Kumar')

        # Check cart was cleared
        cart = Cart.objects.filter(user=self.user).first()
        self.assertEqual(cart.items.count(), 0)

    @patch('razorpay.Client')
    def test_razorpay_subscription_create_view(self, mock_razorpay_client):
        self.client.login(username='testcustomer', password='testpassword123')

        mock_instance = MagicMock()
        mock_instance.order.create.return_value = {
            'id': 'order_sub_rzptest123',
            'amount': int(self.plan.price * 100),
            'currency': 'INR',
            'status': 'created'
        }
        mock_razorpay_client.return_value = mock_instance

        create_data = {
            'chef_id': str(self.chef.id),
            'plan_id': str(self.plan.id),
            'recipient_name': 'Aarav Sub',
            'recipient_phone': '9876543210',
        }
        res = self.client.post(reverse('customer:razorpay_subscription_create'), create_data)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['razorpay_order_id'], 'order_sub_rzptest123')
        self.assertEqual(data['key_id'], 'rzp_test_TBNsUzgbC9Y6kK')
        self.assertEqual(data['amount'], int(self.plan.price * 100))

    @patch('razorpay.Client')
    def test_razorpay_subscription_verify_view(self, mock_razorpay_client):
        self.client.login(username='testcustomer', password='testpassword123')

        mock_instance = MagicMock()
        mock_instance.utility.verify_payment_signature.return_value = True
        mock_razorpay_client.return_value = mock_instance

        start_date = timezone.now().date() + timedelta(days=2)
        verify_payload = {
            'chef_id': str(self.chef.id),
            'plan_id': str(self.plan.id),
            'start_date': start_date.strftime('%Y-%m-%d'),
            'delivery_slot': 'lunch',
            'dietary_preference': 'veg',
            'recipient_name': 'Aarav Sub',
            'recipient_phone': '9876543210',
            'address_choice': str(self.address.id),
            'payment_method': 'online',
            'razorpay_payment_id': 'pay_sub_test_112233',
            'razorpay_order_id': 'order_sub_rzptest123',
            'razorpay_signature': 'test_signature_sub_xyz',
        }

        res = self.client.post(reverse('customer:razorpay_subscription_verify'), verify_payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('redirect_url', data)

        # Check Subscription was created in DB
        sub = Subscription.objects.filter(payment_transaction_id='pay_sub_test_112233').first()
        self.assertIsNotNone(sub)
        self.assertEqual(sub.status, 'active')
        self.assertEqual(sub.payment_method, 'online')
        self.assertEqual(sub.payment_status, 'paid')
        self.assertEqual(sub.recipient_name, 'Aarav Sub')
        self.assertEqual(sub.total_amount, self.plan.price)

    def test_subscription_online_unverified_post_rejected(self):
        self.client.login(username='testcustomer', password='testpassword123')

        start_date = timezone.now().date() + timedelta(days=2)
        sub_data = {
            'chef_id': str(self.chef.id),
            'plan_id': str(self.plan.id),
            'start_date': start_date.strftime('%Y-%m-%d'),
            'delivery_slot': 'lunch',
            'dietary_preference': 'veg',
            'recipient_name': 'Test Online Customer',
            'recipient_phone': '9876543210',
            'address_choice': str(self.address.id),
            'payment_method': 'online',
        }
        res = self.client.post(reverse('customer:subscribe'), sub_data, follow=True)
        # Should redirect with error message
        self.assertEqual(res.status_code, 200)
        # Subscription should NOT be created
        self.assertFalse(Subscription.objects.filter(recipient_name='Test Online Customer').exists())


class PromotionalDescriptionWorkflowTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username='admin_test',
            email='admin@tiffintrail.test',
            password='adminpassword123'
        )
        self.customer_user = User.objects.create_user(
            username='customer_test',
            email='customer@tiffintrail.test',
            password='customerpassword123'
        )
        self.profile = CustomerProfile.objects.create(
            user=self.customer_user,
            phone='9876543210'
        )
        self.chef_user = User.objects.create_user(
            username='chef_test',
            password='chefpassword123'
        )
        self.chef = ChefProfile.objects.create(
            user=self.chef_user,
            business_name="Swad Kitchen",
            cuisines="North Indian",
            specialties="Thali",
            service_areas="Indiranagar",
            is_approved=True,
            is_active=True
        )
        self.category = MenuCategory.objects.create(name="Lunch Combos", display_order=1)
        self.meal = Meal.objects.create(
            chef=self.chef,
            category=self.category,
            name="Deluxe North Indian Thali",
            description="Complete wholesome lunch meal",
            price=Decimal('250.00'),
            is_veg=True,
            is_available=True
        )

    def test_complete_promotional_description_workflow(self):
        """
        End-to-end test:
        1. Admin creates a coupon with a promotional description.
        2. Description is saved in the database.
        3. Customer opens Available Coupons.
        4. Customer sees the exact description entered by Admin.
        5. Admin edits the description.
        6. Customer sees the updated description.
        7. Customer applies the coupon.
        8. Coupon discount and description are displayed correctly.
        """
        # Step 1: Admin logs in and creates a coupon
        self.client.login(username='admin_test', password='adminpassword123')
        create_res = self.client.post(reverse('adminpanel:coupon_add'), {
            'code': 'FESTIVE50',
            'description': 'Get 50% off on your first meal order.',
            'discount_type': 'percent',
            'discount_value': '50.00',
            'min_order_amount': '200.00',
            'max_discount_amount': '100.00',
            'usage_limit': 100,
            'is_active': True,
        })
        self.assertEqual(create_res.status_code, 302)

        # Step 2: Description is saved in the database
        coupon = Coupon.objects.filter(code='FESTIVE50').first()
        self.assertIsNotNone(coupon)
        self.assertEqual(coupon.description, 'Get 50% off on your first meal order.')

        # Step 3 & 4: Customer logs in, adds item to cart, and views Available Coupons on Cart & Checkout
        self.client.login(username='customer_test', password='customerpassword123')
        self.client.post(reverse('customer:cart_add', kwargs={'meal_id': self.meal.pk}), {'quantity': 1})

        # Cart page
        cart_res = self.client.get(reverse('customer:cart'))
        self.assertEqual(cart_res.status_code, 200)
        self.assertContains(cart_res, 'FESTIVE50')
        self.assertContains(cart_res, 'Get 50% off on your first meal order.')

        # Checkout page
        checkout_res = self.client.get(reverse('customer:checkout'))
        self.assertEqual(checkout_res.status_code, 200)
        self.assertContains(checkout_res, 'FESTIVE50')
        self.assertContains(checkout_res, 'Get 50% off on your first meal order.')

        # Step 5: Admin edits the promotional description
        self.client.login(username='admin_test', password='adminpassword123')
        edit_res = self.client.post(reverse('adminpanel:coupon_edit', args=[coupon.id]), {
            'code': 'FESTIVE50',
            'description': 'Get 50% off on all weekend special thalis.',
            'discount_type': 'percent',
            'discount_value': '50.00',
            'min_order_amount': '200.00',
            'max_discount_amount': '100.00',
            'usage_limit': 100,
            'is_active': True,
        })
        self.assertEqual(edit_res.status_code, 302)
        coupon.refresh_from_db()
        self.assertEqual(coupon.description, 'Get 50% off on all weekend special thalis.')

        # Step 6: Customer views the updated description dynamically
        self.client.login(username='customer_test', password='customerpassword123')
        checkout_updated = self.client.get(reverse('customer:checkout'))
        self.assertEqual(checkout_updated.status_code, 200)
        self.assertContains(checkout_updated, 'Get 50% off on all weekend special thalis.')
        self.assertNotContains(checkout_updated, 'Get 50% off on your first meal order.')

        # Step 7 & 8: Customer applies the coupon
        apply_res = self.client.post(reverse('customer:cart_apply_coupon'), {
            'coupon_code': 'FESTIVE50',
            'next': reverse('customer:checkout'),
        }, follow=True)
        self.assertEqual(apply_res.status_code, 200)
        self.assertContains(apply_res, 'FESTIVE50 applied successfully!')
        self.assertContains(apply_res, 'Get 50% off on all weekend special thalis.')

        # Verify discount applied on cart
        cart = Cart.objects.filter(user=self.customer_user).first()
        self.assertEqual(cart.coupon, coupon)
        self.assertEqual(cart.discount_amount, Decimal('100.00'))  # 50% of 250 is 125, capped at 100
        self.assertEqual(cart.final_total, cart.subtotal + cart.delivery_fee + cart.tax_amount - Decimal('100.00'))

    def test_coupon_card_details_and_field_preservation(self):
        """
        Tests:
        - Promotional description is displayed below coupon code.
        - Discount value, min order, max discount cap, expiry date, Apply button are present.
        - Editing another coupon field preserves the existing promotional description.
        - Deleting coupon removes it immediately from customer view.
        """
        future_date = timezone.now() + timedelta(days=30)
        coupon = Coupon.objects.create(
            code='SPECIAL40',
            description='Flat 40% discount on healthy diet tiffins.',
            discount_type='percent',
            discount_value=Decimal('40.00'),
            min_order_amount=Decimal('180.00'),
            max_discount_amount=Decimal('80.00'),
            valid_until=future_date,
            is_active=True
        )

        # Customer views coupon details on checkout
        self.client.login(username='customer_test', password='customerpassword123')
        self.client.post(reverse('customer:cart_add', kwargs={'meal_id': self.meal.pk}), {'quantity': 1})

        checkout_res = self.client.get(reverse('customer:checkout'))
        self.assertContains(checkout_res, 'SPECIAL40')
        self.assertContains(checkout_res, 'Flat 40% discount on healthy diet tiffins.')
        self.assertContains(checkout_res, '40% OFF')
        self.assertContains(checkout_res, 'Min. order:')
        self.assertContains(checkout_res, 'Max. discount:')
        self.assertContains(checkout_res, 'Apply Coupon')

        # Admin edits another field (e.g. min_order_amount) without changing description
        self.client.login(username='admin_test', password='adminpassword123')
        edit_res = self.client.post(reverse('adminpanel:coupon_edit', args=[coupon.id]), {
            'code': 'SPECIAL40',
            'description': 'Flat 40% discount on healthy diet tiffins.',
            'discount_type': 'percent',
            'discount_value': '40.00',
            'min_order_amount': '220.00',  # Changed min order
            'max_discount_amount': '80.00',
            'usage_limit': 100,
            'is_active': True,
        }, follow=True)
        self.assertEqual(edit_res.status_code, 200)
        coupon.refresh_from_db()
        self.assertEqual(coupon.min_order_amount, Decimal('220.00'))
        # Promotional description is preserved
        self.assertEqual(coupon.description, 'Flat 40% discount on healthy diet tiffins.')

        # Delete coupon -> disappears from listings
        coupon.delete()
        self.client.login(username='customer_test', password='customerpassword123')
        checkout_res2 = self.client.get(reverse('customer:checkout'))
        self.assertNotContains(checkout_res2, 'SPECIAL40')
        self.assertNotContains(checkout_res2, 'Flat 40% discount on healthy diet tiffins.')

    def test_min_order_amount_enforcement(self):
        """Coupon cannot be applied if cart subtotal is below min_order_amount."""
        coupon = Coupon.objects.create(
            code='BIGORDER',
            description='Get ₹150 off on orders above ₹500.',
            discount_type='fixed',
            discount_value=Decimal('150.00'),
            min_order_amount=Decimal('500.00'),
            is_active=True
        )
        self.client.login(username='customer_test', password='customerpassword123')
        # Meal price is 250, subtotal 250 < 500
        self.client.post(reverse('customer:cart_add', kwargs={'meal_id': self.meal.pk}), {'quantity': 1})
        apply_res = self.client.post(reverse('customer:cart_apply_coupon'), {
            'coupon_code': 'BIGORDER',
            'next': reverse('customer:checkout'),
        }, follow=True)
        self.assertContains(apply_res, "Minimum order amount of ₹500.00 required.")
        cart = Cart.objects.filter(user=self.customer_user).first()
        self.assertIsNone(cart.coupon)

    def test_inactive_and_expired_coupons_filtered_out(self):
        """Inactive or expired coupons do not appear in available coupons and cannot be applied."""
        now = timezone.now()
        expired_cpn = Coupon.objects.create(
            code='EXPIRED10',
            description='Expired promo offer',
            discount_type='fixed',
            discount_value=Decimal('50.00'),
            min_order_amount=Decimal('100.00'),
            is_active=True,
            valid_until=now - timedelta(days=2)
        )
        inactive_cpn = Coupon.objects.create(
            code='INACTIVE20',
            description='Inactive promo offer',
            discount_type='fixed',
            discount_value=Decimal('50.00'),
            min_order_amount=Decimal('100.00'),
            is_active=False
        )
        exhausted_cpn = Coupon.objects.create(
            code='EXHAUSTED30',
            description='Exhausted promo offer',
            discount_type='fixed',
            discount_value=Decimal('50.00'),
            min_order_amount=Decimal('100.00'),
            usage_limit=5,
            times_used=5,
            is_active=True
        )

        available = Coupon.get_available_coupons()
        available_codes = list(available.values_list('code', flat=True))
        self.assertNotIn('EXPIRED10', available_codes)
        self.assertNotIn('INACTIVE20', available_codes)
        self.assertNotIn('EXHAUSTED30', available_codes)

        # Attempt to apply inactive coupon
        self.client.login(username='customer_test', password='customerpassword123')
        self.client.post(reverse('customer:cart_add', kwargs={'meal_id': self.meal.pk}), {'quantity': 1})
        res = self.client.post(reverse('customer:cart_apply_coupon'), {'coupon_code': 'INACTIVE20'}, follow=True)
        self.assertContains(res, "Coupon code &#x27;INACTIVE20&#x27; is invalid or expired.")

