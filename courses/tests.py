from django.contrib.auth.models import Group
from django.urls import reverse
from unittest.mock import patch
from datetime import timedelta
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from courses.models import Course, Lesson, Subscription
from users.models import User


class LessonCrudTestCase(APITestCase):
	def setUp(self):
		"""Подготавливает пользователей, курс и урок для тестов."""
		self.owner = User.objects.create_user(email="owner@test.com", password="pass")
		self.other_user = User.objects.create_user(email="other@test.com", password="pass")
		self.moderator = User.objects.create_user(
			email="moder@test.com", password="pass"
		)
		moderators = Group.objects.create(name="moderators")
		self.moderator.groups.add(moderators)

		self.course = Course.objects.create(title="Course", owner=self.owner)
		self.lesson = Lesson.objects.create(
			title="Lesson",
			course=self.course,
			owner=self.owner,
			video_url="https://www.youtube.com/watch?v=test",
		)

	def test_owner_lesson_crud(self):
		"""Проверяет CRUD операций владельца для урока."""
		self.client.force_authenticate(user=self.owner)

		create_url = reverse("courses:lesson_create")
		payload = {
			"title": "Lesson new",
			"course": self.course.id,
			"video_url": "https://youtu.be/test",
		}
		response = self.client.post(create_url, data=payload)
		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		lesson_id = response.data["id"]

		list_url = reverse("courses:lessons")
		response = self.client.get(list_url)
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(len(response.data["results"]), 2)

		retrieve_url = reverse("courses:lesson_retrieve", args=[lesson_id])
		response = self.client.get(retrieve_url)
		self.assertEqual(response.status_code, status.HTTP_200_OK)

		update_url = reverse("courses:lesson_update", args=[lesson_id])
		response = self.client.patch(update_url, data={"title": "Lesson updated"})
		self.assertEqual(response.status_code, status.HTTP_200_OK)

		delete_url = reverse("courses:lesson_delete", args=[lesson_id])
		response = self.client.delete(delete_url)
		self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

	def test_video_url_validator_rejects_external(self):
		"""Проверяет запрет сторонних ссылок в поле видео."""
		self.client.force_authenticate(user=self.owner)
		create_url = reverse("courses:lesson_create")
		payload = {
			"title": "Lesson bad",
			"course": self.course.id,
			"video_url": "https://example.com/video",
		}
		response = self.client.post(create_url, data=payload)
		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertIn("video_url", response.data)

	def test_other_user_cannot_update(self):
		"""Проверяет запрет на изменение урока чужим пользователем."""
		self.client.force_authenticate(user=self.other_user)
		update_url = reverse("courses:lesson_update", args=[self.lesson.id])
		response = self.client.patch(update_url, data={"title": "Denied"})
		self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

	def test_moderator_can_update(self):
		"""Проверяет, что модератор может редактировать урок."""
		self.client.force_authenticate(user=self.moderator)
		update_url = reverse("courses:lesson_update", args=[self.lesson.id])
		response = self.client.patch(update_url, data={"title": "Moderated"})
		self.assertEqual(response.status_code, status.HTTP_200_OK)


class SubscriptionTestCase(APITestCase):
	def setUp(self):
		"""Подготавливает пользователей и курс для тестов подписки."""
		self.owner = User.objects.create_user(email="owner2@test.com", password="pass")
		self.user = User.objects.create_user(email="user2@test.com", password="pass")
		self.course = Course.objects.create(title="Course", owner=self.owner)

	def test_subscribe_and_unsubscribe(self):
		"""Проверяет добавление и удаление подписки на курс."""
		self.client.force_authenticate(user=self.user)
		subscribe_url = reverse("courses:course_subscription")

		response = self.client.post(subscribe_url, data={"course_id": self.course.id})
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data, {"message": "подписка добавлена"})
		self.assertTrue(
			Subscription.objects.filter(user=self.user, course=self.course).exists()
		)

		courses_url = reverse("courses:courses-list")
		response = self.client.get(courses_url)
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertTrue(response.data["results"][0]["is_subscribed"])

		response = self.client.post(subscribe_url, data={"course_id": self.course.id})
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data["message"], "подписка удалена")
		self.assertFalse(
			Subscription.objects.filter(user=self.user, course=self.course).exists()
		)

	def test_courses_pagination_structure(self):
		"""Проверяет наличие ключей пагинации в выдаче курсов."""
		self.client.force_authenticate(user=self.user)
		courses_url = reverse("courses:courses-list")
		response = self.client.get(courses_url)
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertIn("count", response.data)
		self.assertIn("results", response.data)


class CourseNotificationTestCase(APITestCase):
	def setUp(self):
		self.owner = User.objects.create_user(email="owner-notify@test.com", password="pass")
		self.course = Course.objects.create(title="Notify course", owner=self.owner, price=100)

	@patch("courses.views.send_course_update_notification.delay")
	def test_notify_on_update_after_4_hours(self, task_delay_mock):
		self.client.force_authenticate(user=self.owner)
		Course.objects.filter(pk=self.course.pk).update(
			updated_at=timezone.now() - timedelta(hours=5)
		)

		url = reverse("courses:courses-detail", args=[self.course.id])
		response = self.client.patch(url, data={"description": "Updated"})

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		task_delay_mock.assert_called_once_with(self.course.id)

	@patch("courses.views.send_course_update_notification.delay")
	def test_skip_notify_if_less_than_4_hours(self, task_delay_mock):
		self.client.force_authenticate(user=self.owner)

		url = reverse("courses:courses-detail", args=[self.course.id])
		response = self.client.patch(url, data={"description": "Updated quick"})

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		task_delay_mock.assert_not_called()
