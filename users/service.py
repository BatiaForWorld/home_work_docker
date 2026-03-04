import stripe
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings


def amount_to_kopecks(amount):
    """Конвертирует сумму в рублях в копейки для Stripe."""
    return int((amount * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def create_stripe_product(name, description=""):
    """Создает продукт Stripe и возвращает JSON-данные продукта."""
    stripe.api_key = settings.STRIPE_SECRET_KEY
    product = stripe.Product.create(name=name, description=description)
    return {"id": product.id, "name": product.name}


def create_stripe_price(product_id, amount_in_kopecks):
    """Создает цену Stripe и возвращает JSON-данные цены."""
    stripe.api_key = settings.STRIPE_SECRET_KEY
    price = stripe.Price.create(
        currency="rub",
        unit_amount=amount_in_kopecks,
        product=product_id,
    )
    return {"id": price.id, "currency": price.currency, "unit_amount": price.unit_amount}


def create_stripe_session(price_id):
    """Создает Stripe Checkout Session и возвращает JSON-данные с id и url оплаты."""
    stripe.api_key = settings.STRIPE_SECRET_KEY
    session = stripe.checkout.Session.create(
        success_url=settings.STRIPE_SUCCESS_URL,
        cancel_url=settings.STRIPE_CANCEL_URL,
        line_items=[{"price": price_id, "quantity": 1}],
        mode="payment",
    )
    return {"id": session.id, "url": session.url}


def retrieve_stripe_session(session_id):
    """Возвращает JSON-данные сессии Stripe для проверки статуса платежа."""
    stripe.api_key = settings.STRIPE_SECRET_KEY
    session = stripe.checkout.Session.retrieve(session_id)
    return {
        "id": session.id,
        "status": session.status,
        "payment_status": session.payment_status,
    }