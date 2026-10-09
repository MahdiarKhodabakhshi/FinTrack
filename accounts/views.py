# FT-11: Register with Django's password handling and a fresh authenticated session.
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_not_required
from django.shortcuts import redirect, render
from django.db import IntegrityError, transaction

from .forms import RegistrationForm
from .models import User


# FT-14: Registration must remain reachable without an existing account.
@login_not_required
def register(request):
    if request.user.is_authenticated:
        return redirect("transactions:list")
    form = RegistrationForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        # FT-08: A competing signup can pass validation before the unique DB check.
        try:
            with transaction.atomic():
                user = form.save()
        except IntegrityError:
            if not User.objects.filter(email__iexact=form.cleaned_data["email"]).exists():
                raise
            form.add_error("email", form.duplicate_email_message)
        else:
            login(request, user)
            messages.success(request, "Your account has been created.")
            return redirect("transactions:list")
    return render(request, "accounts/register.html", {"form": form})
