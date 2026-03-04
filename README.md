# Django REST Framework

Домашнее задание на тему:

### Вьюсеты и дженерики (viewsets and generics)

Для установки проекта создайте проект и импортируйте его по ссылке github

Создайте виртуальное окружение

```bash
python3.13 -m venv .venv
```

Установите зависимости из файла requirements.txt

```bash
pip install -r requirements.txt
```


Заполните файл .env по примеру env.example, указав данные для соединения с БД postgreSQL.
Также заполните тестовые настройки Stripe:
- `STRIPE_SECRET_KEY`
- `STRIPE_SUCCESS_URL`
- `STRIPE_CANCEL_URL`
И настройки Redis для Celery:
- `REDIS_HOST`
- `REDIS_PORT`
- `REDIS_DB`
- `REDIS_PASSWORD`

Выполните миграции

```bash
python3 manage.py migrate
```

Скачайте [Postman](https://dl.pstmn.io/download/latest/linux_64) для вашего дистрибутива Linux, распакуйте в удобную для
вас папку и запустите

# Права доступа в DRF 
## JWT

### Фикстуры
Для добавления группы модераторов используйте фикстуру [users/fixtures/groups.json](users/fixtures/groups.json).

Пример применения:

```bash
python3 manage.py loaddata users/fixtures/groups.json
```
Создайте администратора:
```commandline
python3 manage.py createsuperuser
```
После загрузки фикстуры назначайте пользователей в группу moderators через админ-панель.

### Возможности проекта
- Регистрация пользователей и JWT-аутентификация.
- CRUD для пользователей (публичный и полный профиль в зависимости от владельца).
- CRUD для курсов и уроков.
- Разграничение прав: модераторы могут просматривать и редактировать любые курсы и уроки, но не создавать и не удалять.
- Пользователи, не входящие в группу модераторов, видят и изменяют только свои курсы и уроки.

# Валидаторы, пагинация и тесты

Для сохранения уроков и курсов реализована дополнительная проверка на отсутствие в материалах ссылок на сторонние ресурсы, 
кроме youtube.com.
То есть ссылки на видео можно прикреплять в материалы, 
а ссылки на сторонние образовательные платформы или личные сайты — нельзя.

Добавлена модель подписки на обновления курса для пользователя. 

Реализован эндпоинт для установки подписки пользователя и на удаление подписки у пользователя.

Реализована пагинация для вывода всех уроков и курсов.

Реализована документация API через Swagger и Redoc.

Реализована интеграция оплаты курсов через Stripe Checkout.

Написаны тесты, которые проверяют корректность работы CRUD уроков и функционал работы подписки на обновления курса.

Сохранены результат проверки покрытия тестами.

### Что бы запустить тесты введите команду:

```commandline
python3 manage.py test
```

### Чтобы сохранить отчет о покрытии тестами в определенную папку, например, в папку htgmlcov,
нужно выполнить следующие шаги:

Запустить тесты только для ****courses****, выполните:

```commandline
python manage.py test courses
```
Отчёт о покрытии:

```commandline
coverage report
```

Запустить тесты с подсчетом покрытия:

```commandline
coverage run --source='.' manage.py test
```

Сохранить отчет в папку htgmlcov:

```commandline
coverage html -d htgmlcov
```

## Документация API

- Swagger UI: `/swagger/`
- OpenAPI JSON/YAML: `/swagger<format>/`
- ReDoc: `/redoc/`

## Оплата Stripe

Эндпоинты:
- `GET /users/payments/` — список платежей пользователя (модератор видит все).
- `POST /users/payments/create/` — создать платеж и получить ссылку на оплату (`payment_link`).
- `GET /users/payments/status/<stripe_session_id>/` — проверить `payment_status` сессии в Stripe.

При создании платежа система автоматически создаёт в Stripe:
- Product
- Price (сумма передаётся в копейках)
- Checkout Session

Взаимодействие со Stripe вынесено в сервисные функции приложения `users`.

В `.env` укажите реальные URL редиректа, а не заглушки:
- `STRIPE_SUCCESS_URL=http://localhost:8000/users/payments/success/?session_id={CHECKOUT_SESSION_ID}`
- `STRIPE_CANCEL_URL=http://localhost:8000/users/payments/cancel/`

## Полный сценарий запросов (curl)

Ниже минимальный рабочий сценарий от регистрации до получения ссылки Stripe.

1) Регистрация (без Authorization):

```bash
curl -X POST http://localhost:8000/users/register/ \
	-H "Content-Type: application/json" \
	-d '{
		"email": "vasia@example.com",
		"password1": "vasia12345",
		"password2": "vasia12345"
	}'
```

2) Логин (без Authorization):

```bash
curl -X POST http://localhost:8000/users/login/ \
	-H "Content-Type: application/json" \
	-d '{
		"email": "vasia@example.com",
		"password": "vasia12345"
	}'
```

3) Обновить access по refresh:

