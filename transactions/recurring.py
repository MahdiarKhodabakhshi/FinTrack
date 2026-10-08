# FT-76: Anchored scheduling and idempotent, owner-scoped catch-up generation.
from calendar import monthrange
from datetime import date, timedelta

from django.db import transaction
from django.utils import timezone

from .models import RecurringTransaction, Transaction

MAX_CATCH_UP = 400


def next_occurrence(rule, current):
    """FT-76: Advance a period; monthly dates always use the original anchor day."""
    if rule.frequency == RecurringTransaction.Frequency.WEEKLY:
        return current + timedelta(days=7)
    if rule.frequency == RecurringTransaction.Frequency.BIWEEKLY:
        return current + timedelta(days=14)
    if rule.frequency != RecurringTransaction.Frequency.MONTHLY:
        raise ValueError("Unknown recurring frequency.")
    year, month = current.year + (current.month == 12), current.month % 12 + 1
    return date(year, month, min(rule.start_date.day, monthrange(year, month)[1]))


def generate_due_transactions(*, user=None, today=None):
    """FT-76: Create due occurrences, capped per rule; command may process all users."""
    today = today if today is not None else timezone.localdate()
    due = RecurringTransaction.objects.filter(is_active=True, next_due_date__lte=today)
    if user is not None:
        due = due.filter(user=user)
    created_count = 0
    for pk in list(due.values_list("pk", flat=True)):
        with transaction.atomic():
            rule = due.select_for_update().filter(pk=pk).first()
            if rule is None:
                continue
            processed = 0
            while (rule.next_due_date <= today and
                   (rule.end_date is None or rule.next_due_date <= rule.end_date) and
                   processed < MAX_CATCH_UP):
                _, created = Transaction.objects.get_or_create(
                    recurring_source=rule, date=rule.next_due_date,
                    defaults={"user": rule.user, "transaction_type": rule.transaction_type,
                              "amount": rule.amount, "description": rule.description},
                )
                created_count += int(created)
                processed += 1
                rule.next_due_date = next_occurrence(rule, rule.next_due_date)
            if rule.end_date and rule.next_due_date > rule.end_date:
                rule.is_active = False
            rule.save(update_fields=["next_due_date", "is_active", "updated_at"])
    return created_count


def resume_rule(rule, today=None):
    """FT-76: Skip paused dates without backfill; an elapsed end date stays ended."""
    today = today if today is not None else timezone.localdate()
    with transaction.atomic():
        locked = RecurringTransaction.objects.select_for_update().get(pk=rule.pk, user=rule.user)
        while locked.next_due_date < today:
            locked.next_due_date = next_occurrence(locked, locked.next_due_date)
        locked.is_active = not (locked.end_date and locked.next_due_date > locked.end_date)
        locked.save(update_fields=["next_due_date", "is_active", "updated_at"])
        rule.next_due_date, rule.is_active = locked.next_due_date, locked.is_active
    return rule
