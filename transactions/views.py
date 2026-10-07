# FT-18: Create records for the authenticated user.
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView

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

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)


def get_user_transaction_or_404(user, pk):
    """FT-24 to FT-27: Sprint 2 edit/delete views must use this ownership helper."""
    return get_object_or_404(Transaction, pk=pk, user=user)
