# FT-72: Private filtered CSV downloads with spreadsheet-safe descriptions.
import csv
from datetime import date
from io import StringIO
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from transactions.models import Transaction


class ExportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('export@example.com', name='Export')
        other = User.objects.create_user('other@example.com', name='Other')
        self.income = Transaction.objects.create(user=self.user, date=date(2026, 1, 1), transaction_type='income', amount='1234.50', description='Salary')
        self.expense = Transaction.objects.create(user=self.user, date=date(2026, 2, 1), transaction_type='expense', amount='20.00', description='=SUM(A1)')
        Transaction.objects.create(user=other, date=date(2026, 2, 1), transaction_type='income', amount='50', description='Private')
        self.client.force_login(self.user)

    def export(self, **params):
        return self.client.get(reverse('transactions:export'), params)

    def rows(self, response):
        return list(csv.reader(StringIO(response.content.decode('utf-8-sig'))))

    @patch('transactions.views.timezone.localdate', return_value=date(2026, 10, 8))
    def test_headers_bom_and_filename(self, mocked_today):
        response = self.export()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        self.assertEqual(response['Content-Disposition'], 'attachment; filename="fintrack-transactions-2026-10-08.csv"')
        self.assertEqual(response['Cache-Control'], 'no-store')
        self.assertTrue(response.content.startswith(b'\xef\xbb\xbf'))
        self.assertEqual(self.rows(response)[0], ['Date', 'Type', 'Description', 'Amount'])

    def test_signed_plain_amounts_and_owner(self):
        rows = self.rows(self.export())
        self.assertEqual(rows[1], ['2026-02-01', 'Expense', "'=SUM(A1)", '-20.00'])
        self.assertEqual(rows[2], ['2026-01-01', 'Income', 'Salary', '1234.50'])
        self.assertEqual(len(rows), 3)

    def test_all_filters_and_sort_match_history(self):
        params = {'q': 'sum', 'type': 'expense', 'date_from': '2026-02-01', 'date_to': '2026-02-01', 'sort': 'oldest'}
        rows = self.rows(self.export(**params))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][3], '-20.00')
        self.assertEqual(self.rows(self.export(sort='amount_high'))[1][2], 'Salary')
        for sort in ['newest', 'oldest', 'amount_high', 'amount_low', 'invalid']:
            with self.subTest(sort=sort):
                expected = list(self.client.get(reverse('transactions:list'), {'sort': sort}).context['transactions'])
                self.assertEqual([row[3] for row in self.rows(self.export(sort=sort))[1:]], [f'{record.signed_amount:.2f}' for record in expected])

    def test_formula_prefixes_and_csv_quoting(self):
        for prefix in ('=', '+', '-', '@', '\t', '\r'):
            self.expense.description = prefix + 'formula,"quoted"\nnext line'
            self.expense.save()
            with self.subTest(prefix=prefix):
                self.assertEqual(self.rows(self.export(type='expense'))[1][2], "'" + self.expense.description)

    def test_invalid_range_is_consistent_with_list(self):
        self.assertEqual(len(self.rows(self.export(date_from='2026-03-01', date_to='2026-01-01'))), 3)

    def test_no_matches_still_exports_header(self):
        self.assertEqual(self.rows(self.export(q='absent')), [['Date', 'Type', 'Description', 'Amount']])

    def test_signed_out_redirect_and_post_rejection(self):
        self.assertEqual(self.client.post(reverse('transactions:export')).status_code, 405)
        self.client.logout()
        self.assertRedirects(self.export(), reverse('accounts:login') + '?next=/transactions/export/')
