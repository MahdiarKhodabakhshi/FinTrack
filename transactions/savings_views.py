# FT-73, FT-74: Owner-scoped savings goals, contribution history and progress.
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import CreateView

from .models import SavingsContribution, SavingsGoal
from .savings_forms import SavingsContributionForm, SavingsGoalForm


def _goal_rows(user, *, bound_goal=None, bound_form=None):
    goals = SavingsGoal.objects.filter(user=user).annotate(
        saved_amount=Sum("contributions__amount", default=Decimal("0.00")),
    ).prefetch_related("contributions")
    rows = list(goals)
    for goal in rows:
        goal.progress_percent = min(100, int(goal.saved_amount * 100 / goal.target_amount))
        goal.remaining_amount = max(goal.target_amount - goal.saved_amount, Decimal("0.00"))
        goal.is_complete = goal.saved_amount >= goal.target_amount
        prefix = f"goal-{goal.pk}"
        goal.contribution_form = (
            bound_form if bound_goal == goal.pk
            else SavingsContributionForm(prefix=prefix, initial={"date": timezone.localdate()})
        )
    return rows


@login_required
def savings_goal_list(request):
    return render(request, "transactions/savings_goal_list.html", {
        "goals": _goal_rows(request.user),
    })


class SavingsGoalCreateView(LoginRequiredMixin, CreateView):
    login_url = "accounts:login"
    model = SavingsGoal
    form_class = SavingsGoalForm
    template_name = "transactions/savings_goal_form.html"
    success_url = reverse_lazy("transactions:savings_goals")

    def form_valid(self, form):
        form.instance.user = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, "Savings goal created.")
        return response


@login_required
@require_POST
def savings_goal_contribute(request, pk):
    goal = get_object_or_404(SavingsGoal, pk=pk, user=request.user)
    form = SavingsContributionForm(request.POST, prefix=f"goal-{goal.pk}")
    if form.is_valid():
        SavingsContribution.objects.create(
            goal=goal,
            amount=form.cleaned_data["amount"],
            date=form.cleaned_data["date"],
            note=form.cleaned_data["note"],
        )
        messages.success(request, f"Contribution added to {goal.name}.")
        return redirect("transactions:savings_goals")
    return render(request, "transactions/savings_goal_list.html", {
        "goals": _goal_rows(request.user, bound_goal=goal.pk, bound_form=form),
    })
