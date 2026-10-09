# FT-48, FT-49, FT-50, FT-51: Optional filters with safe, deterministic sorting.
from django import forms

from .models import Transaction

SORT_ORDERS = {
    "newest": ("-date", "-created_at", "-pk"),
    "oldest": ("date", "created_at", "pk"),
    "amount_high": ("-amount", "-date", "-pk"),
    "amount_low": ("amount", "-date", "-pk"),
}


class TransactionFilterForm(forms.Form):
    q = forms.CharField(label="Search", max_length=100, required=False, strip=True,
                        widget=forms.TextInput(attrs={"type": "search", "placeholder": "Search descriptions"}))
    type = forms.ChoiceField(label="Type", choices=[("", "All types"), *Transaction.TransactionType.choices], required=False)
    date_from = forms.DateField(label="From", required=False, widget=forms.DateInput(attrs={"type": "date"}))
    date_to = forms.DateField(label="To", required=False, widget=forms.DateInput(attrs={"type": "date"}))
    sort = forms.ChoiceField(label="Sort by", required=False, initial="newest", choices=[
        ("newest", "Newest first"), ("oldest", "Oldest first"),
        ("amount_high", "Amount: high to low"), ("amount_low", "Amount: low to high"),
    ])

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get("date_from"), cleaned.get("date_to")
        if start and end and start > end:
            self.add_error(None, "The start date must be on or before the end date.")
            cleaned.pop("date_from", None)
            cleaned.pop("date_to", None)
        return cleaned


def apply_transaction_filters(queryset, form):
    """FT-48 to FT-51: Filter an already user-scoped queryset using clean fields."""
    if not form.is_bound:
        return queryset.order_by(*SORT_ORDERS["newest"])
    form.is_valid()
    data = form.cleaned_data
    if data.get("q"):
        queryset = queryset.filter(description__icontains=data["q"])
    if data.get("type"):
        queryset = queryset.filter(transaction_type=data["type"])
    if data.get("date_from"):
        queryset = queryset.filter(date__gte=data["date_from"])
    if data.get("date_to"):
        queryset = queryset.filter(date__lte=data["date_to"])
    return queryset.order_by(*SORT_ORDERS.get(data.get("sort"), SORT_ORDERS["newest"]))


def filters_active(form):
    """FT-48 to FT-50: Keep Clear available for entered filters, including errors."""
    return any(str(form[name].value() or "").strip() for name in ("q", "type", "date_from", "date_to"))
