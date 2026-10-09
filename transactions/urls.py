# FT-18, FT-21: Both endpoints explicitly require a signed-in user.
from django.urls import path

from .views import TransactionCreateView, TransactionListView, transaction_export_csv

app_name = "transactions"
urlpatterns = [
    # FT-72: GET-only private CSV download.
    path("export/", transaction_export_csv, name="export"),
    path("", TransactionListView.as_view(), name="list"),
    path("add/", TransactionCreateView.as_view(), name="add"),
]
