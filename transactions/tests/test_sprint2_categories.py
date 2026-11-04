# FT-29 to FT-34: Category ownership, defaults, management and transaction links.
from datetime import date
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from transactions.models import Budget, Category, RecurringTransaction, Transaction
from transactions.recurring import generate_due_transactions


class CategoryManagementTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("category@example.com", name="Category User")
        self.other = User.objects.create_user("other-category@example.com", name="Other")
        self.client.force_login(self.user)

    def test_new_users_get_private_default_and_uncategorized_categories(self):
        defaults = Category.objects.filter(user=self.user, is_default=True)
        self.assertEqual(defaults.count(), 8)
        self.assertEqual(defaults.filter(is_uncategorized=True).count(), 1)
        self.assertFalse(defaults.filter(user=self.other).exists())
        self.assertFalse(set(defaults.values_list("pk", flat=True)) & set(Category.objects.filter(user=self.other).values_list("pk", flat=True)))

    def test_category_page_lists_starter_categories_and_custom_actions(self):
        custom = Category.objects.create(user=self.user, name="Pets")
        response = self.client.get(reverse("transactions:categories"))
        self.assertContains(response, "Starter categories")
        self.assertContains(response, "Food")
        self.assertContains(response, "Pets")
        self.assertContains(response, reverse("transactions:category_edit", args=[custom.pk]))

    def test_create_and_rename_category_trim_names_and_reject_case_duplicates(self):
        response = self.client.post(reverse("transactions:category_add"), {"name": "  Pets  "})
        self.assertRedirects(response, reverse("transactions:categories"), fetch_redirect_response=False)
        pets = Category.objects.get(user=self.user, name="Pets")
        duplicate = self.client.post(reverse("transactions:category_add"), {"name": "pETS"})
        self.assertEqual(duplicate.status_code, 200)
        self.assertContains(duplicate, "You already have a category with this name.")
        self.assertEqual(Category.objects.filter(user=self.user, name__iexact="pets").count(), 1)
        response = self.client.post(reverse("transactions:category_edit", args=[pets.pk]), {"name": "Animal care"})
        self.assertRedirects(response, reverse("transactions:categories"), fetch_redirect_response=False)
        pets.refresh_from_db()
        self.assertEqual(pets.name, "Animal care")

    def test_delete_reassigns_history_and_recurring_rules_and_removes_budgets(self):
        category = Category.objects.create(user=self.user, name="Old label")
        tx = Transaction.objects.create(user=self.user, category=category, transaction_type="expense", amount="12.00", date=date(2026, 10, 2))
        rule = RecurringTransaction.objects.create(user=self.user, category=category, transaction_type="expense", amount="8.00", description="Old label", frequency="monthly", start_date=date(2026, 10, 1), next_due_date=date(2026, 10, 1))
        Budget.objects.create(user=self.user, category=category, month_start=date(2026, 10, 1), amount="30.00")
        url = reverse("transactions:category_delete", args=[category.pk])
        self.assertContains(self.client.get(url), "transactions and recurring rules will move")
        self.assertRedirects(self.client.post(url), reverse("transactions:categories"), fetch_redirect_response=False)
        fallback = Category.objects.get(user=self.user, is_uncategorized=True)
        tx.refresh_from_db()
        rule.refresh_from_db()
        self.assertEqual(tx.category, fallback)
        self.assertEqual(rule.category, fallback)
        self.assertFalse(Budget.objects.filter(category=category).exists())
        self.assertFalse(Category.objects.filter(pk=category.pk).exists())

    def test_default_categories_cannot_be_renamed_or_deleted(self):
        category = Category.objects.get(user=self.user, name="Food")
        self.assertEqual(self.client.get(reverse("transactions:category_edit", args=[category.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("transactions:category_delete", args=[category.pk])).status_code, 404)

    def test_category_views_are_private(self):
        category = Category.objects.create(user=self.other, name="Private")
        self.assertNotContains(self.client.get(reverse("transactions:categories")), "Private")
        self.assertEqual(self.client.get(reverse("transactions:category_edit", args=[category.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("transactions:category_delete", args=[category.pk])).status_code, 404)

    def test_transaction_form_rejects_another_users_category(self):
        url = reverse("transactions:add")
        response = self.client.post(url, {"transaction_type": "expense", "amount": "5.00", "date": "2026-10-01", "description": "", "category": Category.objects.get(user=self.other, name="Food").pk})
        self.assertEqual(response.status_code, 200)
        self.assertIn("category", response.context["form"].errors)
        self.assertFalse(Transaction.objects.exists())

    def test_recurring_expenses_keep_the_selected_category_when_generated(self):
        # FT-76: Keep this acceptance test independent of the wall-clock date.
        with patch("transactions.recurring.timezone.localdate", return_value=date(2026, 10, 1)):
            response = self.client.post(reverse("transactions:recurring_add"), {
                "transaction_type": "expense", "amount": "25.00", "description": "Groceries",
                "frequency": "monthly", "start_date": "2026-10-01", "end_date": "",
                "category": self.user.categories.get(name="Food").pk,
            })
        self.assertEqual(response.status_code, 302)
        rule = RecurringTransaction.objects.get(user=self.user)
        self.assertEqual(rule.category.name, "Food")
        generate_due_transactions(user=self.user, today=date(2026, 10, 1))
        self.assertEqual(rule.generated_transactions.get().category, rule.category)

    def test_signed_out_category_pages_redirect(self):
        self.client.logout()
        for url in (reverse("transactions:categories"), reverse("transactions:budgets")):
            with self.subTest(url=url):
                self.assertRedirects(self.client.get(url), reverse("accounts:login") + f"?next={url}")

    def test_anonymous_category_delete_is_protected(self):
        category = Category.objects.create(user=self.user, name="Private custom")
        self.client.logout()
        url = reverse("transactions:category_delete", args=[category.pk])
        self.assertRedirects(self.client.get(url), reverse("accounts:login") + f"?next={url}")
        self.assertRedirects(self.client.post(url), reverse("accounts:login") + f"?next={url}")
