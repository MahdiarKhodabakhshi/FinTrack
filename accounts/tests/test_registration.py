# FT-06, FT-08, FT-09: Registration validation, safe storage, duplicates and sessions.
from unittest.mock import patch

from django.contrib.auth import SESSION_KEY
from django.db import IntegrityError
from django.test import Client, TestCase
from django.urls import reverse

from accounts.forms import RegistrationForm
from accounts.models import User


class RegistrationTests(TestCase):
    password = 'Distinct-registration-passphrase-42!'

    def data(self, **overrides):
        values = {'name': 'New Member', 'email': 'new@example.com', 'password1': self.password, 'password2': self.password}
        values.update(overrides)
        return values

    def submit(self, **overrides):
        return self.client.post(reverse('accounts:register'), self.data(**overrides))

    def test_valid_registration_creates_user_logs_in_and_shows_success(self):
        response = self.submit(email='  NEW@EXAMPLE.COM  ', name='  New Member  ', is_staff='true', is_superuser='true')
        self.assertRedirects(response, reverse('transactions:list'), fetch_redirect_response=False)
        user = User.objects.get()
        self.assertEqual(user.email, 'new@example.com')
        self.assertEqual(user.name, 'New Member')
        self.assertTrue(user.check_password(self.password))
        self.assertTrue(user.password.startswith('argon2$'))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(self.client.session[SESSION_KEY], str(user.pk))
        self.assertContains(self.client.get(response.url), 'Your account has been created.')

    def test_every_required_field_is_validated_without_saving(self):
        for field in ('name', 'email', 'password1', 'password2'):
            with self.subTest(field=field):
                response = self.submit(**{field: ''})
                self.assertEqual(response.status_code, 200)
                self.assertIn(field, response.context['form'].errors)
                self.assertContains(response, f'id="id_{field}_error"')
        self.assertFalse(User.objects.exists())

    def test_invalid_email_and_blank_name_are_rejected(self):
        for overrides, field in [({'email': 'not-an-email'}, 'email'), ({'name': '   '}, 'name'), ({'name': 'N' * 151}, 'name')]:
            with self.subTest(overrides=overrides):
                response = self.submit(**overrides)
                self.assertEqual(response.status_code, 200)
                self.assertIn(field, response.context['form'].errors)
        self.assertFalse(User.objects.exists())

    def test_matching_passwords_are_required(self):
        response = self.submit(password2='Different-password-42!')
        self.assertContains(response, 'id_password2_error')
        self.assertIn('password2', response.context['form'].errors)
        self.assertFalse(User.objects.exists())

    def test_default_password_strength_rules_remain_active(self):
        for password in ('short', 'password', '135792468000', 'new@example.com'):
            with self.subTest(password=password):
                response = self.submit(password1=password, password2=password)
                self.assertEqual(response.status_code, 200)
                self.assertIn('password2', response.context['form'].errors)
        self.assertFalse(User.objects.exists())

    def test_duplicate_email_variants_have_friendly_error(self):
        existing = User.objects.create_user('new@example.com', 'Original-password-42!', name='Original')
        for email in ('new@example.com', 'NEW@EXAMPLE.COM', 'New@Example.Com', '  new@example.com  '):
            with self.subTest(email=email):
                response = self.submit(email=email)
                self.assertContains(response, RegistrationForm.duplicate_email_message)
                self.assertIn('email', response.context['form'].errors)
                self.assertEqual(User.objects.count(), 1)
                self.assertNotIn(SESSION_KEY, self.client.session)
        existing.refresh_from_db()
        self.assertTrue(existing.check_password('Original-password-42!'))

    def test_duplicate_created_after_validation_is_handled(self):
        form = RegistrationForm(self.data())
        self.assertTrue(form.is_valid())
        User.objects.create_user('new@example.com', name='Competing signup')
        with patch('accounts.views.RegistrationForm', return_value=form):
            response = self.submit()
        self.assertContains(response, form.duplicate_email_message)
        self.assertEqual(User.objects.count(), 1)
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_unrelated_database_errors_are_not_hidden(self):
        form = RegistrationForm(self.data())
        self.assertTrue(form.is_valid())
        with patch('accounts.views.RegistrationForm', return_value=form), patch.object(form, 'save', side_effect=IntegrityError('unrelated database error')):
            with self.assertRaises(IntegrityError):
                self.submit()
        self.assertFalse(User.objects.exists())

    def test_registration_rotates_existing_anonymous_session(self):
        session = self.client.session
        session['anonymous_marker'] = 'keep'
        session.save()
        previous = session.session_key
        self.submit()
        self.assertNotEqual(self.client.session.session_key, previous)
        self.assertEqual(self.client.session['anonymous_marker'], 'keep')

    def test_signed_in_user_is_redirected_without_creating_another_account(self):
        user = User.objects.create_user('member@example.com', name='Member')
        self.client.force_login(user)
        self.assertRedirects(self.client.get(reverse('accounts:register')), reverse('transactions:list'))
        self.assertRedirects(self.submit(), reverse('transactions:list'))
        self.assertEqual(User.objects.count(), 1)

    def test_registration_requires_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        client.get(reverse('accounts:register'))
        self.assertEqual(client.post(reverse('accounts:register'), self.data()).status_code, 403)
        values = self.data(csrfmiddlewaretoken=client.cookies['csrftoken'].value)
        self.assertRedirects(client.post(reverse('accounts:register'), values), reverse('transactions:list'))
