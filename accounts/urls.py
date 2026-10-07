# FT-11: Email login and registration endpoints.
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from .forms import LoginForm
from .views import register

app_name = "accounts"
urlpatterns = [
    # FT-13: Django LogoutView accepts POST and flushes the session.
    path("logout/", LogoutView.as_view(), name="logout"),
    path("register/", register, name="register"),
    path("login/", LoginView.as_view(
        template_name="accounts/login.html",
        authentication_form=LoginForm,
        redirect_authenticated_user=True,
    ), name="login"),
]