```bash
curl -X POST http://localhost:8000/users/token/refresh/ \
	-H "Content-Type: application/json" \
	-d '{
		"refresh": "<YOUR_REFRESH_TOKEN>"
	}'
```

4) Создать курс с ценой (нужен для оплаты):

```bash
curl -X POST http://localhost:8000/courses/ \
	-H "Content-Type: application/json" \
	-H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" \
	-d '{
		"title": "Python Pro",
		"description": "Оплачиваемый курс",
		"price": 500
	}'
```

5) Создать платеж и получить `payment_link` Stripe:

```bash
curl -X POST http://localhost:8000/users/payments/create/ \
	-H "Content-Type: application/json" \
	-H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" \
	-d '{
		"course": 1
	}'
```

6) Получить список своих платежей:

```bash
curl -X GET http://localhost:8000/users/payments/ \
	-H "Authorization: Bearer <YOUR_ACCESS_TOKEN>"
```

7) Проверить статус платежа по `stripe_session_id`:

```bash
curl -X GET http://localhost:8000/users/payments/status/cs_test_123/ \
	-H "Authorization: Bearer <YOUR_ACCESS_TOKEN>"
```

Если приходит `token_not_valid` или `Token is expired`:
- получите новый `access` через `/users/token/refresh/`;
- или заново войдите через `/users/login/`.
- убедитесь, что на `/users/register/` и `/users/login/` вы не отправляете старый `Authorization`.

## Celery и периодические задачи

В проекте реализовано:
- асинхронная рассылка подписчикам при обновлении курса;
- ограничение рассылки: уведомление отправляется, только если курс не обновлялся более 4 часов;
- периодическая задача блокировки пользователей, не заходивших более месяца.

Запуск воркера Celery:

```bash
celery -A config worker -l info
```

Запуск celery-beat:

```bash
celery -A config beat -l info
```


#### A. Проверка рассылки при обновлении курса

1) Получите `access` токен:
- `POST /users/login/`
- body:

```json
{
	"email": "owner@test.com",
	"password": "pass"
}
```

2) Создайте курс (если его нет):
- `POST /courses/`
- Header: `Authorization: Bearer <access>`
- body:

```json
{
	"title": "Celery test course",
	"description": "initial",
	"price": 500
}
```

3) Подпишите другого пользователя на курс:
- `POST /courses/subscriptions/`
- Header: `Authorization: Bearer <access_subscriber>`
- body:

```json
{
	"course_id": 1
}
```

4) Обновите курс владельцем:
- `PATCH /courses/1/`
- Header: `Authorization: Bearer <access_owner>`
- body:

```json
{
	"description": "updated from postman"
}
```
# Docker
Установка на Debian:
```angular2html
sudo apt update

sudo apt install ca-certificates curl gnupg
```
```angular2html
sudo install -m 0755 -d /etc/apt/keyrings

curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

sudo chmod a+r /etc/apt/keyrings/docker.gpg


echo \

  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \

  bookworm stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null



```
Установка прав доступа для Docker в Linux, чтобы использовать команды без sudo.
Добавьте пользователя в группу docker, это позволит управлять контейнерами, 
образами и томами без повышения привилегий до root. 


```angular2html
sudo apt update

sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```
Создайте группу docker (если она не создана):
```angular2html
sudo groupadd docker
```
Добавьте вашего пользователя в группу:

```angular2html
sudo usermod -aG docker $USER
```
Примените изменения:
```angular2html
newgrp docker
```
Проверка без sudo:
```angular2html
docker run hello-world
```
Добавление пользователя в группу docker эквивалентно предоставлению прав root,
так как позволяет контейнерам получить доступ к файловой системе хоста.

## Docker Compose

### Быстрый запуск

1) Скопируйте шаблон окружения и заполните значения находясь в дериктории проекта:

```bash
cp env.example .env
```


2) Запуск всех сервисов одной командой:

```bash
docker compose up --build
```
Проверьте в соседнем терминале:
Проверяем Time Zone:

```
docker compose exec web env | grep TIME_ZONE
```
Проверить, какие значения берёт compose для PostgreSQL:

```
docker compose config | grep -A3 POSTGRES_
```
Проверить, какие значения берёт compose для Redis:

```angular2html
docker compose config | grep -A3 REDIS_
```
Миграции применяются автоматически при старте сервиса `web`.

Если нужно пересобрать заново контейнеры, выполните команду:
```angular2html
docker compose down -v
```
И соберите заново:
```angular2html
docker compose up --build
```

### Проверка работоспособности

- Django API: открыть `http://localhost:8000/swagger/`.
- PostgreSQL: `docker compose exec db pg_isready -U <USER> -d <NAME>`.
- Redis: `docker compose exec redis redis-cli ping`.
- Celery worker: `docker compose logs -f celery`.
- Celery beat: `docker compose logs -f celery-beat`.

Автор: Казанцев Андрей




