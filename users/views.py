import stripe
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView, ListAPIView
from rest_framework.mixins import (
	DestroyModelMixin,
	ListModelMixin,
	RetrieveModelMixin,
	UpdateModelMixin,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import Payment, User
from users.permissions import IsOwner
from users.serializers import (
	LoginSerializer,
	PaymentCreateSerializer,
	PaymentSerializer,
	UserPublicSerializer,
	UserRegistrationSerializer,
	UserSerializer,
)
from users.service import (
	amount_to_kopecks,
	create_stripe_price,
	create_stripe_product,
	create_stripe_session,
	retrieve_stripe_session,
)


class UserProfileViewSet(RetrieveModelMixin, UpdateModelMixin, ListModelMixin, DestroyModelMixin, GenericViewSet):
	"""CRUD-представление профиля пользователя."""

	queryset = User.objects.all()
	serializer_class = UserSerializer

	def get_permissions(self):
		if self.action in {"list", "retrieve"}:
			self.permission_classes = [IsAuthenticated]
		elif self.action in {"update", "partial_update", "destroy"}:
			self.permission_classes = [IsAuthenticated, IsOwner]
		return [permission() for permission in self.permission_classes]

	def get_serializer_class(self):
		if self.action == "list":
			return UserPublicSerializer
		if self.action == "retrieve":
			obj = self.get_object()
			if self.request.user == obj:
				return UserSerializer
			return UserPublicSerializer
		return UserSerializer


class UserRegistrationAPIView(APIView):
	"""Регистрация пользователя с выдачей JWT-токенов."""

	permission_classes = []
	authentication_classes = []

	def post(self, request, *args, **kwargs):
		serializer = UserRegistrationSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		user = serializer.save()
		refresh = RefreshToken.for_user(user)
		return Response(
			{"refresh": str(refresh), "access": str(refresh.access_token)},
			status=status.HTTP_201_CREATED,
		)


class LoginAPIView(APIView):
	"""Аутентификация пользователя и выдача JWT-токенов."""

	permission_classes = []
	authentication_classes = []

	def post(self, request, *args, **kwargs):
		serializer = LoginSerializer(data=request.data, context={"request": request})
		serializer.is_valid(raise_exception=True)
		user = serializer.validated_data["user"]
		refresh = RefreshToken.for_user(user)
		return Response({"refresh": str(refresh), "access": str(refresh.access_token)})


class LogoutAPIView(APIView):
	"""Выход пользователя (stateless для JWT)."""

	permission_classes = [IsAuthenticated]

	def post(self, request, *args, **kwargs):
		return Response(status=status.HTTP_204_NO_CONTENT)


class PaymentCreateAPIView(CreateAPIView):
	"""Создает платеж, а также Product/Price/Checkout Session в Stripe."""

	queryset = Payment.objects.all()
	serializer_class = PaymentCreateSerializer
	permission_classes = [IsAuthenticated]

	@swagger_auto_schema(request_body=PaymentCreateSerializer, responses={201: PaymentSerializer})
	def post(self, request, *args, **kwargs):
		return super().post(request, *args, **kwargs)

	def perform_create(self, serializer):
		"""Создает Stripe-сущности и сохраняет ссылку оплаты в локальном платеже."""
		course = serializer.validated_data["course"]
		if course.price <= 0:
			raise ValidationError({"course": "Цена курса должна быть больше 0."})

		amount_in_kopecks = amount_to_kopecks(course.price)

		try:
			product_id = course.stripe_product_id
			if not product_id:
				stripe_product = create_stripe_product(course.title, course.description or "")
				product_id = stripe_product["id"]
				course.stripe_product_id = product_id
				course.save(update_fields=["stripe_product_id"])

			stripe_price = create_stripe_price(product_id, amount_in_kopecks)
			stripe_session = create_stripe_session(stripe_price["id"])
		except stripe.error.StripeError as exc:
			raise ValidationError({"stripe": str(exc)}) from exc

		serializer.instance = Payment.objects.create(
			user=self.request.user,
			course=course,
			amount=course.price,
			stripe_product_id=product_id,
			stripe_price_id=stripe_price["id"],
			stripe_session_id=stripe_session["id"],
			payment_link=stripe_session["url"],
		)

	def create(self, request, *args, **kwargs):
		"""Возвращает полный объект платежа с `payment_link` после создания."""
		serializer = self.get_serializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		self.perform_create(serializer)
		output_serializer = PaymentSerializer(serializer.instance)
		headers = self.get_success_headers(output_serializer.data)
		return Response(output_serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class PaymentListAPIView(ListAPIView):
	"""Возвращает платежи: свои для пользователя, все для модератора."""

	serializer_class = PaymentSerializer
	permission_classes = [IsAuthenticated]

	def get_queryset(self):
		"""Выбирает набор платежей в зависимости от роли пользователя."""
		user = self.request.user
		if user.groups.filter(name="moderators").exists():
			return Payment.objects.all()
		return Payment.objects.filter(user=user)


class PaymentStatusAPIView(APIView):
	"""Проверяет статус платежа в Stripe по stripe_session_id."""

	permission_classes = [IsAuthenticated]

	def get(self, request, stripe_session_id, *args, **kwargs):
		"""Возвращает статус платежа из Stripe для доступного пользователю платежа."""
		if request.user.groups.filter(name="moderators").exists():
			payment = Payment.objects.filter(stripe_session_id=stripe_session_id).first()
		else:
			payment = Payment.objects.filter(
				stripe_session_id=stripe_session_id,
				user=request.user,
			).first()

		if not payment:
			return Response(
				{"detail": "Платеж не найден."},
				status=status.HTTP_404_NOT_FOUND,
			)

		try:
			session_data = retrieve_stripe_session(stripe_session_id)
		except stripe.error.StripeError as exc:
			raise ValidationError({"stripe": str(exc)}) from exc

		return Response(
			{
				"payment_id": payment.id,
				"stripe_session_id": stripe_session_id,
				"status": session_data["status"],
				"payment_status": session_data["payment_status"],
			}
		)
