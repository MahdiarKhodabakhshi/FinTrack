# FT-75: The recurring section stays active across all its pages.
from types import SimpleNamespace

from django.test import SimpleTestCase

from ui.templatetags.ui import nav_active_prefix


class RecurringNavigationTests(SimpleTestCase):
    def test_recurring_prefix_matching(self):
        for name in ['transactions:recurring_list', 'transactions:recurring_add', 'transactions:recurring_toggle', 'transactions:recurring_delete']:
            self.assertEqual(nav_active_prefix(SimpleNamespace(resolver_match=SimpleNamespace(view_name=name)), 'transactions:recurring_'), 'active')
        self.assertEqual(nav_active_prefix(SimpleNamespace(resolver_match=SimpleNamespace(view_name='transactions:list')), 'transactions:recurring_'), '')
        self.assertEqual(nav_active_prefix(SimpleNamespace(resolver_match=None), 'transactions:recurring_'), '')
