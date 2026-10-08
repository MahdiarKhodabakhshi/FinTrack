# FT-03: Inspect transactions in Django admin.
from django.contrib import admin

from .models import RecurringTransaction, Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ["user", "transaction_type", "amount", "date"]
    list_filter = ["transaction_type", "date"]
    search_fields = ["description"]


# FT-75: Admin inspection of recurring schedules.
@admin.register(RecurringTransaction)
class RecurringTransactionAdmin(admin.ModelAdmin):
    list_display = ["description", "user", "transaction_type", "amount", "frequency", "next_due_date", "is_active"]
    list_filter = ["transaction_type", "frequency", "is_active"]
    search_fields = ["description", "user__email"]
