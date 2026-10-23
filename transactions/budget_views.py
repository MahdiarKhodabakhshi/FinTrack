# FT-35 to FT-38: User-scoped monthly budgets and category spending calculations.
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View

from .budget_forms import BudgetForm
from .models import Budget, Category
from .months import MonthSelectionForm, current_month_start, get_month_financials


def _budget_rows(user, month):
    summary_rows = {row["category"].pk: row for row in get_month_financials(user, month)["category_rows"]}
    budgets = Budget.objects.filter(user=user, month_start=month).select_related("category")
    budget_by_category = {budget.category_id: budget for budget in budgets}
    rows = []
    for category in Category.objects.filter(user=user, is_uncategorized=False).order_by("name"):
        summary = summary_rows.get(category.pk, {})
        budget = budget_by_category.get(category.pk)
        spent = summary.get("spent", 0)
        amount = budget.amount if budget else None
        rows.append({"category": category, "budget": budget, "spent": spent,
                     "remaining": amount - spent if amount is not None else None})
    return budgets, rows


class BudgetListView(LoginRequiredMixin, View):
    login_url = "accounts:login"
    template_name = "transactions/budget_list.html"

    def get_month(self, request):
        default = current_month_start()
        selection = MonthSelectionForm(request.GET or None, initial={"month": default})
        if selection.is_valid():
            return selection.cleaned_data["month"], selection
        return default, selection

    def get(self, request):
        month, month_form = self.get_month(request)
        selected = None
        category_id = request.GET.get("category")
        if category_id:
            selected = Category.objects.filter(user=request.user, pk=category_id, is_uncategorized=False).first()
        form = BudgetForm(user=request.user, initial={"month_start": month, "category": selected})
        budgets, rows = _budget_rows(request.user, month)
        return render(request, self.template_name, {
            "form": form, "month_form": month_form, "month": month,
            "budgets": budgets, "has_budgets": budgets.exists(), "budget_rows": rows,
        })

    def post(self, request):
        form = BudgetForm(request.POST, user=request.user)
        month_form = MonthSelectionForm({"month": request.POST.get("month_start", "")})
        if form.is_valid():
            category = form.cleaned_data["category"]
            month = form.cleaned_data["month_start"]
            Budget.objects.update_or_create(
                user=request.user, category=category, month_start=month,
                defaults={"amount": form.cleaned_data["amount"]},
            )
            messages.success(request, "Monthly budget saved.")
            return redirect(f"{reverse('transactions:budgets')}?month={month:%Y-%m}&category={category.pk}")
        month = month_form.cleaned_data.get("month") if month_form.is_valid() else current_month_start()
        budgets, rows = _budget_rows(request.user, month)
        return render(request, self.template_name, {
            "form": form, "month_form": month_form, "month": month,
            "budgets": budgets, "has_budgets": budgets.exists(), "budget_rows": rows,
        })
