from drf_yasg.utils import swagger_auto_schema
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta
from rest_framework.generics import (
    CreateAPIView,
    DestroyAPIView,
    ListAPIView,
    RetrieveAPIView,
    UpdateAPIView,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from courses.models import Course, Lesson, Subscription
from courses.paginators import CourseLessonPagination
from courses.serializers import (
    CourseSerializer,
    LessonSerializer,
    SubscriptionActionSerializer,
)
from courses.tasks import send_course_update_notification
from users.permissions import IsModer, IsOwner


class CourseViewSet(ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    pagination_class = CourseLessonPagination

    def get_queryset(self):
        """Возвращает курсы в зависимости от роли пользователя."""
        user = self.request.user
        if not user or not user.is_authenticated:
            return Course.objects.none()
        if self.action in {"list", "retrieve"}:
            return Course.objects.all()
        if user.groups.filter(name="moderators").exists():
            return Course.objects.all()
        return Course.objects.filter(owner=user)

    def perform_create(self, serializer):
        """Сохраняет курс с владельцем из запроса."""
        serializer.save(owner=self.request.user)

    def perform_update(self, serializer):
        """Обновляет курс и отправляет уведомление подписчикам не чаще раза в 4 часа."""
        course = serializer.instance
        should_notify = (timezone.now() - course.updated_at) > timedelta(hours=4)

        updated_course = serializer.save()

        if should_notify:
            send_course_update_notification.delay(updated_course.id)

    def get_permissions(self):
        """Назначает права доступа в зависимости от действия."""
        if self.action in {"list", "retrieve"}:
            self.permission_classes = [IsAuthenticated]
        elif self.action == "create":
            self.permission_classes = [IsAuthenticated, ~IsModer]
        elif self.action in {"update", "partial_update"}:
            self.permission_classes = [IsAuthenticated, IsModer | IsOwner]
        elif self.action == "destroy":
            self.permission_classes = [IsAuthenticated, IsOwner & ~IsModer]
        return [permission() for permission in self.permission_classes]


class LessonCreateAPIView(CreateAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated, ~IsModer]

    def perform_create(self, serializer):
        """Сохраняет урок с владельцем из запроса."""
        serializer.save(owner=self.request.user)


class LessonListAPIView(ListAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CourseLessonPagination

    def get_queryset(self):
        """Возвращает список уроков в зависимости от роли пользователя."""
        user = self.request.user
        if user.is_authenticated and user.groups.filter(name="moderators").exists():
            return Lesson.objects.all()
        return Lesson.objects.filter(owner=user)


class LessonRetrieveAPIView(RetrieveAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Возвращает доступные уроки для просмотра."""
        user = self.request.user
        if user.is_authenticated and user.groups.filter(name="moderators").exists():
            return Lesson.objects.all()
        return Lesson.objects.filter(owner=user)


class LessonUpdateAPIView(UpdateAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated, IsModer | IsOwner]

    def get_queryset(self):
        """Возвращает доступные уроки для изменения."""
        user = self.request.user
        if user.is_authenticated and user.groups.filter(name="moderators").exists():
            return Lesson.objects.all()
        return Lesson.objects.filter(owner=user)


class LessonDestroyAPIView(DestroyAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated, IsOwner & ~IsModer]

    def get_queryset(self):
        """Возвращает доступные уроки для удаления."""
        user = self.request.user
        if user.is_authenticated and user.groups.filter(name="moderators").exists():
            return Lesson.objects.all()
        return Lesson.objects.filter(owner=user)


class SubscriptionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(request_body=SubscriptionActionSerializer)
    def post(self, request, *args, **kwargs):
        """Добавляет или удаляет подписку пользователя на курс."""
        course_id = request.data.get("course_id")
        course_item = get_object_or_404(Course, pk=course_id)
        subs_item = Subscription.objects.filter(user=request.user, course=course_item)

        if subs_item.exists():
            subs_item.delete()
            message = "подписка удалена"
        else:
            Subscription.objects.create(user=request.user, course=course_item)
            message = "подписка добавлена"

        return Response({"message": message})
