# FT-75, FT-76: Idempotent catch-up, pause/resume, end boundaries and DB constraints.
from datetime import date, timedelta
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase

from accounts.models import User
from transactions.models import RecurringTransaction, Transaction
from transactions.recurring import MAX_CATCH_UP, generate_due_transactions, resume_rule


class GenerationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('recurring@example.com', name='Recurring')
        self.other = User.objects.create_user('other@example.com', name='Other')

    def rule(self, **overrides):
        data = {'user': self.user, 'transaction_type': 'expense', 'amount': Decimal('20.00'),
                'description': 'Weekly supplies', 'frequency': 'weekly',
                'start_date': date(2026, 1, 1), 'next_due_date': date(2026, 1, 1)}
        data.update(overrides)
        return RecurringTransaction.objects.create(**data)

    def test_catchup_and_second_run_are_idempotent(self):
        rule = self.rule()
        today = date(2026, 1, 22)
        self.assertEqual(generate_due_transactions(today=today), 4)
        self.assertEqual(generate_due_transactions(today=today), 0)
        self.assertEqual(list(rule.generated_transactions.order_by('date').values_list('date', flat=True)), [date(2026, 1, n) for n in [1, 8, 15, 22]])
        rule.refresh_from_db()
        self.assertEqual(rule.next_due_date, date(2026, 1, 29))

    def test_existing_occurrence_does_not_duplicate(self):
        rule = self.rule()
        Transaction.objects.create(user=self.user, recurring_source=rule, date=rule.start_date, transaction_type='expense', amount='20', description=rule.description)
        self.assertEqual(generate_due_transactions(today=rule.start_date), 0)
        self.assertEqual(rule.generated_transactions.count(), 1)

    def test_end_date_is_inclusive_and_deactivates(self):
        rule = self.rule(end_date=date(2026, 1, 15))
        self.assertEqual(generate_due_transactions(today=date(2026, 1, 22)), 3)
        rule.refresh_from_db()
        self.assertFalse(rule.is_active)
        self.assertTrue(rule.is_ended)
        self.assertTrue(rule.generated_transactions.filter(date=rule.end_date).exists())

    def test_paused_rule_creates_nothing(self):
        self.rule(is_active=False)
        self.assertEqual(generate_due_transactions(today=date(2026, 2, 1)), 0)

    def test_resume_skips_paused_period_but_includes_today(self):
        rule = self.rule(is_active=False, next_due_date=date(2026, 1, 8))
        resume_rule(rule, today=date(2026, 1, 22))
        self.assertEqual(rule.next_due_date, date(2026, 1, 22))
        self.assertTrue(rule.is_active)
        self.assertEqual(generate_due_transactions(today=date(2026, 1, 22)), 1)
        self.assertEqual(rule.generated_transactions.get().date, date(2026, 1, 22))

    def test_resume_before_next_date_preserves_schedule_and_expired_rule_stays_ended(self):
        rule = self.rule(is_active=False, next_due_date=date(2026, 1, 8))
        resume_rule(rule, today=date(2026, 1, 5))
        self.assertEqual(rule.next_due_date, date(2026, 1, 8))
        rule.is_active = False
        rule.end_date = date(2026, 1, 8)
        rule.save()
        resume_rule(rule, today=date(2026, 2, 1))
        self.assertFalse(rule.is_active)
        self.assertTrue(rule.is_ended)

    def test_max_catchup_counts_occurrences_and_continues_next_run(self):
        start = date(2010, 1, 1)
        rule = self.rule(start_date=start, next_due_date=start)
        today = start + timedelta(days=7 * (MAX_CATCH_UP + 1))
        self.assertEqual(generate_due_transactions(today=today), MAX_CATCH_UP)
        rule.refresh_from_db()
        self.assertEqual(rule.next_due_date, start + timedelta(days=7 * MAX_CATCH_UP))
        self.assertEqual(generate_due_transactions(today=today), 2)

    def test_generated_fields_and_user_scoping(self):
        rule = self.rule(transaction_type='income', amount=Decimal('1234.50'), description='Paycheque')
        other = self.rule(user=self.other)
        self.assertEqual(generate_due_transactions(user=self.user, today=rule.start_date), 1)
        record = rule.generated_transactions.get()
        for field in ['user', 'transaction_type', 'amount', 'description']:
            self.assertEqual(getattr(record, field), getattr(rule, field))
        other.refresh_from_db()
        self.assertEqual(other.next_due_date, other.start_date)
        self.assertFalse(other.generated_transactions.exists())

    @patch('transactions.recurring.timezone.localdate', return_value=date(2026, 1, 1))
    def test_command_reports_all_user_count_and_repeated_run(self, mocked_today):
        self.rule()
        self.rule(user=self.other)
        output = StringIO()
        call_command('generate_recurring_transactions', stdout=output)
        self.assertIn('Created 2 recurring transactions.', output.getvalue())
        output = StringIO()
        call_command('generate_recurring_transactions', stdout=output)
        self.assertIn('Created 0 recurring transactions.', output.getvalue())

    def test_deleting_rule_keeps_generated_history(self):
        rule = self.rule()
        generate_due_transactions(today=rule.start_date)
        record = rule.generated_transactions.get()
        rule.delete()
        record.refresh_from_db()
        self.assertIsNone(record.recurring_source)
        self.assertEqual(record.user, self.user)

    def test_database_constraints_and_rule_summary(self):
        for overrides in [{'amount': '0'}, {'amount': '-1'}, {'end_date': date(2025, 12, 31)}]:
            with self.subTest(overrides=overrides), self.assertRaises(IntegrityError), transaction.atomic():
                self.rule(**overrides)
        rule = self.rule()
        self.assertIn('Weekly supplies', str(rule))
        generate_due_transactions(today=rule.start_date)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Transaction.objects.create(user=self.user, recurring_source=rule, date=rule.start_date, transaction_type='expense', amount='20')
        self.assertEqual(rule.signed_amount, Decimal('-20.00'))
