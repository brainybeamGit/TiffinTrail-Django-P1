from .models import AdminNotification, Complaint
from chef.models import ChefProfile


def admin_context(request):
    """Provides admin badges and notification counts for the Admin Console."""
    if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
        unread_notifications = AdminNotification.objects.filter(is_read=False).count()
        pending_complaints = Complaint.objects.filter(status__in=['open', 'in_progress']).count()
        pending_verifications = ChefProfile.objects.filter(verification_status='pending').count()
        return {
            'admin_unread_count': unread_notifications,
            'admin_pending_complaints_count': pending_complaints,
            'admin_pending_verifications_count': pending_verifications,
        }
    return {
        'admin_unread_count': 0,
        'admin_pending_complaints_count': 0,
        'admin_pending_verifications_count': 0,
    }
