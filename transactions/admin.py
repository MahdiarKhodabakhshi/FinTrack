# FT-03: Inspect transactions in Django admin.
from django.contrib import admin

from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ["user", "transaction_type", "amount", "date"]
    list_filter = ["transaction_type", "date"]
    search_fields = ["description"]
