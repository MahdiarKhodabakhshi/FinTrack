# FT-75, FT-76: Owner-only pages, lazy generation, accessible errors and POST actions.
from datetime import date
from unittest.mock import patch

from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import User
from transactions.models import RecurringTransaction, Transaction


class RecurringViewTests(TestCase):
    def setUp(self):
        self.today_patch = patch('django.utils.timezone.localdate', return_value=date(2026, 10, 8))
        self.today_patch.start()
        self.addCleanup(self.today_patch.stop)
        self.user = User.objects.create_user('rules@example.com', name='Rules')
        self.other = User.objects.create_user('other@example.com', name='Other')
        self.client.force_login(self.user)

    def rule(self, **overrides):
        data = {'user': self.user, 'transaction_type': 'expense', 'amount': '20.00', 'description': 'Rent', 'frequency': 'monthly',
                'start_date': date(2026, 8, 31), 'next_due_date': date(2026, 8, 31)}
        data.update(overrides)
        return RecurringTransaction.objects.create(**data)

    def data(self, **overrides):
        data = {'transaction_type': 'income', 'amount': '500.00', 'description': 'Paycheque', 'frequency': 'weekly', 'start_date': '2026-10-08', 'end_date': ''}
        data.update(overrides)
        return data

    def test_create_sets_owner_ignores_forged_fields_and_announces_count(self):
        response = self.client.post(reverse('transactions:recurring_add'), self.data(user=self.other.pk, next_due_date='2030-01-01', is_active='false'), follow=True)
        self.assertContains(response, 'Recurring transaction created. 1 entry added so far.')
        rule = RecurringTransaction.objects.get()
        self.assertEqual(rule.user, self.user)
        self.assertEqual(rule.next_due_date, date(2026, 10, 15))
        self.assertTrue(rule.is_active)
        self.assertEqual(rule.generated_transactions.get().user, self.user)

    def test_plural_creation_message(self):
        response = self.client.post(reverse('transactions:recurring_add'), self.data(start_date='2026-10-01'), follow=True)
        self.assertContains(response, 'Recurring transaction created. 2 entries added so far.')

    def test_form_validation_and_year_boundary(self):
        for overrides, field in [({'end_date': '2026-10-07'}, 'end_date'), ({'start_date': '2025-10-06'}, 'start_date'), ({'amount': '0'}, 'amount'), ({'description': ''}, 'description')]:
            with self.subTest(overrides=overrides):
                response = self.client.post(reverse('transactions:recurring_add'), self.data(**overrides))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, f'id="id_{field}_error"')
                self.assertFalse(RecurringTransaction.objects.exists())
        from transactions.recurring_forms import RecurringTransactionForm
        self.assertTrue(RecurringTransactionForm(self.data(start_date='2025-10-07')).is_valid())

    def test_toggle_get_405_and_pause_resume(self):
        rule = self.rule(start_date=date(2026, 10, 8), next_due_date=date(2026, 10, 8), frequency='weekly')
        url = reverse('transactions:recurring_toggle', args=[rule.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url).status_code, 302)
        rule.refresh_from_db()
        self.assertFalse(rule.is_active)
        response = self.client.post(url, follow=True)
        self.assertContains(response, 'Recurring transaction resumed.')
        rule.refresh_from_db()
        self.assertTrue(rule.is_active)

    def test_cross_user_toggle_and_delete_return_404(self):
        rule = self.rule(user=self.other)
        for route in ['transactions:recurring_toggle', 'transactions:recurring_delete']:
            with self.subTest(route=route):
                self.assertEqual(self.client.post(reverse(route, args=[rule.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse('transactions:recurring_delete', args=[rule.pk])).status_code, 404)
        response = self.client.get(reverse('transactions:recurring_list'))
        self.assertNotContains(response, 'Rent')
        rule.refresh_from_db()
        self.assertEqual(rule.next_due_date, rule.start_date)

    def test_delete_confirmation_and_retained_history(self):
        rule = self.rule()
        self.client.get(reverse('transactions:recurring_list'))
        url = reverse('transactions:recurring_delete', args=[rule.pk])
        response = self.client.get(url)
        self.assertContains(response, 'Already-created entries stay in your history.')
        self.assertContains(response, 'method="post"')
        self.assertTrue(RecurringTransaction.objects.filter(pk=rule.pk).exists())
        self.client.post(url)
        self.assertFalse(RecurringTransaction.objects.exists())
        self.assertEqual(Transaction.objects.count(), 2)
        self.assertFalse(Transaction.objects.exclude(recurring_source=None).exists())

    def test_list_generation_history_badge_and_active_navigation(self):
        rule = self.rule()
        response = self.client.get(reverse('transactions:list'))
        self.assertContains(response, 'Created by a recurring transaction')
        self.assertEqual(rule.generated_transactions.count(), 2)
        for route, args in [('transactions:recurring_list', []), ('transactions:recurring_add', []), ('transactions:recurring_delete', [rule.pk])]:
            with self.subTest(route=route):
                response = self.client.get(reverse(route, args=args))
                self.assertContains(response, 'aria-current="page">Recurring</a>')
                self.assertContains(response, '<h1 class="h3')

    def test_recurring_list_generates_and_shows_ended_schedule(self):
        rule = self.rule(end_date=date(2026, 9, 30))
        response = self.client.get(reverse('transactions:recurring_list'))
        self.assertContains(response, 'Ended')
        self.assertContains(response, 'Paused')
        self.assertEqual(rule.generated_transactions.count(), 2)
        response = self.client.post(reverse('transactions:recurring_toggle', args=[rule.pk]), follow=True)
        self.assertContains(response, 'Recurring transaction has ended.')

    def test_empty_page_and_frequency_help(self):
        self.assertContains(self.client.get(reverse('transactions:recurring_list')), 'Add your first recurring transaction')
        self.assertContains(self.client.get(reverse('transactions:recurring_add')), 'Monthly entries on the 29th–31st move to the last day of shorter months.')

    def test_signed_out_requests_redirect(self):
        rule = self.rule()
        self.client.logout()
        for route, args in [('transactions:recurring_list', []), ('transactions:recurring_add', []), ('transactions:recurring_delete', [rule.pk]), ('transactions:recurring_toggle', [rule.pk])]:
            with self.subTest(route=route):
                url = reverse(route, args=args)
                self.assertRedirects(self.client.get(url), reverse('accounts:login') + '?next=' + url)

    def test_csrf_is_required_for_state_changes(self):
        rule = self.rule()
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        for route in ['transactions:recurring_toggle', 'transactions:recurring_delete']:
            with self.subTest(route=route):
                self.assertEqual(client.post(reverse(route, args=[rule.pk])).status_code, 403)
