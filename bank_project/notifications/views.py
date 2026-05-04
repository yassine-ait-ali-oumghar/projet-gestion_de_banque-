from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Notification


@login_required
def notifications_list(request):
    """Liste des notifications de l'utilisateur."""
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    # Marquer comme lues
    notifications.filter(is_read=False).update(is_read=True)
    return render(request, 'notifications/notifications.html', {'notifications': notifications})
