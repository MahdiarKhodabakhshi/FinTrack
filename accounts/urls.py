# FT-11: Email login and registration endpoints.
from django.contrib.auth.views import LoginView
from django.urls import path

from .forms import LoginForm
from .views import register

app_name = "accounts"
urlpatterns = [
    path("register/", register, name="register"),
    path("login/", LoginView.as_view(
        template_name="accounts/login.html",
        authentication_form=LoginForm,
        redirect_authenticated_user=True,
    ), name="login"),
]
