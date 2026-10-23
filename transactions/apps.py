from django.apps import AppConfig


class TransactionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'transactions'

    def ready(self):
        # FT-30: Install the account-created category receiver.
        from . import signals  # noqa: F401
