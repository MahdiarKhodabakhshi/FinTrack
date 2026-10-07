# FT-18: Ownership is assigned by the view, never accepted from form input.
from django import forms

from .models import Transaction


class TransactionForm(forms.ModelForm):
    # FT-17 (Tom): custom validation rules go here
    class Meta:
        model = Transaction
        fields = ("transaction_type", "amount", "date", "description")
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}
