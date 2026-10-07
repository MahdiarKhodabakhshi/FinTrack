# FT-02: Keep application routes independent for later feature branches.
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path


def home(request):
    return redirect("transactions:list" if request.user.is_authenticated else "accounts:login")


urlpatterns = [
    path("", home, name="home"),
    path("accounts/", include("accounts.urls", namespace="accounts")),
    path("transactions/", include("transactions.urls", namespace="transactions")),
    path("admin/", admin.site.urls),
]
