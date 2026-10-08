# FT-03: Admin forms adapted to the email-only User model.
from django import forms
from django.contrib.auth.forms import (
    AdminUserCreationForm, AuthenticationForm, BaseUserCreationForm, UserChangeForm,
)

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
class RegistrationForm(BaseUserCreationForm):
    # FT-06: EmailField checks format; Django validates password strength/matching.
    # FT-08: Check case variants before saving and give a friendly field error.
    duplicate_email_message = "An account with this email already exists."

    def clean_email(self):
        email = User.objects.normalize_email(self.cleaned_data["email"]).lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(self.duplicate_email_message, code="unique")
        return email

    class Meta(BaseUserCreationForm.Meta):
        model = User
        fields = ("name", "email")


class LoginForm(AuthenticationForm):
    username = forms.EmailField(label="Email", widget=forms.EmailInput(attrs={"autofocus": True}))
