from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils import timezone
from datetime import timedelta

from users.models import Payment, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
	model = User
	list_display = ("id", "email", "first_name", "last_name", "last_login", "is_staff", "is_active")
	list_filter = ("is_staff", "is_superuser", "is_active", "groups")
	search_fields = ("email", "first_name", "last_name")
	ordering = ("email",)
	actions = ("deactivate_users_inactive_over_month",)

	fieldsets = (
		(None, {"fields": ("email", "password")}),
		("Персональные данные", {"fields": ("first_name", "last_name", "phone_number", "city", "avatar")}),
		("Права", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
		("Важные даты", {"fields": ("last_login", "date_joined")}),
	)

	add_fieldsets = (
		(
			None,
			{
				"classes": ("wide",),
				"fields": ("email", "password1", "password2", "is_staff", "is_superuser"),
			},
		),
	)

	@admin.action(description="Деактивировать выбранных, не входивших более 30 дней")
	def deactivate_users_inactive_over_month(self, request, queryset):
		threshold = timezone.now() - timedelta(days=30)
		updated_count = queryset.filter(
			is_active=True,
			last_login__isnull=False,
			last_login__lt=threshold,
		).update(is_active=False)
		self.message_user(request, f"Деактивировано пользователей: {updated_count}")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
	list_display = ("id", "user", "course", "amount", "created_at")
	search_fields = ("stripe_session_id", "stripe_product_id", "stripe_price_id")
