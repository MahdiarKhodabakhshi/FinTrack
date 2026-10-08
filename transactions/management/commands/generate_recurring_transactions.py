# FT-76: A future scheduled deployment job can invoke this idempotent command.
from django.core.management.base import BaseCommand

from transactions.recurring import generate_due_transactions


class Command(BaseCommand):
    help = "Generate due recurring transactions for all users."

    def handle(self, *args, **options):
        count = generate_due_transactions()
        self.stdout.write(self.style.SUCCESS(f"Created {count} recurring transaction{'s' if count != 1 else ''}."))
