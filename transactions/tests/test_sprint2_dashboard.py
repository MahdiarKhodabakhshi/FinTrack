# FT-39 to FT-43: Dashboard totals, month selection and user separation.
from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from transactions.models import Budget, Category, Transaction


class DashboardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("dashboard@example.com", name="Dash")
        self.other = User.objects.create_user("other-dashboard@example.com", name="Other")
        self.food = Category.objects.get(user=self.user, name="Food")
        self.client.force_login(self.user)

    def test_dashboard_calculates_income_expenses_net_and_category_budget(self):
        Transaction.objects.create(user=self.user, transaction_type="income", amount="2400.00", date=date(2026, 10, 1), description="Pay")
        Transaction.objects.create(user=self.user, category=self.food, transaction_type="expense", amount="600.00", date=date(2026, 10, 31), description="Food")
        Transaction.objects.create(user=self.user, transaction_type="expense", amount="20.00", date=date(2026, 11, 1), description="Other month")
        Transaction.objects.create(user=self.other, transaction_type="income", amount="9000.00", date=date(2026, 10, 4))
        Budget.objects.create(user=self.user, category=self.food, month_start=date(2026, 10, 1), amount="500.00")
        response = self.client.get(reverse("transactions:dashboard") + "?month=2026-10")
        self.assertEqual(response.status_code, 200)
        self.assertEqual((response.context["income"], response.context["expenses"], response.context["net"]),
                         (Decimal("2400.00"), Decimal("600.00"), Decimal("1800.00")))
        self.assertContains(response, "$2,400.00")
        self.assertContains(response, "$600.00")
        self.assertContains(response, "+$1,800.00")
        row = next(row for row in response.context["category_rows"] if row["category"] == self.food)
        self.assertEqual(row["remaining"], Decimal("-100.00"))
        self.assertContains(response, "Food")
        self.assertContains(response, "−$100.00")

    def test_month_selector_rejects_bad_value_and_uses_current_month(self):
        response = self.client.get(reverse("transactions:dashboard") + "?month=not-a-month")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["month_form"].errors)
        self.assertEqual(response.context["month"].day, 1)
        self.assertContains(response, 'id="id_month_error"')

    def test_empty_dashboard_has_useful_budget_and_transaction_actions(self):
        response = self.client.get(reverse("transactions:dashboard") + "?month=2026-10")
        self.assertContains(response, "No category spending or budgets for this month yet.")
        self.assertContains(response, reverse("transactions:budgets"))
        self.assertContains(response, reverse("transactions:add"))
        self.assertEqual(response.context["income"], Decimal("0.00"))

    def test_root_sends_authenticated_users_to_dashboard(self):
        self.assertRedirects(self.client.get("/"), reverse("transactions:dashboard"), fetch_redirect_response=False)

    def test_signed_out_dashboard_redirects_to_login(self):
        self.client.logout()
        url = reverse("transactions:dashboard")
        self.assertRedirects(self.client.get(url), reverse("accounts:login") + f"?next={url}")
