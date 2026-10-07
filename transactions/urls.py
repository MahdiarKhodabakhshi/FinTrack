# FT-02: Protected placeholders; FT-18 and FT-21 replace these views.
from django.contrib.auth.decorators import login_required
from django.urls import path
from django.views.generic import TemplateView

app_name = "transactions"
placeholder = login_required(TemplateView.as_view(template_name="base.html"), login_url="accounts:login")
urlpatterns = [
    path("", placeholder, name="list"),
    path("add/", placeholder, name="add"),
]
