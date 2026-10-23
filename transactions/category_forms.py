# FT-31, FT-34: Validate user-owned category names for add and rename actions.
from django import forms

from .models import Category


class CategoryForm(forms.ModelForm):
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    class Meta:
        model = Category
        fields = ("name",)
        widgets = {"name": forms.TextInput(attrs={"autocomplete": "off", "maxlength": 50})}

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        matches = Category.objects.filter(user=self.user, name__iexact=name)
        if self.instance.pk:
            matches = matches.exclude(pk=self.instance.pk)
        if matches.exists():
            raise forms.ValidationError("You already have a category with this name.")
        if not name:
            raise forms.ValidationError("Enter a category name.")
        return name
