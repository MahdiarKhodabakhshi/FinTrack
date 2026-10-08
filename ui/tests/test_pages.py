# FT-04, FT-05, FT-10, FT-12, FT-16, FT-20, FT-22: Test rendered UI contracts.
from datetime import date
from decimal import Decimal
from html.parser import HTMLParser
import re

from django.contrib.messages import constants as message_levels
from django.contrib.messages.storage.base import Message
from django.template.loader import render_to_string
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from transactions.models import Transaction


class Elements(HTMLParser):
    """FT-04: Read HTML attributes using the standard library, without dependencies."""
    def __init__(self, html):
        super().__init__()
        self.elements = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))

    def matching(self, tag, **attrs):
        return [attributes for name, attributes in self.elements
                if name == tag and all(attributes.get(key) == value for key, value in attrs.items())]


class PageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("member@example.com", "Unique-ui-passphrase-42!", name="Member")

    def document(self, response):
        self.assertEqual(response.status_code, 200)
        return Elements(response.content.decode())

    def test_public_pages_share_layout_and_signed_out_navigation(self):
        for route in ("accounts:login", "accounts:register"):
            with self.subTest(route=route):
                response = self.client.get(reverse(route))
                doc = self.document(response)
                self.assertTemplateUsed(response, "base.html")
                self.assertEqual(len(doc.matching("h1")), 1)
                self.assertTrue(doc.matching("link", href="/static/vendor/bootstrap-5.3.8/css/bootstrap.min.css"))
                self.assertTrue(doc.matching("link", href="/static/css/fintrack.css"))
                nav = re.search(r"<nav\b.*?</nav>", response.content.decode(), re.S).group()
                self.assertIn("Log in", nav)
                self.assertIn("Register", nav)
                self.assertNotIn("Log out", nav)
                focusable = next((tag, attrs) for tag, attrs in doc.elements if tag in ("a", "input", "button", "select"))
                self.assertEqual(focusable, ("a", {"class": "visually-hidden-focusable ft-skip-link", "href": "#main"}))

    def test_signed_in_navigation_has_post_logout_and_active_history(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("transactions:list"))
        doc = self.document(response)
        self.assertTrue(doc.matching("a", href=reverse("transactions:list"), **{"aria-current": "page"}))
        logout = re.search(r'<form\b[^>]*action="' + re.escape(reverse("accounts:logout")) + r'"[^>]*>.*?</form>', response.content.decode(), re.S).group()
        self.assertIn('method="post"', logout)
        self.assertIn('name="csrfmiddlewaretoken"', logout)
        self.assertIn("Log out", logout)

    def test_bad_login_alert_keeps_email_and_clears_password(self):
        response = self.client.post(reverse("accounts:login"), {"username": self.user.email, "password": "incorrect"})
        doc = self.document(response)
        self.assertRegex(response.content.decode(), r'(?s)role="alert">\s*<p class="mb-0">Please enter a correct email and password')
        self.assertEqual(doc.matching("input", name="username")[0]["value"], self.user.email)
        self.assertNotIn("value", doc.matching("input", name="password")[0])
        self.assertContains(response, "Note that both fields may be case-sensitive.")

    def test_bad_registration_connects_widget_to_errors(self):
        response = self.client.post(reverse("accounts:register"), {
            "name": "New Member", "email": "new@example.com", "password1": "Unique-ui-passphrase-42!", "password2": "different-passphrase-42!",
        })
        doc = self.document(response)
        password = doc.matching("input", name="password2")[0]
        self.assertIn("is-invalid", password["class"])
        self.assertEqual(password["aria-invalid"], "true")
        self.assertIn("id_password2_error", password["aria-describedby"].split())
        self.assertTrue(doc.matching("div", id="id_password2_error"))

    def test_registration_autofocus_and_safe_password_help(self):
        response = self.client.get(reverse("accounts:register"))
        doc = self.document(response)
        focused = [attrs["name"] for tag, attrs in doc.elements if tag == "input" and "autofocus" in attrs]
        self.assertEqual(focused, ["name"])
        self.assertTrue(doc.matching("div", id="id_password1_helptext"))
        self.assertIn("id_password1_helptext", doc.matching("input", name="password1")[0]["aria-describedby"])
        self.assertContains(response, "<ul>")
        self.assertNotContains(response, "&lt;ul&gt;")

    def test_login_preserves_next_only_when_present(self):
        response = self.client.get(reverse("accounts:login"), {"next": reverse("transactions:add")})
        doc = self.document(response)
        self.assertTrue(doc.matching("input", type="hidden", name="next", value=reverse("transactions:add")))
        response = self.client.get(reverse("accounts:login"))
        self.assertFalse(self.document(response).matching("input", name="next"))

    def test_add_page_prefix_optional_description_and_active_navigation(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("transactions:add"))
        doc = self.document(response)
        self.assertContains(response, '<span class="input-group-text">$</span>', html=True)
        self.assertRegex(response.content.decode(), r'(?s)<label[^>]*for="id_description"[^>]*>Description.*?\(optional\).*?</label>')
        self.assertTrue(doc.matching("select", name="transaction_type", **{"class": "form-select"}))
        self.assertTrue(doc.matching("input", name="amount", inputmode="decimal", placeholder="0.00"))
        self.assertTrue(doc.matching("input", name="date", type="date"))
        self.assertTrue(doc.matching("a", href=reverse("transactions:add"), **{"aria-current": "page"}))
        self.assertTrue(doc.matching("form", method="post"))
        self.assertContains(response, "---------")

    def test_add_errors_retain_django_aria_references(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("transactions:add"), {"transaction_type": "expense", "amount": "0", "date": "invalid", "description": ""})
        doc = self.document(response)
        for name in ("amount", "date"):
            widget = doc.matching("input", name=name)[0]
            self.assertEqual(widget["aria-invalid"], "true")
            self.assertTrue(doc.matching("div", id=f"id_{name}_error"))

    def test_empty_history_has_call_to_action_and_no_table(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("transactions:list"))
        self.assertContains(response, "No transactions yet")
        self.assertContains(response, "Add your first transaction")
        self.assertTrue(self.document(response).matching("a", href=reverse("transactions:add")))
        self.assertNotContains(response, "<table")

    def test_populated_history_formats_money_and_keeps_ordering(self):
        Transaction.objects.create(user=self.user, transaction_type="income", amount=Decimal("1234.50"), date=date(2026, 10, 1), description="Older paycheque")
        Transaction.objects.create(user=self.user, transaction_type="expense", amount=Decimal("20.00"), date=date(2026, 10, 7), description="Newer groceries")
        self.client.force_login(self.user)
        response = self.client.get(reverse("transactions:list"))
        doc = self.document(response)
        for text in ("+$1,234.50", "−$20.00", "Income", "Expense"):
            self.assertContains(response, text)
        self.assertTrue(doc.matching("time", datetime="2026-10-07"))
        self.assertContains(response, 'scope="col"', count=4)
        html = response.content.decode()
        self.assertLess(html.index("Newer groceries"), html.index("Older paycheque"))

    def test_registration_success_message_appears_on_history(self):
        response = self.client.post(reverse("accounts:register"), {
            "name": "New Member", "email": "new@example.com", "password1": "Unique-ui-passphrase-42!", "password2": "Unique-ui-passphrase-42!",
        }, follow=True)
        self.assertContains(response, "Your account has been created.")
        self.assertContains(response, "alert-success")
        self.assertTrue(self.document(response).matching("div", role="status"))

    def test_message_severity_mapping_and_extra_tags(self):
        for level, style, role in ((message_levels.DEBUG, "secondary", "status"), (message_levels.INFO, "info", "status"), (message_levels.SUCCESS, "success", "status"), (message_levels.WARNING, "warning", "alert"), (message_levels.ERROR, "danger", "alert")):
            with self.subTest(level=level):
                html = render_to_string("base.html", {"user": self.user, "messages": [Message(level, "Notice", extra_tags="custom")]})
                self.assertIn(f"alert-{style}", html)
                self.assertIn(f'role="{role}"', html)
                self.assertIn('aria-label="Close"', html)

    def test_multiple_nonfield_errors_use_one_alert(self):
        from django import forms
        form = forms.Form(data={})
        form.add_error(None, ["First problem", "Second problem"])
        html = render_to_string("includes/form_errors.html", {"form": form})
        doc = Elements(html)
        self.assertEqual(len(doc.matching("div", role="alert")), 1)
        self.assertIn('<ul class="mb-0">', html)
        self.assertIn("First problem", html)
        self.assertIn("Second problem", html)
