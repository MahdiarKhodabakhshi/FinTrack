# FT-35 to FT-38: Budget persistence, validation, isolation and month calculations.
from datetime import date
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from transactions.models import Budget, Category, Transaction
from transactions.months import get_month_financials


class BudgetTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("budget@example.com", name="Budgeter")
        self.other = User.objects.create_user("other-budget@example.com", name="Other")
        self.food = Category.objects.get(user=self.user, name="Food")
        self.transport = Category.objects.get(user=self.user, name="Transport")
        self.client.force_login(self.user)

    def budget_post(self, **overrides):
        values = {"category": self.food.pk, "month_start": "2026-10", "amount": "300.00"}
        values.update(overrides)
        return self.client.post(reverse("transactions:budgets"), values)

    def test_page_shows_month_and_available_categories(self):
        response = self.client.get(reverse("transactions:budgets") + "?month=2026-10")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Monthly budgets")
        self.assertContains(response, "October 2026")
        self.assertContains(response, "Food")
        self.assertContains(response, 'type="month"')
        self.assertNotContains(response, "Uncategorized")

    def test_saves_and_updates_one_budget_per_user_category_month(self):
        response = self.budget_post()
        expected = reverse("transactions:budgets") + f"?month=2026-10&category={self.food.pk}"
        self.assertRedirects(response, expected, fetch_redirect_response=False)
        self.budget_post(amount="450.00")
        self.assertEqual(Budget.objects.filter(user=self.user, category=self.food, month_start=date(2026, 10, 1)).count(), 1)
        self.assertEqual(Budget.objects.get(user=self.user, category=self.food).amount, Decimal("450.00"))

    def test_budget_rejects_invalid_month_amount_and_foreign_category(self):
        for values, field in [({"amount": "0"}, "amount"), ({"amount": "1.001"}, "amount"), ({"month_start": "2026-13"}, "month_start")]:
            with self.subTest(values=values):
                response = self.budget_post(**values)
                self.assertEqual(response.status_code, 200)
                self.assertIn(field, response.context["form"].errors)
        other_food = Category.objects.get(user=self.other, name="Food")
        response = self.budget_post(category=other_food.pk)
        self.assertEqual(response.status_code, 200)
        self.assertIn("category", response.context["form"].errors)
        self.assertFalse(Budget.objects.exists())

    def test_budget_form_only_shows_the_signed_in_users_categories(self):
        response = self.client.get(reverse("transactions:budgets"))
        choices = response.context["form"].fields["category"].queryset
        self.assertEqual(set(choices.values_list("user_id", flat=True)), {self.user.pk})

    def test_spent_and_remaining_are_user_scoped_and_month_bounded(self):
        Transaction.objects.create(user=self.user, category=self.food, transaction_type="expense", amount="125.50", date=date(2026, 10, 1))
        Transaction.objects.create(user=self.user, category=self.food, transaction_type="expense", amount="74.50", date=date(2026, 10, 31))
        Transaction.objects.create(user=self.user, category=self.food, transaction_type="expense", amount="90.00", date=date(2026, 11, 1))
        Transaction.objects.create(user=self.other, transaction_type="expense", amount="500.00", date=date(2026, 10, 10))
        Budget.objects.create(user=self.user, category=self.food, month_start=date(2026, 10, 1), amount="150.00")
        row = next(row for row in get_month_financials(self.user, date(2026, 10, 1))["category_rows"] if row["category"] == self.food)
        self.assertEqual(row["spent"], Decimal("200.00"))
        self.assertEqual(row["remaining"], Decimal("-50.00"))

    def test_signed_out_cannot_view_or_save_budgets(self):
        self.client.logout()
        url = reverse("transactions:budgets")
        self.assertRedirects(self.client.get(url), reverse("accounts:login") + f"?next={url}")
        self.assertRedirects(self.client.post(url, {"category": self.food.pk, "month_start": "2026-10", "amount": "10"}), reverse("accounts:login") + f"?next={url}")

    def test_empty_month_calculations_use_decimal_zero(self):
        summary = get_month_financials(self.user, date(2026, 10, 1))
        self.assertEqual(summary["income"], Decimal("0.00"))
        self.assertEqual(summary["expenses"], Decimal("0.00"))
        self.assertEqual(summary["net"], Decimal("0.00"))

    def test_database_enforces_positive_budget_and_unique_monthly_category(self):
        Budget.objects.create(user=self.user, category=self.food, month_start=date(2026, 10, 1), amount="10.00")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Budget.objects.create(user=self.user, category=self.food, month_start=date(2026, 10, 1), amount="20.00")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Budget.objects.create(user=self.user, category=self.transport, month_start=date(2026, 10, 1), amount="0.00")
