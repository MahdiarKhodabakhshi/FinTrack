# FT-24 to FT-28: Owner-scoped transaction editing and deletion.
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import DeleteView, UpdateView

from .forms import TransactionForm
from .models import Transaction
from .views import get_user_transaction_or_404


def _safe_return_url(request):
    """Keep edit/delete flows on this site when returning to filtered history."""
    candidate = request.POST.get("next") or request.GET.get("next")
    if candidate and url_has_allowed_host_and_scheme(candidate, {request.get_host()}, require_https=request.is_secure()):
        return candidate
    return reverse("transactions:list")


class TransactionUpdateView(LoginRequiredMixin, UpdateView):
    login_url = "accounts:login"
    model = Transaction
    form_class = TransactionForm
    template_name = "transactions/transaction_form.html"

    def get_object(self, queryset=None):
        return get_user_transaction_or_404(self.request.user, self.kwargs["pk"])

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(page_title="Edit transaction", submit_label="Save changes", cancel_url=_safe_return_url(self.request))
        return context

    def get_success_url(self):
        return _safe_return_url(self.request)

    def form_valid(self, form):
        messages.success(self.request, "Transaction updated.")
        return super().form_valid(form)


class TransactionDeleteView(LoginRequiredMixin, DeleteView):
    login_url = "accounts:login"
    model = Transaction
    template_name = "transactions/transaction_confirm_delete.html"

    def get_object(self, queryset=None):
        return get_user_transaction_or_404(self.request.user, self.kwargs["pk"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cancel_url"] = _safe_return_url(self.request)
        return context

    def get_success_url(self):
        return _safe_return_url(self.request)

    def form_valid(self, form):
        messages.success(self.request, "Transaction deleted.")
        return super().form_valid(form)
