# FT-04: Small presentation helpers; Django retains widget validation attributes.
from decimal import Decimal, ROUND_HALF_UP

from django import forms, template

register = template.Library()


@register.simple_tag
def field_widget(field, **attrs):
    """FT-04: Render a bound widget with Bootstrap classes and optional attributes."""
    widget = field.field.widget
    if isinstance(widget, forms.Select):
        base_class = "form-select"
    elif isinstance(widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple, forms.RadioSelect)):
        base_class = "form-check-input"
    else:
        base_class = "form-control"
    supplied = {}
    for key, value in attrs.items():
        if value is not None and value != "":
            key = key.replace("_", "-") if key.startswith(("aria_", "data_")) else key
            supplied[key] = value
    classes = [*widget.attrs.get("class", "").split(), *supplied.pop("class", "").split(), base_class]
    if field.errors:
        classes.append("is-invalid")
    supplied["class"] = " ".join(dict.fromkeys(classes))
    return field.as_widget(attrs=supplied)


@register.filter
def money(value, mode=""):
    """FT-20: Format Decimal money independently of locale, with optional signs."""
    if value is None:
        return ""
    value = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    sign = "−" if value < 0 else "+" if mode == "signed" and value > 0 else ""
    return f"{sign}${abs(value):,.2f}"


@register.simple_tag
def nav_active(request, view_name):
    """FT-04: Return the active class only for the current named route."""
    match = getattr(request, "resolver_match", None)
    return "active" if match and match.view_name == view_name else ""
