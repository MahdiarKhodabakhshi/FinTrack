# FT-15: Email login, safe redirect handling and POST-only logout features.
from django.contrib.auth import SESSION_KEY
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import User


class LoginLogoutTests(TestCase):
    password = 'Distinct-login-passphrase-42!'

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('member@example.com', cls.password, name='Member')

    def login(self, **overrides):
        data = {'username': 'MEMBER@EXAMPLE.COM', 'password': self.password}
        data.update(overrides)
        return self.client.post(reverse('accounts:login'), data)

    def test_login_page_uses_email_label_and_correct_post_field(self):
        response = self.client.get(reverse('accounts:login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/login.html')
        self.assertEqual(response.context['form'].fields['username'].label, 'Email')
        self.assertContains(response, 'name="username"')

    def test_valid_case_insensitive_login_starts_session(self):
        self.assertRedirects(self.login(), reverse('transactions:list'))
        self.assertEqual(self.client.session[SESSION_KEY], str(self.user.pk))
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.last_login)

    def test_invalid_credentials_show_same_clear_error(self):
        errors = []
        for overrides in ({'password': 'wrong'}, {'username': 'unknown@example.com'}):
            with self.subTest(overrides=overrides):
                response = self.login(**overrides)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'Please enter a correct email and password.')
                self.assertContains(response, 'role="alert"')
                self.assertNotIn(SESSION_KEY, self.client.session)
                errors.append(list(response.context['form'].non_field_errors()))
        self.assertEqual(errors[0], errors[1])

    def test_required_credentials_are_checked(self):
        for field in ('username', 'password'):
            with self.subTest(field=field):
                response = self.login(**{field: ''})
                self.assertIn(field, response.context['form'].errors)
                self.assertNotIn(SESSION_KEY, self.client.session)

    def test_inactive_user_cannot_login(self):
        self.user.is_active = False
        self.user.save(update_fields=['is_active'])
        response = self.login()
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_safe_next_redirect_is_respected(self):
        self.assertRedirects(self.login(next=reverse('transactions:add')), reverse('transactions:add'))

    def test_external_next_redirect_is_ignored(self):
        for destination in ('https://evil.example/path', '//evil.example/path'):
            self.client.logout()
            with self.subTest(destination=destination):
                self.assertRedirects(self.login(next=destination), reverse('transactions:list'))

    def test_authenticated_user_skips_login_page(self):
        self.client.force_login(self.user)
        self.assertRedirects(self.client.get(reverse('accounts:login')), reverse('transactions:list'))

    def test_get_logout_leaves_session_intact(self):
        self.login()
        self.assertEqual(self.client.get(reverse('accounts:logout')).status_code, 405)
        self.assertEqual(self.client.session[SESSION_KEY], str(self.user.pk))

    def test_post_logout_flushes_session_and_protects_history(self):
        self.login()
        session = self.client.session
        session['private_marker'] = 'remove'
        session.save()
        self.assertRedirects(self.client.post(reverse('accounts:logout')), reverse('accounts:login'))
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertNotIn('private_marker', self.client.session)
        self.assertRedirects(self.client.get(reverse('transactions:list')), reverse('accounts:login') + '?next=/transactions/')

    def test_login_and_logout_require_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.get(reverse('accounts:login'))
        credentials = {'username': self.user.email, 'password': self.password}
        self.assertEqual(client.post(reverse('accounts:login'), credentials).status_code, 403)
        credentials['csrfmiddlewaretoken'] = client.cookies['csrftoken'].value
        self.assertRedirects(client.post(reverse('accounts:login'), credentials), reverse('transactions:list'))
        self.assertEqual(client.post(reverse('accounts:logout')).status_code, 403)
        self.assertIn(SESSION_KEY, client.session)
        token = client.cookies['csrftoken'].value
        self.assertRedirects(client.post(reverse('accounts:logout'), {'csrfmiddlewaretoken': token}), reverse('accounts:login'))
