from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from users.models import User


@shared_task
def deactivate_inactive_users():
    """Блокирует пользователей, которые не входили в систему более 30 дней."""
    threshold = timezone.now() - timedelta(days=30)
    updated_count = User.objects.filter(
        is_active=True,
        last_login__isnull=False,
        last_login__lt=threshold,
    ).update(is_active=False)
    return updated_count
