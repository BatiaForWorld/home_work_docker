from unittest.mock import patch
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from courses.models import Course
from users.models import Payment, User
from users.tasks import deactivate_inactive_users


class PaymentTestCase(APITestCase):
	"""Тесты API платежей пользователя."""

	def setUp(self):
		self.user = User.objects.create_user(email="payer@test.com", password="pass")
		self.course = Course.objects.create(
			title="Paid course",
			description="Course description",
			owner=self.user,
			price=1000,
		)

	@patch("users.views.create_stripe_session")
	@patch("users.views.create_stripe_price")
	@patch("users.views.create_stripe_product")
	def test_create_payment(self, create_product_mock, create_price_mock, create_session_mock):
		"""Создает платеж и возвращает ссылку Stripe Checkout."""
		self.client.force_authenticate(user=self.user)

		create_product_mock.return_value = {"id": "prod_test", "name": "Paid course"}
		create_price_mock.return_value = {"id": "price_test", "currency": "rub", "unit_amount": 100000}
		create_session_mock.return_value = {"id": "cs_test", "url": "https://checkout.stripe.com/test"}

		url = reverse("users:payment_create")
		response = self.client.post(url, data={"course": self.course.id})

		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		self.assertEqual(response.data["stripe_product_id"], "prod_test")
		self.assertEqual(response.data["stripe_price_id"], "price_test")
		self.assertEqual(response.data["stripe_session_id"], "cs_test")
		self.assertEqual(response.data["payment_link"], "https://checkout.stripe.com/test")
		self.assertEqual(Payment.objects.count(), 1)

	def test_create_payment_with_zero_price(self):
		"""Не позволяет создать платеж для бесплатного курса."""
		self.client.force_authenticate(user=self.user)
		self.course.price = 0
		self.course.save(update_fields=["price"])

		url = reverse("users:payment_create")
		response = self.client.post(url, data={"course": self.course.id})

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertIn("course", response.data)

	@patch("users.views.retrieve_stripe_session")
	def test_payment_status_success(self, retrieve_session_mock):
		"""Возвращает статус платежа из Stripe по stripe_session_id."""
		self.client.force_authenticate(user=self.user)

		payment = Payment.objects.create(
			user=self.user,
			course=self.course,
			amount=self.course.price,
			stripe_product_id="prod_test",
			stripe_price_id="price_test",
			stripe_session_id="cs_test",
			payment_link="https://checkout.stripe.com/test",
		)

		retrieve_session_mock.return_value = {
			"id": "cs_test",
			"status": "complete",
			"payment_status": "paid",
		}

		url = reverse("users:payment_status", args=["cs_test"])
		response = self.client.get(url)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data["payment_id"], payment.id)
		self.assertEqual(response.data["status"], "complete")
		self.assertEqual(response.data["payment_status"], "paid")

	def test_payment_status_not_found(self):
		"""Возвращает 404, если платеж не принадлежит пользователю или отсутствует."""
		self.client.force_authenticate(user=self.user)
		url = reverse("users:payment_status", args=["cs_unknown"])
		response = self.client.get(url)

		self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
		self.assertEqual(response.data["detail"], "Платеж не найден.")


class UserDeactivateTaskTestCase(APITestCase):
	def test_deactivate_users_inactive_more_than_month(self):
		inactive_user = User.objects.create_user(email="inactive@test.com", password="pass")
		active_user = User.objects.create_user(email="active@test.com", password="pass")

		inactive_user.last_login = timezone.now() - timedelta(days=31)
		inactive_user.save(update_fields=["last_login"])

		active_user.last_login = timezone.now() - timedelta(days=5)
		active_user.save(update_fields=["last_login"])

		updated_count = deactivate_inactive_users()

		inactive_user.refresh_from_db()
		active_user.refresh_from_db()

		self.assertEqual(updated_count, 1)
		self.assertFalse(inactive_user.is_active)
		self.assertTrue(active_user.is_active)
