from django.urls import path
from rest_framework.routers import SimpleRouter

from users.apps import UsersConfig
from rest_framework_simplejwt.views import TokenRefreshView

from users.views import (
	LoginAPIView,
	LogoutAPIView,
	PaymentCreateAPIView,
	PaymentListAPIView,
	PaymentStatusAPIView,
	UserProfileViewSet,
	UserRegistrationAPIView,
)

app_name = UsersConfig.name

router = SimpleRouter()
router.register("profile", UserProfileViewSet, basename="profile")

urlpatterns = [
	path("register/", UserRegistrationAPIView.as_view(), name="register"),
	path("login/", LoginAPIView.as_view(), name="login"),
	path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
	path("logout/", LogoutAPIView.as_view(), name="logout"),
	path("payments/", PaymentListAPIView.as_view(), name="payment_list"),
	path("payments/create/", PaymentCreateAPIView.as_view(), name="payment_create"),
	path(
		"payments/status/<str:stripe_session_id>/",
		PaymentStatusAPIView.as_view(),
		name="payment_status",
	),
]

urlpatterns += router.urls
