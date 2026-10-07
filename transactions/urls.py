# FT-02: Protected placeholders; FT-18 and FT-21 replace these views.
from django.contrib.auth.decorators import login_required
from django.urls import path

from .views import TransactionCreateView
from django.views.generic import TemplateView

app_name = "transactions"
placeholder = login_required(TemplateView.as_view(template_name="base.html"), login_url="accounts:login")
urlpatterns = [
    path("", placeholder, name="list"),
    # FT-18: Save transactions using the signed-in user.
    path("add/", TransactionCreateView.as_view(), name="add"),
]
