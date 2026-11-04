# FT-66, FT-67: Final authorization regression across financial pages and mutations.
from datetime import date

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from transactions.models import Budget, Category, RecurringTransaction, Transaction


class FinalSecurityTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("owner-secure@example.com", name="Owner")
        self.visitor = User.objects.create_user("visitor-secure@example.com", name="Visitor")
        self.custom_category = Category.objects.create(user=self.owner, name="Private category")
        self.expense = Transaction.objects.create(
            user=self.owner, category=self.custom_category, transaction_type="expense",
            amount="9843.21", date=date(2026, 10, 10), description="Private purchase marker",
        )
        self.rule = RecurringTransaction.objects.create(
            user=self.owner, category=self.custom_category, transaction_type="expense", amount="55.00",
            description="Private recurring marker", frequency="monthly", start_date=date(2026, 10, 1),
            next_due_date=date(2027, 1, 1),
        )
        Budget.objects.create(user=self.owner, category=self.custom_category, month_start=date(2026, 10, 1), amount="10000.00")
        self.client.force_login(self.visitor)

    def test_another_user_cannot_view_or_mutate_private_object_urls(self):
        paths = [
            (reverse("transactions:edit", args=[self.expense.pk]), 404),
            (reverse("transactions:delete", args=[self.expense.pk]), 404),
            (reverse("transactions:category_edit", args=[self.custom_category.pk]), 404),
            (reverse("transactions:category_delete", args=[self.custom_category.pk]), 404),
            (reverse("transactions:recurring_toggle", args=[self.rule.pk]), 405),
            (reverse("transactions:recurring_delete", args=[self.rule.pk]), 404),
        ]
        for path, get_status in paths:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, get_status)
                post_response = self.client.post(path, {})
                self.assertEqual(post_response.status_code, 404)
        self.assertTrue(Transaction.objects.filter(pk=self.expense.pk, user=self.owner).exists())
        self.assertTrue(Category.objects.filter(pk=self.custom_category.pk, user=self.owner).exists())
        self.assertTrue(RecurringTransaction.objects.filter(pk=self.rule.pk, user=self.owner).exists())

    def test_private_pages_never_render_another_users_rows_or_categories(self):
        for path, marker in [
            (reverse("transactions:list"), "Private purchase marker"),
            (reverse("transactions:dashboard") + "?month=2026-10", "Private purchase marker"),
            (reverse("transactions:categories"), "Private category"),
            (reverse("transactions:recurring_list"), "Private recurring marker"),
        ]:
            with self.subTest(path=path):
                self.assertNotContains(self.client.get(path), marker)
        self.assertFalse(Budget.objects.filter(user=self.visitor).exists())

    def test_foreign_category_cannot_be_used_to_set_another_users_budget(self):
        response = self.client.post(reverse("transactions:budgets"), {
            "category": self.custom_category.pk, "month_start": "2026-10", "amount": "5.00",
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("category", response.context["form"].errors)
        self.assertFalse(Budget.objects.filter(user=self.visitor).exists())
