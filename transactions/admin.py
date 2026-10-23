# FT-03: Inspect transactions in Django admin.
from django.contrib import admin

from .models import Budget, Category, RecurringTransaction, Transaction


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "user", "is_default", "is_uncategorized"]
    list_filter = ["is_default", "is_uncategorized"]
    search_fields = ["name", "user__email"]


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ["category", "user", "month_start", "amount"]
    list_filter = ["month_start"]
    search_fields = ["category__name", "user__email"]


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ["user", "transaction_type", "amount", "date", "category"]
    list_filter = ["transaction_type", "date"]
    search_fields = ["description"]


# FT-75: Admin inspection of recurring schedules.
@admin.register(RecurringTransaction)
class RecurringTransactionAdmin(admin.ModelAdmin):
    list_display = ["description", "user", "transaction_type", "amount", "category", "frequency", "next_due_date", "is_active"]
    list_filter = ["transaction_type", "frequency", "is_active"]
    search_fields = ["description", "user__email"]
