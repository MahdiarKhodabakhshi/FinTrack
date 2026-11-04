# FT-44 to FT-47: Thresholds, dashboard alerts, and expense projections.
from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from transactions.budget_warnings import budget_status, projected_expense_warning
from transactions.models import Budget, Category, Transaction


class BudgetWarningTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("alerts@example.com", name="Alerts")
        self.other = User.objects.create_user("other-alerts@example.com", name="Other")
        self.food = Category.objects.get(user=self.user, name="Food")
        self.client.force_login(self.user)

    def test_warning_thresholds_are_80_percent_and_100_percent(self):
        self.assertEqual(budget_status(Decimal("79.99"), Decimal("100")), (None, 79))
        self.assertEqual(budget_status(Decimal("80"), Decimal("100")), ("near", 80))
        self.assertEqual(budget_status(Decimal("100"), Decimal("100")), ("exceeded", 100))
        self.assertEqual(budget_status(Decimal("125"), Decimal("100")), ("exceeded", 125))

    def test_dashboard_shows_near_and_exceeded_alerts_only_for_selected_month(self):
        Budget.objects.create(user=self.user, category=self.food, month_start=date(2026, 10, 1), amount="100.00")
        Transaction.objects.create(user=self.user, category=self.food, transaction_type="expense", amount="80.00", date=date(2026, 10, 4))
        response = self.client.get(reverse("transactions:dashboard") + "?month=2026-10")
        self.assertContains(response, "You have used 80% of this budget.")
        self.assertContains(response, 'role="alert"')

        Transaction.objects.create(user=self.user, category=self.food, transaction_type="expense", amount="20.00", date=date(2026, 10, 8))
        response = self.client.get(reverse("transactions:dashboard") + "?month=2026-10")
        self.assertContains(response, "You have reached or exceeded this budget.")

    def test_new_expense_warns_after_save_if_it_exceeds_its_monthly_budget(self):
        Budget.objects.create(user=self.user, category=self.food, month_start=date(2026, 10, 1), amount="100.00")
        Transaction.objects.create(user=self.user, category=self.food, transaction_type="expense", amount="90.00", date=date(2026, 10, 2))
        warning = projected_expense_warning(user=self.user, category=self.food, amount=Decimal("15.00"), date=date(2026, 10, 3))
        self.assertIn("above the $100.00 budget", warning)
        self.assertIsNone(projected_expense_warning(user=self.other, category=Category.objects.get(user=self.other, name="Food"), amount=Decimal("15.00"), date=date(2026, 10, 3)))

    def test_new_expense_displays_warning_but_is_still_saved(self):
        Budget.objects.create(user=self.user, category=self.food, month_start=date(2026, 10, 1), amount="100.00")
        Transaction.objects.create(user=self.user, category=self.food, transaction_type="expense", amount="90.00", date=date(2026, 10, 2))
        response = self.client.post(reverse("transactions:add"), {
            "transaction_type": "expense", "amount": "15.00", "date": "2026-10-03",
            "description": "Groceries", "category": self.food.pk,
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Transaction.objects.filter(user=self.user, description="Groceries").count(), 1)
        follow_up = self.client.get(response.url)
        self.assertContains(follow_up, "above the $100.00 budget")

    def test_expense_without_a_budget_does_not_warn(self):
        self.assertIsNone(projected_expense_warning(user=self.user, category=self.food, amount=Decimal("999.00"), date=date(2026, 10, 3)))
