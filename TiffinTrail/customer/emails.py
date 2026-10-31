"""
Email service module for TiffinTrail.
Handles order confirmation, status updates, subscriptions,
customer welcome, and chef registration emails
using Django's EmailMultiAlternatives with rich HTML and text templates.
Supports non-blocking asynchronous email delivery.
"""

import logging
import threading
from datetime import datetime
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


def _safe_str(val):
    """Safely encodes a string for printing to environments with ascii/cp1252 limits."""
    if isinstance(val, str):
        return val.encode('ascii', errors='replace').decode('ascii')
    return str(val)


def _send_email_worker(subject, text_content, html_content, recipients, from_email):
    """Worker function executed inside a thread or synchronously."""
    safe_subj = _safe_str(subject)
    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=recipients
        )
        if html_content:
            msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)
        logger.info(f"[EMAIL SUCCESS] '{safe_subj}' sent to {recipients}")
        print(f"[EMAIL SUCCESS] Email '{safe_subj}' sent to: {', '.join(recipients)}")
        return True
    except Exception as exc:
        logger.error(f"[EMAIL ERROR] Failed to send '{safe_subj}' to {recipients}: {exc}", exc_info=True)
        print(f"[EMAIL ERROR] Failed to send email '{safe_subj}': {exc}")
        return False


def _get_order_recipients(order):
    """
    Returns verified recipient list containing:
    1. The customer (order.user.email)
    2. The store owner / admin (settings.EMAIL_HOST_USER)
    Avoids duplicates and empty strings.
    """
    recipients = []
    
    # 1. Customer email
    if order.user and order.user.email and '@' in order.user.email:
        recipients.append(order.user.email.strip())

    # 2. Store Owner / Admin email (so the user is always notified)
    owner_email = getattr(settings, 'EMAIL_HOST_USER', None)
    if owner_email and '@' in owner_email and owner_email.strip() not in recipients:
        recipients.append(owner_email.strip())

    return recipients


def send_order_confirmation_email(order, async_send=True):
    """
    Sends rich HTML + Text Order Confirmation email when an order is placed/confirmed.
    Recipients: Customer and Store Owner (EMAIL_HOST_USER).
    """
    try:
        recipients = _get_order_recipients(order)
        if not recipients:
            logger.warning(f"[EMAIL SKIPPED] No valid recipients found for Order #{order.order_number}")
            return False

        site_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
        support_email = getattr(settings, 'EMAIL_HOST_USER', 'lakumdharmesh799@gmail.com')
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', f"TiffinTrail <{support_email}>")

        subject = f"Order Confirmed: #{order.order_number} | TiffinTrail"

        context = {
            'order': order,
            'site_url': site_url,
            'support_email': support_email,
            'current_year': datetime.now().year,
        }

        # Render HTML and Plain text templates
        try:
            html_content = render_to_string('customer/emails/order_confirmation.html', context)
        except Exception:
            html_content = None

        try:
            text_content = render_to_string('customer/emails/order_confirmation.txt', context)
        except Exception:
            text_content = strip_tags(html_content) if html_content else f"Order #{order.order_number} Confirmed! Total: Rs. {order.final_amount}"

        if async_send:
            thread = threading.Thread(
                target=_send_email_worker,
                args=(subject, text_content, html_content, recipients, from_email),
                daemon=True
            )
            thread.start()
            return True
        else:
            return _send_email_worker(subject, text_content, html_content, recipients, from_email)

    except Exception as exc:
        logger.error(f"[EMAIL ERROR] Exception in send_order_confirmation_email: {exc}", exc_info=True)
        return False


