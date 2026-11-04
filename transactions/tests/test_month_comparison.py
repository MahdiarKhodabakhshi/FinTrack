# FT-59 to FT-61: Month comparison totals, user separation and page behaviour.
from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from transactions.comparison import compare_category_spending
from transactions.models import Category, Transaction


class MonthComparisonTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("compare@example.com", name="Compare")
        self.other = User.objects.create_user("other-compare@example.com", name="Other")
        self.food = Category.objects.get(user=self.user, name="Food")
        self.transport = Category.objects.get(user=self.user, name="Transport")
        self.client.force_login(self.user)

    def test_category_totals_compare_selected_months_and_ignore_other_users(self):
        Transaction.objects.create(user=self.user, category=self.food, transaction_type="expense", amount="100.00", date=date(2026, 9, 12))
        Transaction.objects.create(user=self.user, category=self.food, transaction_type="expense", amount="75.00", date=date(2026, 10, 1))
        Transaction.objects.create(user=self.user, category=self.transport, transaction_type="expense", amount="25.00", date=date(2026, 10, 2))
        Transaction.objects.create(user=self.user, transaction_type="income", amount="400.00", date=date(2026, 10, 3))
        Transaction.objects.create(user=self.other, transaction_type="expense", amount="900.00", date=date(2026, 10, 4))

        result = compare_category_spending(self.user, date(2026, 9, 1), date(2026, 10, 1))
        self.assertEqual(result["total_a"], Decimal("100.00"))
        self.assertEqual(result["total_b"], Decimal("100.00"))
        self.assertEqual(result["total_change"], Decimal("0.00"))
        by_category = {row["category"].name: row for row in result["comparison_rows"]}
        self.assertEqual(by_category["Food"]["change"], Decimal("-25.00"))
        self.assertEqual(by_category["Transport"]["amount_a"], Decimal("0.00"))

    def test_comparison_page_renders_values_and_form_values(self):
        Transaction.objects.create(user=self.user, category=self.food, transaction_type="expense", amount="42.50", date=date(2026, 10, 5))
        response = self.client.get(reverse("transactions:comparison"), {"month_a": "2026-09", "month_b": "2026-10"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "September 2026 and October 2026")
        self.assertContains(response, "$42.50")
        self.assertContains(response, 'value="2026-09"')
        self.assertContains(response, 'value="2026-10"')

    def test_empty_months_have_a_clear_empty_state(self):
        response = self.client.get(reverse("transactions:comparison"), {"month_a": "2026-08", "month_b": "2026-09"})
        self.assertContains(response, "No expense transactions were recorded in either selected month.")
        self.assertEqual(response.context["comparison_rows"], [])

    def test_invalid_month_values_safely_use_default_months(self):
        response = self.client.get(reverse("transactions:comparison"), {"month_a": "bad", "month_b": "2026-15"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)

    def test_signed_out_cannot_view_comparison(self):
        self.client.logout()
        url = reverse("transactions:comparison")
        self.assertRedirects(self.client.get(url), reverse("accounts:login") + f"?next={url}")
