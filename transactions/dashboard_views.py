# FT-39 to FT-43: Owner-scoped month selector and financial summary dashboard.
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views import View

from .months import MonthSelectionForm, current_month_start, get_month_financials


class DashboardView(LoginRequiredMixin, View):
    login_url = "accounts:login"
    template_name = "transactions/dashboard.html"

    def get(self, request):
        default = current_month_start()
        month_form = MonthSelectionForm(request.GET or None, initial={"month": default})
        month = month_form.cleaned_data["month"] if month_form.is_valid() else default
        summary = get_month_financials(request.user, month)
        return render(request, self.template_name, {"month": month, "month_form": month_form, **summary})