def send_order_status_update_email(order, new_status, async_send=True):
    """
    Sends email notification when an order status is updated (e.g. Confirmed by Chef, Out for Delivery, Delivered).
    """
    try:
        recipients = _get_order_recipients(order)
        if not recipients:
            return False

        site_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
        support_email = getattr(settings, 'EMAIL_HOST_USER', 'lakumdharmesh799@gmail.com')
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', f"TiffinTrail <{support_email}>")

        status_display = order.get_status_display()
        subject = f"Order #{order.order_number} Update: {status_display} | TiffinTrail"

        context = {
            'order': order,
            'status_display': status_display,
            'site_url': site_url,
            'support_email': support_email,
            'current_year': datetime.now().year,
        }

        try:
            html_content = render_to_string('customer/emails/order_status_update.html', context)
        except Exception:
            html_content = None

        try:
            text_content = render_to_string('customer/emails/order_status_update.txt', context)
        except Exception:
            text_content = strip_tags(html_content) if html_content else f"Order #{order.order_number} status updated to {status_display}"

        if async_send:
            thread = threading.Thread(
                target=_send_email_worker,
                args=(subject, text_content, html_content, recipients, from_email),
                daemon=True
            )
            thread.start()
            return True
        else:
            return _send_email_worker(subject, text_content, html_content, recipients, from_email)

    except Exception as exc:
        logger.error(f"[EMAIL ERROR] Exception in send_order_status_update_email: {exc}", exc_info=True)
        return False


def send_subscription_confirmation_email(sub, async_send=True):
    """
    Sends email notification when a meal plan subscription is created/confirmed.
    Recipients: Customer and Store Owner (EMAIL_HOST_USER).
    """
    try:
        recipients = []
        if sub.user and sub.user.email and '@' in sub.user.email:
            recipients.append(sub.user.email.strip())

        owner_email = getattr(settings, 'EMAIL_HOST_USER', None)
        if owner_email and '@' in owner_email and owner_email.strip() not in recipients:
            recipients.append(owner_email.strip())

        if not recipients:
            return False

        site_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
        support_email = getattr(settings, 'EMAIL_HOST_USER', 'lakumdharmesh799@gmail.com')
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', f"TiffinTrail <{support_email}>")

        subject = f"Subscription Confirmed: #{sub.subscription_number} | TiffinTrail"

        context = {
            'sub': sub,
            'site_url': site_url,
            'support_email': support_email,
            'current_year': datetime.now().year,
        }

        try:
            html_content = render_to_string('customer/emails/subscription_confirmation.html', context)
        except Exception:
            html_content = None

        try:
            text_content = render_to_string('customer/emails/subscription_confirmation.txt', context)
        except Exception:
            text_content = strip_tags(html_content) if html_content else f"Subscription #{sub.subscription_number} Confirmed!"

        if async_send:
            thread = threading.Thread(
                target=_send_email_worker,
                args=(subject, text_content, html_content, recipients, from_email),
                daemon=True
            )
            thread.start()
            return True
        else:
            return _send_email_worker(subject, text_content, html_content, recipients, from_email)

    except Exception as exc:
        logger.error(f"[EMAIL ERROR] Exception in send_subscription_confirmation_email: {exc}", exc_info=True)
        return False


