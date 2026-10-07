# FT-03: Verify email identity and manager invariants.
from django.db import IntegrityError, transaction
from django.test import TestCase

from accounts.models import User


class UserModelTests(TestCase):
    def test_create_user_normalizes_email(self):
        user = User.objects.create_user("Mixed@EXAMPLE.COM", "sample-password", name="Mixed")
        self.assertEqual(user.email, "mixed@example.com")
        self.assertTrue(user.check_password("sample-password"))

    def test_save_normalizes_email(self):
        user = User.objects.create(email="Mixed@EXAMPLE.COM", name="Mixed")
        user.refresh_from_db()
        self.assertEqual(user.email, "mixed@example.com")
        user.email = "Changed@EXAMPLE.COM"
        user.save(update_fields=["email"])
        user.refresh_from_db()
        self.assertEqual(user.email, "changed@example.com")

    def test_case_variant_duplicate_is_rejected(self):
        User.objects.create_user("mixed@example.com", name="First")
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user("MIXED@EXAMPLE.COM", name="Second")

    def test_superuser_flags(self):
        user = User.objects.create_superuser("admin@example.com", "sample-password", name="Admin")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        for flag in ("is_staff", "is_superuser"):
            with self.subTest(flag=flag), self.assertRaises(ValueError):
                User.objects.create_superuser("other@example.com", name="Other", **{flag: False})

    def test_email_required_for_users_and_superusers(self):
        for create in (User.objects.create_user, User.objects.create_superuser):
            with self.assertRaises(ValueError):
                create("", name="Missing")

    def test_natural_key_is_case_insensitive(self):
        user = User.objects.create_user("mixed@example.com", name="Mixed")
        self.assertEqual(User.objects.get_by_natural_key("MIXED@EXAMPLE.COM"), user)
