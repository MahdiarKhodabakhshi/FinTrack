# FT-59, FT-61: Owner-scoped category totals for two selected months.
from decimal import Decimal

from django import forms
from django.db.models import Sum

from .models import Category, Transaction
from .months import MonthField, next_month_start


class MonthComparisonForm(forms.Form):
    month_a = MonthField(label="First month")
    month_b = MonthField(label="Second month")


def _spending_by_category(user, month_start):
    next_start = next_month_start(month_start)
    uncategorized_id = Category.objects.filter(user=user, is_uncategorized=True).values_list("pk", flat=True).first()
    rows = Transaction.objects.filter(
        user=user,
        transaction_type=Transaction.TransactionType.EXPENSE,
        date__gte=month_start,
        date__lt=next_start,
    ).values("category_id").annotate(total=Sum("amount"))
    result = {}
    for row in rows:
        category_id = row["category_id"] or uncategorized_id
        if category_id is not None:
            result[category_id] = result.get(category_id, Decimal("0.00")) + row["total"]
    return result


def compare_category_spending(user, month_a, month_b):
    """Return category expense totals and the second-minus-first change."""
    amounts_a = _spending_by_category(user, month_a)
    amounts_b = _spending_by_category(user, month_b)
    category_ids = set(amounts_a) | set(amounts_b)
    categories = Category.objects.filter(user=user, pk__in=category_ids)
    rows = []
    for category in categories:
        amount_a = amounts_a.get(category.pk, Decimal("0.00"))
        amount_b = amounts_b.get(category.pk, Decimal("0.00"))
        rows.append({
            "category": category,
            "amount_a": amount_a,
            "amount_b": amount_b,
            "change": amount_b - amount_a,
        })
    rows.sort(key=lambda row: (row["category"].is_uncategorized, row["category"].name.casefold()))
    total_a = sum((row["amount_a"] for row in rows), Decimal("0.00"))
    total_b = sum((row["amount_b"] for row in rows), Decimal("0.00"))
    return {
        "comparison_rows": rows,
        "total_a": total_a,
        "total_b": total_b,
        "total_change": total_b - total_a,
    }
