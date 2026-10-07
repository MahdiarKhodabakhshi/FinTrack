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
    # FT-29 to FT-34: The category foreign key arrives in Sprint 2.

    class Meta:
        ordering = ["-date", "-created_at"]
        indexes = [models.Index(fields=["user", "-date"])]
        constraints = [models.CheckConstraint(condition=Q(amount__gt=0), name="transaction_amount_positive")]

    @property
    def signed_amount(self):
        return self.amount if self.transaction_type == self.TransactionType.INCOME else -self.amount

    def __str__(self):
        return f"{self.date}: {self.transaction_type} {self.amount}"