def send_customer_welcome_email(user, async_send=True):
    """
    Sends rich HTML + Text Welcome email when a new customer registers.
    Recipients: Customer (user.email) and Store Owner (EMAIL_HOST_USER).
    """
    try:
        recipients = []
        if user and user.email and '@' in user.email:
            recipients.append(user.email.strip())

        owner_email = getattr(settings, 'EMAIL_HOST_USER', None)
        if owner_email and '@' in owner_email and owner_email.strip() not in recipients:
            recipients.append(owner_email.strip())

        if not recipients:
            logger.warning(f"[EMAIL SKIPPED] No valid recipients for user registration: {getattr(user, 'username', 'unknown')}")
            return False

        site_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
        support_email = getattr(settings, 'EMAIL_HOST_USER', 'lakumdharmesh799@gmail.com')
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', f"TiffinTrail <{support_email}>")

        customer_name = user.get_full_name() or user.first_name or user.username
        subject = f"Welcome to TiffinTrail, {customer_name}! Your Account is Ready"

        phone = ''
        if hasattr(user, 'customer_profile') and user.customer_profile:
            phone = getattr(user.customer_profile, 'phone', '') or ''

        context = {
            'user': user,
            'customer_name': customer_name,
            'username': user.username,
            'email': user.email,
            'phone': phone,
            'site_url': site_url,
            'support_email': support_email,
            'current_year': datetime.now().year,
        }

        try:
            html_content = render_to_string('customer/emails/customer_welcome.html', context)
        except Exception as e:
            logger.error(f"[EMAIL ERROR] Error rendering customer_welcome.html: {e}")
            html_content = None

        try:
            text_content = render_to_string('customer/emails/customer_welcome.txt', context)
        except Exception as e:
            text_content = strip_tags(html_content) if html_content else f"Welcome to TiffinTrail, {customer_name}!"

        if async_send:
            thread = threading.Thread(
                target=_send_email_worker,
                args=(subject, text_content, html_content, recipients, from_email),
                daemon=True
            )
            thread.start()
            return True
        else:
            return _send_email_worker(subject, text_content, html_content, recipients, from_email)

    except Exception as exc:
        logger.error(f"[EMAIL ERROR] Exception in send_customer_welcome_email: {exc}", exc_info=True)
        return False


def send_chef_welcome_email(chef, async_send=True):
    """
    Sends rich HTML + Text notification when a new home chef registers their kitchen.
    Recipients: Chef (chef.user.email) and Store Owner (EMAIL_HOST_USER).
    """
    try:
        recipients = []
        if chef.user and chef.user.email and '@' in chef.user.email:
            recipients.append(chef.user.email.strip())

        owner_email = getattr(settings, 'EMAIL_HOST_USER', None)
        if owner_email and '@' in owner_email and owner_email.strip() not in recipients:
            recipients.append(owner_email.strip())

        if not recipients:
            logger.warning(f"[EMAIL SKIPPED] No valid recipients for chef registration: {chef.business_name}")
            return False

        site_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
        support_email = getattr(settings, 'EMAIL_HOST_USER', 'lakumdharmesh799@gmail.com')
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', f"TiffinTrail <{support_email}>")

        chef_name = chef.user.get_full_name() or chef.user.first_name or chef.user.username
        subject = f"Kitchen Application Received: {chef.business_name} | TiffinTrail"

        context = {
            'chef': chef,
            'user': chef.user,
            'chef_name': chef_name,
            'business_name': chef.business_name,
            'cuisines': chef.cuisines,
            'specialties': getattr(chef, 'specialties', '') or '',
            'phone': chef.phone,
            'kitchen_address': chef.kitchen_address,
            'site_url': site_url,
            'support_email': support_email,
            'current_year': datetime.now().year,
        }

        try:
            html_content = render_to_string('customer/emails/chef_welcome.html', context)
        except Exception as e:
            logger.error(f"[EMAIL ERROR] Error rendering chef_welcome.html: {e}")
            html_content = None

        try:
            text_content = render_to_string('customer/emails/chef_welcome.txt', context)
        except Exception as e:
            text_content = strip_tags(html_content) if html_content else f"Welcome Chef {chef_name}! Your kitchen application for {chef.business_name} is under review."

        if async_send:
            thread = threading.Thread(
                target=_send_email_worker,
                args=(subject, text_content, html_content, recipients, from_email),
                daemon=True
            )
            thread.start()
            return True
        else:
            return _send_email_worker(subject, text_content, html_content, recipients, from_email)

    except Exception as exc:
        logger.error(f"[EMAIL ERROR] Exception in send_chef_welcome_email: {exc}", exc_info=True)
        return False



