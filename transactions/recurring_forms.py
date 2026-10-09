# FT-75: New recurring-rule form; the existing TransactionForm stays untouched.
from datetime import timedelta

from django import forms
from django.utils import timezone

from .models import RecurringTransaction


class RecurringTransactionForm(forms.ModelForm):
    class Meta:
        model = RecurringTransaction
        fields = ("transaction_type", "amount", "description", "frequency", "start_date", "end_date")
        widgets = {"start_date": forms.DateInput(attrs={"type": "date"}),
                   "end_date": forms.DateInput(attrs={"type": "date"})}
        help_texts = {"frequency": "Monthly entries on the 29th–31st move to the last day of shorter months."}

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount <= 0:
            raise forms.ValidationError("Amount must be greater than 0.")
        return amount

    def clean_start_date(self):
        start = self.cleaned_data["start_date"]
        if start < timezone.localdate() - timedelta(days=366):
            raise forms.ValidationError("Start dates more than a year ago aren't supported.")
        return start

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get("start_date"), cleaned.get("end_date")
        if start and end and end < start:
            self.add_error("end_date", "The end date must be on or after the start date.")
        return cleaned
