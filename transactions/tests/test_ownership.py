# FT-18, FT-21: Verify user boundaries independently of the auth feature branch.
from datetime import date
from decimal import Decimal

from django.http import Http404
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from transactions.models import Transaction
from transactions.views import get_user_transaction_or_404


class TransactionOwnershipTests(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user("a@example.com", name="A")
        self.user_b = User.objects.create_user("b@example.com", name="B")
        self.record_a = Transaction.objects.create(user=self.user_a, transaction_type="income", amount=Decimal("10.00"), date=date(2026, 10, 1), description="A-private-record")
        self.record_b = Transaction.objects.create(user=self.user_b, transaction_type="expense", amount=Decimal("20.00"), date=date(2026, 10, 2), description="B-private-record")

    def test_history_excludes_other_users(self):
        self.client.force_login(self.user_a)
        response = self.client.get(reverse("transactions:list"))
        self.assertEqual(list(response.context["transactions"]), [self.record_a])
        self.assertContains(response, "A-private-record")
        self.assertNotContains(response, "B-private-record")

    def test_forged_user_is_ignored(self):
        self.client.force_login(self.user_a)
        response = self.client.post(reverse("transactions:add"), {
            "user": self.user_b.pk, "transaction_type": "expense", "amount": "5.25",
            "date": "2026-10-03", "description": "Forged-owner-record",
        })
        self.assertRedirects(response, reverse("transactions:list"))
        saved = Transaction.objects.get(description="Forged-owner-record")
        self.assertEqual(saved.user, self.user_a)
        self.assertNotEqual(saved.user, self.user_b)

    def test_other_users_lookup_returns_404(self):
        with self.assertRaises(Http404):
            get_user_transaction_or_404(self.user_a, self.record_b.pk)
        self.assertEqual(get_user_transaction_or_404(self.user_a, self.record_a.pk), self.record_a)

    def test_anonymous_requests_redirect(self):
        for route in ("transactions:list", "transactions:add"):
            url = reverse(route)
            with self.subTest(route=route):
                self.assertRedirects(self.client.get(url), reverse("accounts:login") + "?next=" + url)
        self.assertRedirects(self.client.post(reverse("transactions:add"), {
            "transaction_type": "income", "amount": "1.00", "date": "2026-10-03",
        }), reverse("accounts:login") + "?next=/transactions/add/")
        self.assertEqual(Transaction.objects.count(), 2)
