# FT-40: Verify dashboard insights use private, fair monthly comparison periods.
from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from transactions.models import Category, Transaction
from transactions.spending_insights import get_monthly_spending_insight


class MonthlySpendingInsightTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("insight@example.com", name="Insight")
        self.other = User.objects.create_user("other-insight@example.com", name="Other")
        self.food = Category.objects.get(user=self.user, name="Food")
        self.transport = Category.objects.get(user=self.user, name="Transport")

    def add_expense(self, owner, category, amount, booked_date, description=""):
        return Transaction.objects.create(
            user=owner, category=category, transaction_type="expense",
            amount=amount, date=booked_date, description=description,
        )

    def test_current_month_compares_same_day_range_and_ignores_future_and_other_users(self):
        self.add_expense(self.user, self.food, "120.00", date(2026, 11, 2))
        self.add_expense(self.user, self.transport, "40.00", date(2026, 11, 10))
        self.add_expense(self.user, self.transport, "900.00", date(2026, 11, 11))
        self.add_expense(self.user, self.food, "100.00", date(2026, 10, 2))
        self.add_expense(self.user, self.food, "800.00", date(2026, 10, 11))
        other_food = Category.objects.get(user=self.other, name="Food")
        self.add_expense(self.other, other_food, "5000.00", date(2026, 11, 4))

        insight = get_monthly_spending_insight(self.user, date(2026, 11, 1), today=date(2026, 11, 10))
        self.assertEqual(insight["insight_total"], Decimal("160.00"))
        self.assertEqual(insight["insight_previous_total"], Decimal("100.00"))
        self.assertEqual(insight["insight_change"], Decimal("60.00"))
        self.assertEqual(insight["insight_change_percent"], 60)
        self.assertEqual(insight["insight_top_category"], self.food)
        self.assertEqual(insight["insight_top_share_percent"], 75)
        self.assertEqual(insight["insight_comparison_basis"], "the same dates last month")
        self.assertTrue(insight["insight_is_month_to_date"])
        self.assertEqual(insight["insight_period_through"], date(2026, 11, 10))

    def test_past_month_uses_full_months(self):
        self.add_expense(self.user, self.food, "90.00", date(2026, 9, 30))
        self.add_expense(self.user, self.food, "25.00", date(2026, 10, 1))
        insight = get_monthly_spending_insight(self.user, date(2026, 10, 1), today=date(2026, 11, 10))
        self.assertEqual(insight["insight_total"], Decimal("25.00"))
        self.assertEqual(insight["insight_previous_total"], Decimal("90.00"))
        self.assertEqual(insight["insight_change_percent"], -72)
        self.assertEqual(insight["insight_comparison_basis"], "the previous month")
        self.assertFalse(insight["insight_is_month_to_date"])
        self.assertEqual(insight["insight_period_through"], date(2026, 10, 31))

    def test_zero_previous_period_has_no_misleading_percentage(self):
        self.add_expense(self.user, self.food, "12.00", date(2026, 11, 5))
        insight = get_monthly_spending_insight(self.user, date(2026, 11, 1), today=date(2026, 11, 10))
        self.assertFalse(insight["insight_has_baseline"])
        self.assertIsNone(insight["insight_change_percent"])

    def test_empty_spending_returns_a_clean_empty_insight(self):
        insight = get_monthly_spending_insight(self.user, date(2026, 11, 1), today=date(2026, 11, 10))
        self.assertFalse(insight["insight_has_spending"])
        self.assertIsNone(insight["insight_top_category"])
        self.assertEqual(insight["insight_total"], Decimal("0.00"))

    def test_dashboard_renders_insight_and_top_category(self):
        self.add_expense(self.user, self.food, "35.00", date(2026, 10, 3))
        client = self.client
        client.force_login(self.user)
        response = client.get(reverse("transactions:dashboard"), {"month": "2026-10"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Monthly spending insight")
        self.assertContains(response, "Top spending category")
        self.assertContains(response, "Food")
        self.assertContains(response, "Explore comparison")
