from urllib.parse import urlparse

from django.core.exceptions import ValidationError


ALLOWED_VIDEO_HOSTS = ("youtube.com", "youtu.be")


def validate_video_url(value):
    """Разрешает только ссылки на YouTube, остальные домены запрещены."""
    if not value:
        return
    parsed = urlparse(value)
    host = (parsed.netloc or "").lower()
    if not host:
        raise ValidationError("Укажите корректную ссылку на видео.")
    if any(host.endswith(allowed) for allowed in ALLOWED_VIDEO_HOSTS):
        return
    raise ValidationError("Ссылки на сторонние ресурсы запрещены.")
