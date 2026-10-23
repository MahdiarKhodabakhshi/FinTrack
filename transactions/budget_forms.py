# FT-36, FT-38: User-scoped monthly category budget form.
from decimal import Decimal

from django import forms

from .models import Budget, Category
from .months import MonthField


class BudgetForm(forms.ModelForm):
    month_start = MonthField(label="Budget month")
    amount = forms.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"), label="Monthly limit")

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["category"].queryset = Category.objects.filter(user=user, is_uncategorized=False).order_by("name")
        self.fields["amount"].widget.attrs.update({"inputmode": "decimal", "placeholder": "0.00", "step": "0.01"})

    class Meta:
        model = Budget
        fields = ("category", "month_start", "amount")

    def clean(self):
        cleaned = super().clean()
        category = cleaned.get("category")
        if category is not None and self.user is not None and category.user_id != self.user.pk:
            self.add_error("category", "Choose one of your own categories.")
        return cleaned
