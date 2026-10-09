# FT-03: User-owned income and expense records.
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q


class Transaction(models.Model):
    class TransactionType(models.TextChoices):
        INCOME = "income", "Income"
        EXPENSE = "expense", "Expense"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="transactions")
    transaction_type = models.CharField(max_length=7, choices=TransactionType.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    date = models.DateField()
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # FT-75, FT-76: Deleting a rule keeps its history; each occurrence is unique.
    recurring_source = models.ForeignKey("RecurringTransaction", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="generated_transactions")
    # FT-29 to FT-34: The category foreign key arrives in Sprint 2.

    class Meta:
        ordering = ["-date", "-created_at"]
        indexes = [models.Index(fields=["user", "-date"])]
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name="transaction_amount_positive"),
            models.UniqueConstraint(fields=["recurring_source", "date"],
                condition=Q(recurring_source__isnull=False), name="unique_recurring_occurrence"),
        ]

    @property
    def signed_amount(self):
        return self.amount if self.transaction_type == self.TransactionType.INCOME else -self.amount

    def __str__(self):
        return f"{self.date}: {self.transaction_type} {self.amount}"


# FT-75: Recognizable user-owned rules for repeating income and expenses.
class RecurringTransaction(models.Model):
    class Frequency(models.TextChoices):
        WEEKLY = "weekly", "Weekly"
        BIWEEKLY = "biweekly", "Every two weeks"
        MONTHLY = "monthly", "Monthly"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="recurring_transactions")
    transaction_type = models.CharField(max_length=7, choices=Transaction.TransactionType.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    description = models.CharField(max_length=255)
    frequency = models.CharField(max_length=8, choices=Frequency.choices)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    next_due_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["next_due_date", "description"]
        indexes = [models.Index(fields=["user", "is_active", "next_due_date"])]
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name="recurring_amount_positive"),
            models.CheckConstraint(condition=Q(end_date__isnull=True) | Q(end_date__gte=models.F("start_date")), name="recurring_end_after_start"),
        ]

    @property
    def signed_amount(self):
        return self.amount if self.transaction_type == Transaction.TransactionType.INCOME else -self.amount

    @property
    def is_ended(self):
        return bool(not self.is_active and self.end_date and self.next_due_date > self.end_date)

    def __str__(self):
        return f"{self.description} ({self.get_frequency_display()}, {self.amount})"
