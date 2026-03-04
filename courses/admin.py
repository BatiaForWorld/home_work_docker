from django.contrib import admin

from courses.models import Course, Lesson, Subscription


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
	list_display = ("id", "title", "price", "owner", "created_at")
	search_fields = ("title",)


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
	list_display = ("id", "title", "course", "owner", "created_at")
	search_fields = ("title",)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
	list_display = ("id", "user", "course", "created_at")
