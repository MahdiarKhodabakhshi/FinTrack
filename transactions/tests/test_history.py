# FT-23: Private history, newest-first display, money, empty state and escaping.
from datetime import date, datetime, timezone as dt_timezone

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from transactions.models import Transaction


class TransactionHistoryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('history@example.com', name='History')
        self.other = User.objects.create_user('other@example.com', name='Other')
        self.client.force_login(self.user)

    def record(self, **overrides):
        values = {'user': self.user, 'transaction_type': 'income', 'amount': '1234.50', 'date': date(2026, 10, 1), 'description': 'Paycheque'}
        values.update(overrides)
        return Transaction.objects.create(**values)

    def history(self):
        response = self.client.get(reverse('transactions:list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'transactions/transaction_list.html')
        return response

    def test_empty_history_has_clear_message_and_add_link(self):
        response = self.history()
        self.assertContains(response, 'No transactions yet')
        self.assertContains(response, 'Add your first transaction')
        self.assertContains(response, f'href="{reverse("transactions:add")}"')
        self.assertNotContains(response, '<table')

    def test_other_users_history_is_never_visible(self):
        own = self.record()
        self.record(user=self.other, description='Other private salary')
        response = self.history()
        self.assertEqual(list(response.context['transactions']), [own])
        self.assertNotContains(response, 'Other private salary')

    def test_only_other_users_rows_still_means_empty_history(self):
        self.record(user=self.other, description='Other private salary')
        response = self.history()
        self.assertContains(response, 'No transactions yet')
        self.assertNotContains(response, 'Other private salary')

    def test_newest_date_then_creation_time_ordering(self):
        older = self.record(date=date(2026, 9, 30), description='Older date')
        first = self.record(date=date(2026, 10, 1), description='First same day')
        last = self.record(date=date(2026, 10, 1), description='Last same day')
        Transaction.objects.filter(pk=first.pk).update(created_at=datetime(2026, 10, 1, 10, tzinfo=dt_timezone.utc))
        Transaction.objects.filter(pk=last.pk).update(created_at=datetime(2026, 10, 1, 11, tzinfo=dt_timezone.utc))
        Transaction.objects.filter(pk=older.pk).update(created_at=datetime(2026, 10, 2, tzinfo=dt_timezone.utc))
        response = self.history()
        self.assertEqual(list(response.context['transactions']), [last, first, older])
        html = response.content.decode()
        self.assertLess(html.index('Last same day'), html.index('First same day'))
        self.assertLess(html.index('First same day'), html.index('Older date'))

    def test_type_labels_signed_money_and_machine_readable_dates(self):
        self.record()
        self.record(transaction_type='expense', amount='20', description='Groceries')
        response = self.history()
        for text in ('Income', 'Expense', '+$1,234.50', '−$20.00', '<time datetime="2026-10-01">'):
            self.assertContains(response, text)

    def test_blank_description_and_html_escaping(self):
        self.record(description='')
        self.record(description='<script>alert("unsafe")</script>')
        response = self.history()
        self.assertContains(response, '<span class="text-body-secondary">—</span>', html=True)
        self.assertContains(response, '&lt;script&gt;')
        self.assertNotContains(response, '<script>alert(')

    def test_history_switches_with_the_logged_in_user(self):
        self.record(description='A private record')
        self.record(user=self.other, description='B private record')
        self.assertContains(self.history(), 'A private record')
        self.client.post(reverse('accounts:logout'))
        self.client.force_login(self.other)
        response = self.history()
        self.assertContains(response, 'B private record')
        self.assertNotContains(response, 'A private record')

    def test_signed_out_history_redirects_to_login(self):
        self.client.logout()
        self.assertRedirects(self.client.get(reverse('transactions:list')), reverse('accounts:login') + '?next=/transactions/')
