# FT-59, FT-60: Month-to-month category spending comparison page.
from datetime import date

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views import View

from .comparison import MonthComparisonForm, compare_category_spending
from .months import current_month_start


def _previous_month(month):
    if month.month == 1:
        return date(month.year - 1, 12, 1)
    return date(month.year, month.month - 1, 1)


class MonthComparisonView(LoginRequiredMixin, View):
    login_url = "accounts:login"
    template_name = "transactions/month_comparison.html"

    def get(self, request):
        current = current_month_start()
        initial = {"month_a": _previous_month(current), "month_b": current}
        form = MonthComparisonForm(request.GET or None, initial=initial)
        if form.is_valid():
            month_a, month_b = form.cleaned_data["month_a"], form.cleaned_data["month_b"]
        else:
            month_a, month_b = initial["month_a"], initial["month_b"]
        comparison = compare_category_spending(request.user, month_a, month_b)
        return render(request, self.template_name, {
            "form": form,
            "month_a": month_a,
            "month_b": month_b,
            **comparison,
        })
