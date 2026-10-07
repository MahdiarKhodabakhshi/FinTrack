# FT-02: Temporary public route placeholders; FT-11 replaces these views.
from django.urls import path
from django.views.generic import TemplateView

app_name = "accounts"
urlpatterns = [
    path("login/", TemplateView.as_view(template_name="accounts/login.html"), name="login"),
    path("register/", TemplateView.as_view(template_name="accounts/register.html"), name="register"),
]
