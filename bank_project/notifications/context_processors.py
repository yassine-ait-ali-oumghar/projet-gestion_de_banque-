from notifications.models import Notification


def unread_notifications(request):
    """Provide unread notification count to all templates."""
    if request.user.is_authenticated:
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        return {'unread_notification_count': count}
    return {'unread_notification_count': 0}
