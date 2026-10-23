# FT-18: Ownership is assigned by the view, never accepted from form input.
from django import forms

from .models import Category, Transaction


class TransactionForm(forms.ModelForm):
    category = forms.ModelChoiceField(
        queryset=Category.objects.none(),
        required=False,
        label="Category",
        help_text="Required for expenses. Income is saved without a category.",
    )
    category.required_for_expense = True

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if user is not None:
            self.fields["category"].queryset = Category.objects.filter(user=user).order_by("is_uncategorized", "name")
            if not self.is_bound and not self.instance.pk:
                self.initial.setdefault(
                    "category", Category.objects.filter(user=user, is_uncategorized=True).values_list("pk", flat=True).first()
                )

    # FT-17: DateField parses valid dates; model fields require type, amount and date.
    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount <= 0:
            raise forms.ValidationError("Amount must be greater than 0.")
        return amount

    def clean(self):
        cleaned = super().clean()
        transaction_type = cleaned.get("transaction_type")
        category = cleaned.get("category")
        if transaction_type == Transaction.TransactionType.EXPENSE and category is None:
            self.add_error("category", "Choose a category for this expense.")
        elif transaction_type == Transaction.TransactionType.INCOME:
            cleaned["category"] = None
        if category is not None and self.user is not None and category.user_id != self.user.pk:
            self.add_error("category", "Choose one of your own categories.")
        date_value = cleaned.get("date")
        if self.instance.pk and self.instance.recurring_source_id and date_value:
            duplicate = Transaction.objects.filter(recurring_source_id=self.instance.recurring_source_id, date=date_value).exclude(pk=self.instance.pk)
            if duplicate.exists():
                self.add_error("date", "A recurring transaction already exists on that date.")
        return cleaned

    class Meta:
        model = Transaction
        fields = ("transaction_type", "amount", "date", "description", "category")
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}
        error_messages = {
            "transaction_type": {"required": "Choose income or expense.", "invalid_choice": "Choose income or expense."},
            "amount": {"required": "Enter an amount."},
            "date": {"required": "Enter a transaction date.", "invalid": "Enter a valid date."},
        }
