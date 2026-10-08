# FT-04, FT-20: Verify reusable presentation helpers and Django accessibility.
from decimal import Decimal
from types import SimpleNamespace

from django import forms
from django.template import Context, Template
from django.test import SimpleTestCase
from django.utils import translation

from ui.templatetags.ui import field_widget, money, nav_active


class ExampleForm(forms.Form):
    name = forms.CharField(help_text="Enter your name.", widget=forms.TextInput(attrs={"class": "existing", "autofocus": True}))
    choice = forms.ChoiceField(choices=[("income", "Income"), ("expense", "Expense")])


class MoneyTests(SimpleTestCase):
    def test_money_cases(self):
        cases = [
            (Decimal("1234.5"), "", "$1,234.50"),
            (Decimal("1234.5"), "signed", "+$1,234.50"),
            (Decimal("-20"), "signed", "−$20.00"),
            (None, "", ""),
            (Decimal("0.005"), "", "$0.01"),
            (Decimal("0"), "signed", "$0.00"),
            (Decimal("-0.005"), "signed", "−$0.01"),
        ]
        with translation.override("en-ca"):
            for value, mode, expected in cases:
                with self.subTest(value=value, mode=mode):
                    self.assertEqual(money(value, mode), expected)


class FieldWidgetTests(SimpleTestCase):
    def test_input_classes_preserve_original_widget(self):
        form = ExampleForm()
        html = field_widget(form["name"])
        self.assertIn('class="existing form-control"', html)
        self.assertEqual(form.fields["name"].widget.attrs["class"], "existing")
        self.assertIn('class="form-select"', field_widget(form["choice"]))

    def test_choice_controls_use_check_class(self):
        for widget in (forms.CheckboxInput(), forms.CheckboxSelectMultiple(), forms.RadioSelect()):
            with self.subTest(widget=type(widget).__name__):
                form = forms.Form()
                form.fields["control"] = forms.CharField(widget=widget)
                self.assertIn('class="form-check-input"', field_widget(form["control"]))

    def test_invalid_widget_retains_accessibility_references(self):
        form = ExampleForm(data={"name": "", "choice": "income"})
        self.assertFalse(form.is_valid())
        html = field_widget(form["name"])
        self.assertIn("is-invalid", html)
        self.assertIn('aria-invalid="true"', html)
        self.assertIn('aria-describedby="id_name_helptext id_name_error"', html)

    def test_autofocus_can_be_removed(self):
        form = ExampleForm()
        self.assertNotIn("autofocus", field_widget(form["name"], autofocus=False))
        self.assertTrue(form.fields["name"].widget.attrs["autofocus"])

    def test_attributes_are_merged_and_escaped(self):
        html = field_widget(ExampleForm()["name"], aria_label='Your "name"', data_testid="name", autocomplete="name", placeholder="Name")
        self.assertIn('aria-label="Your &quot;name&quot;"', html)
        self.assertIn('data-testid="name"', html)
        self.assertIn('autocomplete="name"', html)
        self.assertIn('placeholder="Name"', html)

    def test_tag_accepts_template_keyword_arguments(self):
        html = Template('{% load ui %}{% field_widget field autofocus=False aria_label="Name" %}').render(Context({"field": ExampleForm()["name"]}))
        self.assertNotIn("autofocus", html)
        self.assertIn('aria-label="Name"', html)


class NavActiveTests(SimpleTestCase):
    def test_only_matching_route_is_active(self):
        request = SimpleNamespace(resolver_match=SimpleNamespace(view_name="transactions:list"))
        self.assertEqual(nav_active(request, "transactions:list"), "active")
        self.assertEqual(nav_active(request, "transactions:add"), "")
        self.assertEqual(nav_active(SimpleNamespace(resolver_match=None), "transactions:list"), "")
        self.assertEqual(nav_active(SimpleNamespace(), "transactions:list"), "")
