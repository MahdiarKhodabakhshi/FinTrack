# FT-18: Create records for the authenticated user.
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView

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
