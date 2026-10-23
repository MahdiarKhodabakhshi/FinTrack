# FT-24 to FT-28: Safe transaction editing and deletion.
from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from transactions.models import Category, RecurringTransaction, Transaction


class TransactionManagementTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("edit@example.com", name="Editor")
        self.other = User.objects.create_user("other-edit@example.com", name="Other")
        self.food = Category.objects.get(user=self.user, name="Food")
        self.transport = Category.objects.get(user=self.user, name="Transport")
        self.client.force_login(self.user)
        self.record = Transaction.objects.create(user=self.user, category=self.food, transaction_type="expense", amount=Decimal("24.50"), date=date(2026, 10, 3), description="Market")

    def edit_url(self, record=None):
        return reverse("transactions:edit", args=[(record or self.record).pk])

    def delete_url(self, record=None):
        return reverse("transactions:delete", args=[(record or self.record).pk])

    def test_edit_form_is_prefilled_and_uses_existing_validation(self):
        response = self.client.get(self.edit_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Edit transaction")
        self.assertEqual(response.context["form"].initial["description"], "Market")
        self.assertEqual(response.context["form"].initial["category"], self.food.pk)
        invalid = self.client.post(self.edit_url(), {"transaction_type": "expense", "amount": "0", "date": "2026-10-03", "description": "Market", "category": self.food.pk})
        self.assertEqual(invalid.status_code, 200)
        self.assertIn("amount", invalid.context["form"].errors)
        self.record.refresh_from_db()
        self.assertEqual(self.record.amount, Decimal("24.50"))

    def test_edit_updates_values_and_preserves_a_safe_filtered_return_url(self):
        next_url = reverse("transactions:list") + "?q=market&type=expense"
        response = self.client.post(self.edit_url() + "?next=" + next_url.replace("&", "%26"), {
            "transaction_type": "expense", "amount": "30.00", "date": "2026-10-04", "description": "Weekly shop", "category": self.transport.pk, "next": next_url,
        })
        self.assertRedirects(response, next_url, fetch_redirect_response=False)
        self.record.refresh_from_db()
        self.assertEqual((self.record.amount, self.record.description, self.record.category), (Decimal("30.00"), "Weekly shop", self.transport))

    def test_income_clears_a_category(self):
        response = self.client.post(self.edit_url(), {"transaction_type": "income", "amount": "400.00", "date": "2026-10-04", "description": "Refund", "category": self.food.pk})
        self.assertRedirects(response, reverse("transactions:list"), fetch_redirect_response=False)
        self.record.refresh_from_db()
        self.assertIsNone(self.record.category)

    def test_generated_transaction_cannot_be_moved_to_an_existing_occurrence_date(self):
        rule = RecurringTransaction.objects.create(user=self.user, category=self.food, transaction_type="expense", amount="10", description="Scheduled", frequency="weekly", start_date=date(2026, 10, 1), next_due_date=date(2026, 10, 1))
        self.record.recurring_source = rule
        self.record.date = date(2026, 10, 3)
        self.record.save(update_fields=["recurring_source", "date"])
        Transaction.objects.create(user=self.user, category=self.food, recurring_source=rule, transaction_type="expense", amount="10", date=date(2026, 10, 10))
        response = self.client.post(self.edit_url(), {"transaction_type": "expense", "amount": "24.50", "date": "2026-10-10", "description": "Market", "category": self.food.pk})
        self.assertEqual(response.status_code, 200)
        self.assertIn("date", response.context["form"].errors)

    def test_edit_and_delete_of_another_users_record_return_404(self):
        foreign = Transaction.objects.create(user=self.other, transaction_type="income", amount="9.00", date=date(2026, 10, 1))
        self.assertEqual(self.client.get(self.edit_url(foreign)).status_code, 404)
        self.assertEqual(self.client.post(self.edit_url(foreign), {}).status_code, 404)
        self.assertEqual(self.client.get(self.delete_url(foreign)).status_code, 404)
        self.assertEqual(self.client.post(self.delete_url(foreign)).status_code, 404)
        self.assertTrue(Transaction.objects.filter(pk=foreign.pk).exists())

    def test_delete_requires_confirmation_and_post(self):
        url = self.delete_url() + "?next=%2Ftransactions%2F%3Fq%3Dmarket"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'method="post"')
        self.assertContains(response, "This removes the transaction from your history.")
        self.assertTrue(Transaction.objects.filter(pk=self.record.pk).exists())
        response = self.client.post(url, {"next": reverse("transactions:list")})
        self.assertRedirects(response, reverse("transactions:list"), fetch_redirect_response=False)
        self.assertFalse(Transaction.objects.filter(pk=self.record.pk).exists())

    def test_external_return_url_is_rejected(self):
        response = self.client.post(self.edit_url(), {"transaction_type": "expense", "amount": "30", "date": "2026-10-04", "description": "Changed", "category": self.food.pk, "next": "https://attacker.example/"})
        self.assertRedirects(response, reverse("transactions:list"), fetch_redirect_response=False)

    def test_signed_out_edit_and_delete_redirect_to_login(self):
        self.client.logout()
        for url in (self.edit_url(), self.delete_url()):
            with self.subTest(url=url):
                self.assertRedirects(self.client.get(url), reverse("accounts:login") + f"?next={url}")
