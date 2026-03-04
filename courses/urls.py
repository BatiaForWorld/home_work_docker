from rest_framework.routers import SimpleRouter
from django.urls import path
from courses.views import CourseViewSet, LessonListAPIView, LessonCreateAPIView, \
    LessonUpdateAPIView, LessonDestroyAPIView, LessonRetrieveAPIView, SubscriptionAPIView
from courses.apps import CoursesConfig

app_name = CoursesConfig.name

router = SimpleRouter()
router.register('', CourseViewSet, basename="courses")

urlpatterns = [
    path("lessons/", LessonListAPIView.as_view(), name="lessons"),
    path("lessons/create/", LessonCreateAPIView.as_view(), name="lesson_create"),
    path("lessons/<int:pk>/update/", LessonUpdateAPIView.as_view(), name="lesson_update"),
    path("lessons/<int:pk>/", LessonRetrieveAPIView.as_view(), name="lesson_retrieve"),
    path("lessons/<int:pk>/delete/", LessonDestroyAPIView.as_view(), name="lesson_delete"),
    path("subscriptions/", SubscriptionAPIView.as_view(), name="course_subscription"),
]
urlpatterns += router.urls