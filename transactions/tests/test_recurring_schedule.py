# FT-76: Calendar schedules retain the original monthly anchor.
from datetime import date

from django.test import SimpleTestCase

from transactions.models import RecurringTransaction
from transactions.recurring import next_occurrence


class ScheduleTests(SimpleTestCase):
    def test_weekly_and_biweekly(self):
        for frequency, expected in [('weekly', date(2026, 1, 8)), ('biweekly', date(2026, 1, 15))]:
            with self.subTest(frequency=frequency):
                rule = RecurringTransaction(start_date=date(2026, 1, 1), frequency=frequency)
                self.assertEqual(next_occurrence(rule, rule.start_date), expected)

    def test_january_31_leap_and_nonleap(self):
        for year, february in [(2027, 28), (2028, 29)]:
            with self.subTest(year=year):
                rule = RecurringTransaction(start_date=date(year, 1, 31), frequency='monthly')
                current = rule.start_date
                for expected in [date(year, 2, february), date(year, 3, 31), date(year, 4, 30)]:
                    current = next_occurrence(rule, current)
                    self.assertEqual(current, expected)

    def test_august_anchor_does_not_drift(self):
        rule = RecurringTransaction(start_date=date(2026, 8, 31), frequency='monthly')
        september = next_occurrence(rule, rule.start_date)
        self.assertEqual(september, date(2026, 9, 30))
        self.assertEqual(next_occurrence(rule, september), date(2026, 10, 31))

    def test_middle_of_month_stays_on_fifteenth_and_crosses_year(self):
        rule = RecurringTransaction(start_date=date(2026, 12, 15), frequency='monthly')
        self.assertEqual(next_occurrence(rule, rule.start_date), date(2027, 1, 15))
        self.assertEqual(next_occurrence(rule, date(2027, 1, 15)), date(2027, 2, 15))

    def test_invalid_frequency_is_rejected(self):
        rule = RecurringTransaction(start_date=date(2026, 1, 1), frequency='unknown')
        with self.assertRaises(ValueError):
            next_occurrence(rule, rule.start_date)
