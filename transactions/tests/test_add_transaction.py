# FT-17, FT-19: Required fields, valid money/dates, ownership and saved values.
from datetime import date
from decimal import Decimal

from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import User
from transactions.models import Transaction


class AddTransactionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('adding@example.com', name='Adding')
        self.other = User.objects.create_user('other@example.com', name='Other')
        self.client.force_login(self.user)

    def data(self, **overrides):
        values = {'transaction_type': 'expense', 'amount': '12.34', 'date': '2026-10-08', 'description': 'Groceries'}
        values.update(overrides)
        return values

    def submit(self, **overrides):
        return self.client.post(reverse('transactions:add'), self.data(**overrides))

    def test_add_page_shows_only_user_editable_fields(self):
        response = self.client.get(reverse('transactions:add'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'transactions/transaction_form.html')
        self.assertEqual(list(response.context['form'].fields), ['transaction_type', 'amount', 'date', 'description'])
        self.assertNotContains(response, 'name="user"')

    def test_income_and_expense_save_all_values_and_success_message(self):
        for kind in ('income', 'expense'):
            with self.subTest(kind=kind):
                response = self.submit(transaction_type=kind, description=f'{kind} saved')
                self.assertRedirects(response, reverse('transactions:list'))
                record = Transaction.objects.get(description=f'{kind} saved')
                self.assertEqual(record.user, self.user)
                self.assertEqual(record.transaction_type, kind)
                self.assertEqual(record.amount, Decimal('12.34'))
                self.assertEqual(record.date, date(2026, 10, 8))
                self.assertContains(self.client.get(response.url), 'Transaction added.')

    def test_required_fields_have_errors_and_nothing_is_saved(self):
        for field in ('transaction_type', 'amount', 'date'):
            with self.subTest(field=field):
                response = self.submit(**{field: ''})
                self.assertEqual(response.status_code, 200)
                self.assertIn(field, response.context['form'].errors)
                self.assertContains(response, f'id="id_{field}_error"')
        self.assertFalse(Transaction.objects.exists())

    def test_amount_validation_rejects_nonpositive_invalid_and_out_of_range(self):
        for amount in ('0', '-0.01', 'invalid', 'NaN', 'Infinity', '0.001', '10000000000.00'):
            with self.subTest(amount=amount):
                response = self.submit(amount=amount)
                self.assertEqual(response.status_code, 200)
                self.assertIn('amount', response.context['form'].errors)
        self.assertFalse(Transaction.objects.exists())

    def test_minimum_and_maximum_supported_amounts_are_saved(self):
        for amount in ('0.01', '9999999999.99'):
            with self.subTest(amount=amount):
                self.assertRedirects(self.submit(amount=amount), reverse('transactions:list'))
                self.assertTrue(Transaction.objects.filter(user=self.user, amount=Decimal(amount)).exists())

    def test_invalid_calendar_dates_are_rejected(self):
        for day in ('not-a-date', '2026-02-30', '2027-02-29'):
            with self.subTest(day=day):
                response = self.submit(date=day)
                self.assertEqual(response.status_code, 200)
                self.assertIn('date', response.context['form'].errors)
        self.assertFalse(Transaction.objects.exists())

    def test_leap_day_and_future_date_are_valid(self):
        for day in ('2028-02-29', '2030-01-01'):
            with self.subTest(day=day):
                self.assertRedirects(self.submit(date=day), reverse('transactions:list'))
                self.assertTrue(Transaction.objects.filter(user=self.user, date=day).exists())

    def test_unknown_type_is_rejected(self):
        response = self.submit(transaction_type='transfer')
        self.assertIn('transaction_type', response.context['form'].errors)
        self.assertFalse(Transaction.objects.exists())

    def test_description_is_optional_but_length_is_limited(self):
        self.assertRedirects(self.submit(description=''), reverse('transactions:list'))
        self.assertEqual(Transaction.objects.get().description, '')
        response = self.submit(description='x' * 256)
        self.assertIn('description', response.context['form'].errors)
        self.assertEqual(Transaction.objects.count(), 1)

    def test_forged_owner_is_ignored(self):
        self.assertRedirects(self.submit(user=self.other.pk), reverse('transactions:list'))
        self.assertEqual(Transaction.objects.get().user, self.user)

    def test_signed_out_cannot_add_a_transaction(self):
        self.client.logout()
        self.assertRedirects(self.submit(), reverse('accounts:login') + '?next=/transactions/add/')
        self.assertFalse(Transaction.objects.exists())

    def test_saving_requires_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        client.get(reverse('transactions:add'))
        self.assertEqual(client.post(reverse('transactions:add'), self.data()).status_code, 403)
        self.assertFalse(Transaction.objects.exists())
        values = self.data(csrfmiddlewaretoken=client.cookies['csrftoken'].value)
        self.assertRedirects(client.post(reverse('transactions:add'), values), reverse('transactions:list'))