def send_password_reset_email(user, reset_url, async_send=True):
    """
    Sends rich HTML + Text password reset email to a customer.
    Recipient: strictly user.email.
    """
    try:
        if not user or not user.email or '@' not in user.email:
            logger.warning(f"[EMAIL SKIPPED] No valid email for password reset: {getattr(user, 'username', 'unknown')}")
            return False

        recipients = [user.email.strip()]
        site_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000').rstrip('/')
        if 'testserver' in reset_url:
            reset_url = reset_url.replace('http://testserver', site_url).replace('https://testserver', site_url)
        elif not reset_url.startswith(('http://', 'https://')):
            reset_url = f"{site_url}{reset_url if reset_url.startswith('/') else '/' + reset_url}"
        support_email = getattr(settings, 'EMAIL_HOST_USER', 'lakumdharmesh799@gmail.com')
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', f"TiffinTrail <{support_email}>")

        customer_name = user.get_full_name() or user.first_name or user.username
        subject = "Password Reset Request | TiffinTrail"

        context = {
            'user': user,
            'customer_name': customer_name,
            'reset_url': reset_url,
            'site_url': site_url,
            'support_email': support_email,
            'current_year': datetime.now().year,
        }

        try:
            html_content = render_to_string('customer/emails/password_reset.html', context)
        except Exception as e:
            logger.error(f"[EMAIL ERROR] Error rendering password_reset.html: {e}")
            html_content = None

        try:
            text_content = render_to_string('customer/emails/password_reset.txt', context)
        except Exception as e:
            text_content = strip_tags(html_content) if html_content else f"Reset password link: {reset_url}"

        if async_send:
            thread = threading.Thread(
                target=_send_email_worker,
                args=(subject, text_content, html_content, recipients, from_email),
                daemon=True
            )
            thread.start()
            return True
        else:
            return _send_email_worker(subject, text_content, html_content, recipients, from_email)

    except Exception as exc:
        logger.error(f"[EMAIL ERROR] Exception in send_password_reset_email: {exc}", exc_info=True)
        return False


def send_chef_password_reset_email(chef, reset_url, async_send=True):
    """
    Sends rich HTML + Text password reset email to a chef.
    Recipient: strictly chef.user.email.
    """
    try:
        if not chef or not chef.user or not chef.user.email or '@' not in chef.user.email:
            logger.warning(f"[EMAIL SKIPPED] No valid email for chef password reset: {getattr(chef, 'business_name', 'unknown')}")
            return False

        recipients = [chef.user.email.strip()]
        site_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000').rstrip('/')
        if 'testserver' in reset_url:
            reset_url = reset_url.replace('http://testserver', site_url).replace('https://testserver', site_url)
        elif not reset_url.startswith(('http://', 'https://')):
            reset_url = f"{site_url}{reset_url if reset_url.startswith('/') else '/' + reset_url}"
        support_email = getattr(settings, 'EMAIL_HOST_USER', 'lakumdharmesh799@gmail.com')
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', f"TiffinTrail <{support_email}>")

        chef_name = chef.user.get_full_name() or chef.user.first_name or chef.user.username
        subject = "Chef Studio Password Reset Request | TiffinTrail"

        context = {
            'chef': chef,
            'user': chef.user,
            'chef_name': chef_name,
            'business_name': chef.business_name,
            'reset_url': reset_url,
            'site_url': site_url,
            'support_email': support_email,
            'current_year': datetime.now().year,
        }

        try:
            html_content = render_to_string('customer/emails/chef_password_reset.html', context)
        except Exception as e:
            logger.error(f"[EMAIL ERROR] Error rendering chef_password_reset.html: {e}")
            html_content = None

        try:
            text_content = render_to_string('customer/emails/chef_password_reset.txt', context)
        except Exception as e:
            text_content = strip_tags(html_content) if html_content else f"Reset chef password link: {reset_url}"

        if async_send:
            thread = threading.Thread(
                target=_send_email_worker,
                args=(subject, text_content, html_content, recipients, from_email),
                daemon=True
            )
            thread.start()
            return True
        else:
            return _send_email_worker(subject, text_content, html_content, recipients, from_email)

    except Exception as exc:
        logger.error(f"[EMAIL ERROR] Exception in send_chef_password_reset_email: {exc}", exc_info=True)
        return False



