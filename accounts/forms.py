# FT-03: Admin forms adapted to the email-only User model.
from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm

from .models import User


class UserAdminCreationForm(AdminUserCreationForm):
    class Meta(AdminUserCreationForm.Meta):
        model = User
        fields = ("email", "name")


class UserAdminChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = ("email", "name", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")


# FT-11: Django handles baseline password validation and authentication.
from django import forms
from django.contrib.auth.forms import AuthenticationForm, BaseUserCreationForm


class RegistrationForm(BaseUserCreationForm):
    # FT-06 (Tom): custom validation rules go here
    # FT-08 (Tom): friendly duplicate-email message goes here
    class Meta(BaseUserCreationForm.Meta):
        model = User
        fields = ("name", "email")


class LoginForm(AuthenticationForm):
    username = forms.EmailField(label="Email", widget=forms.EmailInput(attrs={"autofocus": True}))
