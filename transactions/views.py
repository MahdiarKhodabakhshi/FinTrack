# FT-18: Create records for the authenticated user.
import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.http import require_GET
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView

from .filters import TransactionFilterForm, apply_transaction_filters, filters_active
from .forms import TransactionForm
from .models import Transaction


class TransactionCreateView(LoginRequiredMixin, CreateView):
    login_url = "accounts:login"
    model = Transaction
    form_class = TransactionForm
    template_name = "transactions/transaction_form.html"
    success_url = reverse_lazy("transactions:list")

    def form_valid(self, form):
        form.instance.user = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, "Transaction added.")
        return response


# FT-21: Filter history and future individual lookups by user ownership.
class TransactionListView(LoginRequiredMixin, ListView):
    login_url = "accounts:login"
    model = Transaction
    context_object_name = "transactions"
    template_name = "transactions/transaction_list.html"

    # FT-48 to FT-51: Start with ownership, then reuse the shared filter pipeline.
    def get_queryset(self):
        self.filter_form = TransactionFilterForm(self.request.GET or None)
        return apply_transaction_filters(Transaction.objects.filter(user=self.request.user), self.filter_form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.copy()
        for key, values in list(query.lists()):
            nonempty = [value for value in values if value]
            if nonempty:
                query.setlist(key, nonempty)
            else:
                del query[key]
        context.update(
            filter_form=self.filter_form,
            filters_active=filters_active(self.filter_form),
            result_count=self.object_list.count(),
            sort_label=dict(self.filter_form.fields["sort"].choices).get(
                getattr(self.filter_form, "cleaned_data", {}).get("sort"), "Newest first"),
            has_any_transactions=Transaction.objects.filter(user=self.request.user).exists(),
            export_query=query.urlencode(),
        )
        return context


def get_user_transaction_or_404(user, pk):
    """FT-24 to FT-27: Sprint 2 edit/delete views must use this ownership helper."""
    return get_object_or_404(Transaction, pk=pk, user=user)


# FT-72: Export the same user-scoped, filtered, ordered rows as the list.
@login_required
@require_GET
def transaction_export_csv(request):
    form = TransactionFilterForm(request.GET or None)
    rows = apply_transaction_filters(Transaction.objects.filter(user=request.user), form)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="fintrack-transactions-{timezone.localdate():%Y-%m-%d}.csv"'
    response["Cache-Control"] = "no-store"
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(["Date", "Type", "Description", "Amount"])
    for record in rows.iterator():
        description = record.description
        if description.startswith(("=", "+", "-", "@", "\t", "\r")):
            description = "'" + description
        writer.writerow([record.date.isoformat(), record.get_transaction_type_display(),
                         description, f"{record.signed_amount:.2f}"])
    return response
