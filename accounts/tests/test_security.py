# FT-07, FT-11, FT-13, FT-14: Password and session security invariants.
from django.contrib.auth import SESSION_KEY
from django.test import TestCase
from django.urls import reverse

from accounts.models import User


class AuthenticationSecurityTests(TestCase):
    def setUp(self):
        self.password = "Unique-demo-passphrase-42!"
        self.user = User.objects.create_user("member@example.com", self.password, name="Member")

    def sign_in(self):
        return self.client.post(reverse("accounts:login"), {
            "username": "MEMBER@EXAMPLE.COM", "password": self.password,
        })

    def test_password_is_argon2_and_not_raw(self):
        self.assertTrue(self.user.password.startswith("argon2$"))
        self.assertNotEqual(self.user.password, self.password)
        self.assertTrue(self.user.check_password(self.password))

    def test_protected_page_redirects_with_next(self):
        self.assertRedirects(self.client.get(reverse("transactions:list")),
                             reverse("accounts:login") + "?next=/transactions/")

    def test_public_authentication_pages(self):
        for route in ("accounts:login", "accounts:register", "admin:login"):
            with self.subTest(route=route):
                self.assertEqual(self.client.get(reverse(route)).status_code, 200)

    def test_get_logout_does_not_end_session(self):
        self.sign_in()
        self.assertEqual(self.client.get(reverse("accounts:logout")).status_code, 405)
        self.assertEqual(self.client.session[SESSION_KEY], str(self.user.pk))
        self.assertEqual(self.client.get(reverse("transactions:list")).status_code, 200)

    def test_post_logout_ends_session(self):
        self.sign_in()
        self.assertRedirects(self.client.post(reverse("accounts:logout")), reverse("accounts:login"))
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertRedirects(self.client.get(reverse("transactions:list")),
                             reverse("accounts:login") + "?next=/transactions/")

    def test_login_rotates_existing_session_key(self):
        session = self.client.session
        session["anonymous_marker"] = "preserved"
        session.save()
        previous_key = session.session_key
        self.assertRedirects(self.sign_in(), reverse("transactions:list"))
        self.assertNotEqual(self.client.session.session_key, previous_key)
        self.assertEqual(self.client.session["anonymous_marker"], "preserved")
        self.assertEqual(self.client.session[SESSION_KEY], str(self.user.pk))
