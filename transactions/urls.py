# FT-18, FT-21: Both endpoints explicitly require a signed-in user.
from django.urls import path

from .views import TransactionCreateView, TransactionListView

app_name = "transactions"
urlpatterns = [
    path("", TransactionListView.as_view(), name="list"),
    path("add/", TransactionCreateView.as_view(), name="add"),
]
