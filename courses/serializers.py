from rest_framework import serializers

from courses.models import Course, Lesson, Subscription
from courses.validators import validate_video_url


class LessonSerializer(serializers.ModelSerializer):
    video_url = serializers.URLField(
        required=False,
        allow_blank=True,
        allow_null=True,
        validators=[validate_video_url],
    )

    class Meta:
        model = Lesson
        fields = "__all__"
        read_only_fields = ("owner",)


class CourseSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = (
            "id",
            "title",
            "preview",
            "description",
            "price",
            "created_at",
            "updated_at",
            "owner",
            "is_subscribed",
        )
        read_only_fields = ("owner",)

    def get_is_subscribed(self, obj):
        """Проверяет, подписан ли текущий пользователь на курс."""
        request = self.context.get("request")
        if not request or not request.user or not request.user.is_authenticated:
            return False
        return Subscription.objects.filter(user=request.user, course=obj).exists()


class SubscriptionActionSerializer(serializers.Serializer):
    course_id = serializers.IntegerField()