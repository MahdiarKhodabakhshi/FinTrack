# FT-40: Explain the largest category and compare spending over fair periods.
from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Sum
from django.utils import timezone

from .models import Category, Transaction
from .months import current_month_start, next_month_start


def _expense_snapshot(user, start, end):
    """Return an owner's expense total and category totals in [start, end)."""
    expenses = Transaction.objects.filter(
        user=user,
        transaction_type=Transaction.TransactionType.EXPENSE,
        date__gte=start,
        date__lt=end,
    )
    grouped = list(expenses.values("category_id").annotate(total=Sum("amount")))
    category_ids = {row["category_id"] for row in grouped if row["category_id"] is not None}
    categories = {category.pk: category for category in Category.objects.filter(user=user, pk__in=category_ids)}
    uncategorized = Category.objects.filter(user=user, is_uncategorized=True).first()
    totals_by_category = {}
    total = Decimal("0.00")
    for row in grouped:
        amount = row["total"] or Decimal("0.00")
        total += amount
        category_id = row["category_id"]
        category = categories.get(category_id) if category_id is not None else uncategorized
        if category is not None:
            previous_amount = totals_by_category.get(category.pk, (category, Decimal("0.00")))[1]
            totals_by_category[category.pk] = (category, previous_amount + amount)
    return total, totals_by_category


def get_monthly_spending_insight(user, month_start, *, today=None):
    """FT-40: Summarize the top category and compare like-for-like expense periods."""
    today = today or timezone.localdate()
    today_month = today.replace(day=1)
    previous_start = date(month_start.year - (month_start.month == 1), 12 if month_start.month == 1 else month_start.month - 1, 1)

    if month_start == today_month:
        current_end = today + timedelta(days=1)
        previous_day = min(today.day, monthrange(previous_start.year, previous_start.month)[1])
        previous_end = date(previous_start.year, previous_start.month, previous_day) + timedelta(days=1)
        comparison_basis = "the same dates last month"
    else:
        current_end = next_month_start(month_start)
        previous_end = month_start
        comparison_basis = "the previous month"

    current_total, categories = _expense_snapshot(user, month_start, current_end)
    previous_total, _ = _expense_snapshot(user, previous_start, previous_end)
    top_category, top_amount = (None, Decimal("0.00"))
    if categories:
        top_category, top_amount = sorted(
            categories.values(), key=lambda row: (-row[1], row[0].name.casefold())
        )[0]

    change = current_total - previous_total
    change_percent = None
    if previous_total:
        change_percent = int((change * 100 / previous_total).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    top_share_percent = 0
    if current_total:
        top_share_percent = int((top_amount * 100 / current_total).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    return {
        "insight_total": current_total,
        "insight_previous_total": previous_total,
        "insight_change": change,
        "insight_change_percent": change_percent,
        "insight_comparison_basis": comparison_basis,
        "insight_period_through": current_end - timedelta(days=1),
        "insight_is_month_to_date": month_start == today_month,
        "insight_top_category": top_category,
        "insight_top_amount": top_amount,
        "insight_top_share_percent": top_share_percent,
        "insight_has_spending": bool(current_total),
        "insight_has_baseline": bool(previous_total),
    }
