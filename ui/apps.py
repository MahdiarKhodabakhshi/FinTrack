# FT-04: Frontend-only app; it has no models or migrations.
from django.apps import AppConfig


class UiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ui"
