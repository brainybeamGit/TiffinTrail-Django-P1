from .models import ChefProfile, ChefNotification


def chef_context(request):
    """Provides chef profile and unread notification count for chef studio views."""
    chef_prof = None
    unread_count = 0

    if request.user.is_authenticated:
        chef_prof = ChefProfile.objects.filter(user=request.user).first()
        if chef_prof:
            unread_count = ChefNotification.objects.filter(chef=chef_prof, is_read=False).count()

    return {
        'current_chef': chef_prof,
        'chef_unread_count': unread_count,
    }
