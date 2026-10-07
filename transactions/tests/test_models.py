# FT-03: Verify persistence, ordering, amount constraints, and cascading deletion.
from datetime import date
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase

from accounts.models import User
from transactions.models import Transaction


class TransactionModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("user@example.com", name="User")

    def make_transaction(self, **overrides):
        fields = {"user": self.user, "transaction_type": "income", "amount": Decimal("10.00"), "date": date(2026, 10, 1)}
        fields.update(overrides)
        return Transaction.objects.create(**fields)

    def test_default_ordering(self):
        older = self.make_transaction(date=date(2026, 9, 1))
        first = self.make_transaction()
        latest = self.make_transaction()
        self.assertEqual(list(Transaction.objects.all()), [latest, first, older])

    def test_database_rejects_nonpositive_amounts(self):
        for amount in (Decimal("0.00"), Decimal("-1.00")):
            with self.subTest(amount=amount), self.assertRaises(IntegrityError), transaction.atomic():
                self.make_transaction(amount=amount)

    def test_signed_amount(self):
        income = self.make_transaction()
        expense = self.make_transaction(transaction_type="expense")
        self.assertEqual(income.signed_amount, Decimal("10.00"))
        self.assertEqual(expense.signed_amount, Decimal("-10.00"))

    def test_deleting_user_cascades(self):
        self.make_transaction()
        self.user.delete()
        self.assertFalse(Transaction.objects.exists())
