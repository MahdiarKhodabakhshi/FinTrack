# FT-35, FT-39, FT-42: Shared Toronto-local month parsing and summary calculations.
from calendar import monthrange
from datetime import date
from decimal import Decimal

from django import forms
from django.db.models import Q, Sum
from django.utils import timezone

from .budget_warnings import budget_status
from .models import Budget, Category, Transaction


class MonthField(forms.DateField):
    """Accept an HTML month value and store it as that month's first date."""
    def __init__(self, **kwargs):
        kwargs.setdefault("input_formats", ["%Y-%m"])
        kwargs.setdefault("widget", forms.DateInput(format="%Y-%m", attrs={"type": "month"}))
        super().__init__(**kwargs)

    def prepare_value(self, value):
        if isinstance(value, date):
            return value.strftime("%Y-%m")
        return value

    def to_python(self, value):
        parsed = super().to_python(value)
        return parsed.replace(day=1) if parsed else parsed


class MonthSelectionForm(forms.Form):
    month = MonthField(label="Month")


def current_month_start():
    """Return the first date of the current Toronto-local month."""
    return timezone.localdate().replace(day=1)


def next_month_start(month_start):
    """Return the exclusive end date for a month range."""
    if month_start.month == 12:
        return date(month_start.year + 1, 1, 1)
    return date(month_start.year, month_start.month + 1, 1)


def month_dates(month_start):
    """Return the first and inclusive last dates for a month."""
    last_day = monthrange(month_start.year, month_start.month)[1]
    return month_start, date(month_start.year, month_start.month, last_day)


def get_month_financials(user, month_start):
    """FT-37, FT-39, FT-41: Calculate only this user's income, expenses and category budgets."""
    next_start = next_month_start(month_start)
    transactions = Transaction.objects.filter(user=user, date__gte=month_start, date__lt=next_start)
    totals = transactions.aggregate(
        income=Sum("amount", filter=Q(transaction_type=Transaction.TransactionType.INCOME)),
        expenses=Sum("amount", filter=Q(transaction_type=Transaction.TransactionType.EXPENSE)),
    )
    income = totals["income"] or Decimal("0.00")
    expenses = totals["expenses"] or Decimal("0.00")
    spent_rows = transactions.filter(transaction_type=Transaction.TransactionType.EXPENSE).values("category_id").annotate(spent=Sum("amount"))
    spent_by_category = {row["category_id"]: row["spent"] for row in spent_rows}
    uncategorized_id = Category.objects.filter(user=user, is_uncategorized=True).values_list("pk", flat=True).first()
    if None in spent_by_category and uncategorized_id is not None:
        spent_by_category[uncategorized_id] = spent_by_category.get(uncategorized_id, Decimal("0.00")) + spent_by_category.pop(None)
    budget_rows = Budget.objects.filter(user=user, month_start=month_start).select_related("category")
    budgets_by_category = {budget.category_id: budget.amount for budget in budget_rows}
    visible_category_ids = set(spent_by_category) | set(budgets_by_category)
    categories = Category.objects.filter(user=user, pk__in=visible_category_ids).order_by("is_uncategorized", "name")
    category_rows = []
    for category in categories:
        spent = spent_by_category.get(category.pk, Decimal("0.00"))
        budget = budgets_by_category.get(category.pk)
        warning_state, budget_percent = budget_status(spent, budget)
        category_rows.append({
            "category": category,
            "spent": spent,
            "budget": budget,
            "remaining": budget - spent if budget is not None else None,
            "warning_state": warning_state,
            "budget_percent": budget_percent,
        })
    return {
        "income": income,
        "expenses": expenses,
        "net": income - expenses,
        "category_rows": category_rows,
    }
