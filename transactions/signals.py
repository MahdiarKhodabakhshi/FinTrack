# FT-30: Every account, including admin-created accounts, receives its own defaults.
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Category


DEFAULT_CATEGORIES = (
    "Food", "Housing", "Transport", "Utilities", "Health", "Personal", "Entertainment",
)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_default_categories(sender, instance, created, raw=False, **kwargs):
    """Create the starter categories once, scoped to a newly-created account."""
    if not created or raw:
        return
    Category.objects.bulk_create(
        [Category(user=instance, name=name, is_default=True) for name in DEFAULT_CATEGORIES]
        + [Category(user=instance, name="Uncategorized", is_default=True, is_uncategorized=True)],
        ignore_conflicts=True,
    )
