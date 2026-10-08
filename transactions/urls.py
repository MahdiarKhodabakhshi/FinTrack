# FT-18, FT-21: Both endpoints explicitly require a signed-in user.
from django.urls import path

from .views import TransactionCreateView, TransactionListView, transaction_export_csv

from .recurring_views import RecurringCreateView, RecurringDeleteView, RecurringListView, recurring_toggle

app_name = "transactions"
urlpatterns = [
    # FT-75: Every rule lookup checks ownership; changes use POST.
    path("recurring/", RecurringListView.as_view(), name="recurring_list"),
    path("recurring/add/", RecurringCreateView.as_view(), name="recurring_add"),
    path("recurring/<int:pk>/toggle/", recurring_toggle, name="recurring_toggle"),
    path("recurring/<int:pk>/delete/", RecurringDeleteView.as_view(), name="recurring_delete"),
    # FT-72: GET-only private CSV download.
    path("export/", transaction_export_csv, name="export"),
    path("", TransactionListView.as_view(), name="list"),
    path("add/", TransactionCreateView.as_view(), name="add"),
]
