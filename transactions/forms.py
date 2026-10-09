# FT-18: Ownership is assigned by the view, never accepted from form input.
from django import forms

from .models import Transaction


class TransactionForm(forms.ModelForm):
    # FT-17: DateField parses valid dates; model fields require type, amount and date.
    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount <= 0:
            raise forms.ValidationError("Amount must be greater than 0.")
        return amount

    class Meta:
        model = Transaction
        fields = ("transaction_type", "amount", "date", "description")
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}
        error_messages = {
            "transaction_type": {"required": "Choose income or expense.", "invalid_choice": "Choose income or expense."},
            "amount": {"required": "Enter an amount."},
            "date": {"required": "Enter a transaction date.", "invalid": "Enter a valid date."},
        }