def send_password_reset_otp_email(user, otp, async_send=True):
    """
    Sends rich HTML + Text 6-digit OTP email to a customer for password reset.
    Recipient: user.email.
    """
    try:
        if not user or not user.email or '@' not in user.email:
            logger.warning(f"[EMAIL SKIPPED] No valid email for password reset OTP: {getattr(user, 'username', 'unknown')}")
            return False

        recipients = [user.email.strip()]
        support_email = getattr(settings, 'EMAIL_HOST_USER', 'lakumdharmesh799@gmail.com')
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', f"TiffinTrail <{support_email}>")

        customer_name = user.get_full_name() or user.first_name or user.username
        subject = f"{otp} is your TiffinTrail Password Reset OTP"

        context = {
            'user': user,
            'customer_name': customer_name,
            'otp': otp,
            'support_email': support_email,
            'current_year': datetime.now().year,
        }

        try:
            html_content = render_to_string('customer/emails/password_reset_otp.html', context)
        except Exception as e:
            logger.error(f"[EMAIL ERROR] Error rendering password_reset_otp.html: {e}")
            html_content = None

        try:
            text_content = render_to_string('customer/emails/password_reset_otp.txt', context)
        except Exception as e:
            text_content = strip_tags(html_content) if html_content else f"Your TiffinTrail password reset OTP is {otp}"

        if async_send:
            thread = threading.Thread(
                target=_send_email_worker,
                args=(subject, text_content, html_content, recipients, from_email),
                daemon=True
            )
            thread.start()
            return True
        else:
            return _send_email_worker(subject, text_content, html_content, recipients, from_email)

    except Exception as exc:
        logger.error(f"[EMAIL ERROR] Exception in send_password_reset_otp_email: {exc}", exc_info=True)
        return False


def send_chef_password_reset_otp_email(chef, otp, async_send=True):
    """
    Sends rich HTML + Text 6-digit OTP email to a chef partner for Chef Studio password reset.
    Recipient: chef.user.email.
    """
    try:
        if not chef or not chef.user or not chef.user.email or '@' not in chef.user.email:
            logger.warning(f"[EMAIL SKIPPED] No valid email for chef password reset OTP: {getattr(chef, 'business_name', 'unknown')}")
            return False

        recipients = [chef.user.email.strip()]
        support_email = getattr(settings, 'EMAIL_HOST_USER', 'lakumdharmesh799@gmail.com')
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', f"TiffinTrail <{support_email}>")

        chef_name = chef.user.get_full_name() or chef.user.first_name or chef.user.username
        subject = f"{otp} is your Chef Studio Password Reset OTP | TiffinTrail"

        context = {
            'chef': chef,
            'user': chef.user,
            'chef_name': chef_name,
            'business_name': chef.business_name,
            'otp': otp,
            'support_email': support_email,
            'current_year': datetime.now().year,
        }

        try:
            html_content = render_to_string('customer/emails/chef_password_reset_otp.html', context)
        except Exception as e:
            logger.error(f"[EMAIL ERROR] Error rendering chef_password_reset_otp.html: {e}")
            html_content = None

        try:
            text_content = render_to_string('customer/emails/chef_password_reset_otp.txt', context)
        except Exception as e:
            text_content = strip_tags(html_content) if html_content else f"Your Chef Studio password reset OTP is {otp}"

        if async_send:
            thread = threading.Thread(
                target=_send_email_worker,
                args=(subject, text_content, html_content, recipients, from_email),
                daemon=True
            )
            thread.start()
            return True
        else:
            return _send_email_worker(subject, text_content, html_content, recipients, from_email)

    except Exception as exc:
        logger.error(f"[EMAIL ERROR] Exception in send_chef_password_reset_otp_email: {exc}", exc_info=True)
        return False
