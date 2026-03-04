from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

from courses.models import Course, Subscription


@shared_task
def send_course_update_notification(course_id):
    """Отправляет уведомление подписчикам о обновлении материалов курса."""
    course = Course.objects.filter(pk=course_id).first()
    if not course:
        return 0

    recipients = list(
        Subscription.objects.filter(course=course)
        .select_related("user")
        .values_list("user__email", flat=True)
    )
    recipients = [email for email in recipients if email]

    if not recipients:
        return 0

    subject = f"Обновление курса: {course.title}"
    message = f"В курсе '{course.title}' появились обновления материалов."

    sent_count = 0
    for recipient in recipients:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )
        sent_count += 1

    return sent_count
