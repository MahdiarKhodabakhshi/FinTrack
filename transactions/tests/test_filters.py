# FT-52: Search, filter, sort, ownership and rendered state contracts.
from datetime import date, datetime, timezone as dt_timezone

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from transactions.filters import TransactionFilterForm, apply_transaction_filters, filters_active
from transactions.models import Transaction


class FilterTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('filters@example.com', name='Filters')
        other = User.objects.create_user('other@example.com', name='Other')
        self.client.force_login(self.user)
        self.a = self.record(date(2026, 1, 1), '10', 'income', 'Paycheque')
        self.b = self.record(date(2026, 1, 3), '30', 'expense', 'GROCERIES market')
        self.c = self.record(date(2026, 1, 3), '10', 'expense', 'Groceries corner')
        self.d = self.record(date(2026, 1, 3), '10', 'income', 'Refund')
        Transaction.objects.create(user=other, date=date(2026, 1, 3), amount='10', transaction_type='expense', description='Groceries private')
        Transaction.objects.filter(user=self.user).update(created_at=datetime(2026, 1, 4, tzinfo=dt_timezone.utc))

    def record(self, day, amount, kind, description):
        return Transaction.objects.create(user=self.user, date=day, amount=amount, transaction_type=kind, description=description)

    def response(self, **params):
        response = self.client.get(reverse('transactions:list'), params)
        self.assertEqual(response.status_code, 200)
        return response

    def ids(self, **params):
        return list(self.response(**params).context['transactions'].values_list('pk', flat=True))

    def test_keyword_is_partial_case_insensitive_and_stripped(self):
        self.assertEqual(self.ids(q='  gRoCeR  '), [self.c.pk, self.b.pk])

    def test_type_filter(self):
        self.assertEqual(self.ids(type='income'), [self.d.pk, self.a.pk])

    def test_date_range_is_inclusive(self):
        self.assertEqual(self.ids(date_from='2026-01-01', date_to='2026-01-03'), [self.d.pk, self.c.pk, self.b.pk, self.a.pk])
        self.assertEqual(self.ids(date_from='2026-01-03', date_to='2026-01-03'), [self.d.pk, self.c.pk, self.b.pk])

    def test_reversed_range_drops_both_dates_and_keeps_other_filters(self):
        response = self.response(q='groc', date_from='2026-02-01', date_to='2026-01-01')
        self.assertContains(response, 'The start date must be on or before the end date.')
        self.assertEqual(list(response.context['transactions']), [self.c, self.b])
        self.assertTrue(response.context['filters_active'])

    def test_invalid_fields_do_not_discard_successful_fields(self):
        self.assertEqual(self.ids(type='expense', date_from='invalid', date_to='2026-01-03', sort='-user'), [self.c.pk, self.b.pk])
        response = self.response(q='x' * 101, type='income')
        self.assertTrue(response.context['filter_form'].errors)
        self.assertEqual(list(response.context['transactions']), [self.d, self.a])

    def test_whitelisted_sort_orders_and_pk_ties(self):
        expected = {'newest': [self.d, self.c, self.b, self.a], 'oldest': [self.a, self.b, self.c, self.d],
                    'amount_high': [self.b, self.d, self.c, self.a], 'amount_low': [self.d, self.c, self.a, self.b]}
        for key, rows in expected.items():
            with self.subTest(sort=key):
                self.assertEqual(self.ids(sort=key), [row.pk for row in rows])

    def test_created_at_tie_breaks_date_sorts(self):
        Transaction.objects.filter(pk=self.b.pk).update(created_at=datetime(2026, 1, 5, tzinfo=dt_timezone.utc))
        self.assertEqual(self.ids(sort='newest'), [self.b.pk, self.d.pk, self.c.pk, self.a.pk])
        self.assertEqual(self.ids(sort='oldest'), [self.a.pk, self.c.pk, self.d.pk, self.b.pk])

    def test_unknown_sort_falls_back_to_newest(self):
        self.assertEqual(self.ids(sort='user__email'), self.ids(sort='newest'))

    def test_user_scope_is_always_preserved(self):
        response = self.response(q='groceries', type='expense', date_from='2026-01-03', sort='amount_low')
        self.assertNotContains(response, 'Groceries private')
        self.assertTrue(all(row.user_id == self.user.pk for row in response.context['transactions']))

    def test_three_ui_states(self):
        self.assertContains(self.response(), '<table')
        response = self.response(q='no-match')
        self.assertContains(response, 'No transactions match your filters')
        self.assertContains(response, 'Filter transactions')
        self.assertNotContains(response, 'No transactions yet')
        Transaction.objects.filter(user=self.user).delete()
        response = self.response()
        self.assertContains(response, 'No transactions yet')
        self.assertNotContains(response, 'Filter transactions')
        self.assertNotContains(response, 'Export CSV')

    def test_result_count_pluralization(self):
        self.assertContains(self.response(q='paycheque'), 'Showing 1 transaction matching your filters')
        self.assertContains(self.response(q='groc'), 'Showing 2 transactions matching your filters')
        self.assertContains(self.response(q='none'), 'Showing 0 transactions matching your filters')

    def test_values_and_export_query_are_preserved(self):
        response = self.response(q='market', type='expense', date_from='2026-01-01', date_to='', sort='oldest')
        self.assertContains(response, 'value="market"')
        self.assertContains(response, 'value="expense" selected')
        self.assertContains(response, 'value="2026-01-01"')
        self.assertContains(response, 'value="oldest" selected')
        self.assertNotIn('date_to=', response.context['export_query'])

    def test_sort_alone_is_not_a_filter(self):
        self.assertFalse(self.response(sort='oldest').context['filters_active'])
        form = TransactionFilterForm()
        self.assertFalse(filters_active(form))
        self.assertEqual(list(apply_transaction_filters(Transaction.objects.filter(user=self.user), form)), [self.d, self.c, self.b, self.a])
