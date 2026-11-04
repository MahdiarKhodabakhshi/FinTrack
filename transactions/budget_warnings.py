# FT-44, FT-45, FT-46: Shared budget warning thresholds and projection logic.
from decimal import Decimal

from django.db.models import Sum

from .models import Budget, Transaction

NEAR_BUDGET_THRESHOLD = Decimal("0.80")
FULL_BUDGET_THRESHOLD = Decimal("1.00")


def budget_status(spent, budget):
    """Return the warning state and percentage for a budget row."""
    if budget is None or budget <= 0:
        return None, None
    ratio = spent / budget
    if ratio >= FULL_BUDGET_THRESHOLD:
        state = "exceeded"
    elif ratio >= NEAR_BUDGET_THRESHOLD:
        state = "near"
    else:
        state = None
    return state, int(ratio * 100)


def projected_expense_warning(*, user, category, amount, date):
    """Warn, without blocking, when a new expense exceeds its monthly budget."""
    month_start = date.replace(day=1)
    budget = Budget.objects.filter(user=user, category=category, month_start=month_start).first()
    if budget is None:
        return None
    if month_start.month == 12:
        month_end = month_start.replace(year=month_start.year + 1, month=1)
    else:
        month_end = month_start.replace(month=month_start.month + 1)
    spent = Transaction.objects.filter(
        user=user,
        category=category,
        transaction_type=Transaction.TransactionType.EXPENSE,
        date__gte=month_start,
        date__lt=month_end,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    projected = spent + amount
    if projected > budget.amount:
        return (f"This expense brings {category.name} spending to ${projected:,.2f}, "
                f"above the ${budget.amount:,.2f} budget for {month_start:%B %Y}.")
    return None
