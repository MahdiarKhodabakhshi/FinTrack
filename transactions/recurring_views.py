# FT-75, FT-76: Private recurring-rule pages and POST-only state changes.
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, ListView

from .models import RecurringTransaction
from .recurring import generate_due_transactions, resume_rule
from .recurring_forms import RecurringTransactionForm


class RecurringListView(LoginRequiredMixin, ListView):
    login_url = "accounts:login"
    template_name = "transactions/recurring_list.html"
    context_object_name = "rules"

    def get(self, request, *args, **kwargs):
        generate_due_transactions(user=request.user)
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return RecurringTransaction.objects.filter(user=self.request.user)


class RecurringCreateView(LoginRequiredMixin, CreateView):
    login_url = "accounts:login"
    model = RecurringTransaction
    form_class = RecurringTransactionForm
    template_name = "transactions/recurring_form.html"
    success_url = reverse_lazy("transactions:recurring_list")

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.next_due_date = form.cleaned_data["start_date"]
        response = super().form_valid(form)
        count = generate_due_transactions(user=self.request.user)
        noun = "entry" if count == 1 else "entries"
        messages.success(self.request, f"Recurring transaction created. {count} {noun} added so far.")
        return response


@login_required
@require_POST
def recurring_toggle(request, pk):
    with transaction.atomic():
        rule = get_object_or_404(RecurringTransaction.objects.select_for_update(), pk=pk, user=request.user)
        if rule.is_active:
            rule.is_active = False
            rule.save(update_fields=["is_active", "updated_at"])
            messages.success(request, "Recurring transaction paused.")
        else:
            resume_rule(rule)
            messages.success(request, "Recurring transaction resumed." if rule.is_active else "Recurring transaction has ended.")
    return redirect("transactions:recurring_list")


class RecurringDeleteView(LoginRequiredMixin, DeleteView):
    login_url = "accounts:login"
    template_name = "transactions/recurring_confirm_delete.html"
    success_url = reverse_lazy("transactions:recurring_list")

    def get_object(self, queryset=None):
        return get_object_or_404(RecurringTransaction, pk=self.kwargs["pk"], user=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Recurring transaction deleted. Already-created entries stay in your history.")
        return super().form_valid(form)
