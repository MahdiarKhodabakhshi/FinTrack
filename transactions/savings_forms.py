# FT-73, FT-74: Validate goal targets and dated savings contributions.
from decimal import Decimal

from django import forms

from .models import SavingsGoal


class SavingsGoalForm(forms.ModelForm):
    class Meta:
        model = SavingsGoal
        fields = ("name", "target_amount", "target_date")
        widgets = {"target_date": forms.DateInput(attrs={"type": "date"})}
        labels = {"name": "Goal name", "target_amount": "Target amount", "target_date": "Target date"}

    target_amount = forms.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if not name:
            raise forms.ValidationError("Enter a name for this savings goal.")
        return name


class SavingsContributionForm(forms.Form):
    amount = forms.DecimalField(label="Contribution", max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    date = forms.DateField(label="Date", widget=forms.DateInput(attrs={"type": "date"}))
    note = forms.CharField(label="Note", max_length=255, required=False)
