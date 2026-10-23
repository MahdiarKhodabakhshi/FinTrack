# FT-30 to FT-34: User-owned category management and safe category removal.
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction as db_transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from .category_forms import CategoryForm
from .models import Category, RecurringTransaction, Transaction


class CategoryListView(LoginRequiredMixin, ListView):
    login_url = "accounts:login"
    model = Category
    context_object_name = "categories"
    template_name = "transactions/category_list.html"

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = kwargs.get("form") or CategoryForm(user=self.request.user)
        context["custom_categories"] = Category.objects.filter(user=self.request.user, is_default=False).order_by("name")
        context["uncategorized"] = Category.objects.filter(user=self.request.user, is_uncategorized=True).first()
        return context


class CategoryCreateView(LoginRequiredMixin, CreateView):
    login_url = "accounts:login"
    model = Category
    form_class = CategoryForm
    template_name = "transactions/category_list.html"
    success_url = reverse_lazy("transactions:categories")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = Category.objects.filter(user=self.request.user)
        context["custom_categories"] = Category.objects.filter(user=self.request.user, is_default=False).order_by("name")
        context["uncategorized"] = Category.objects.filter(user=self.request.user, is_uncategorized=True).first()
        return context

    def form_valid(self, form):
        form.instance.user = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, "Category created.")
        return response


class CategoryUpdateView(LoginRequiredMixin, UpdateView):
    login_url = "accounts:login"
    model = Category
    form_class = CategoryForm
    template_name = "transactions/category_form.html"
    success_url = reverse_lazy("transactions:categories")

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user, is_default=False, is_uncategorized=False)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Category updated.")
        return response


class CategoryDeleteView(LoginRequiredMixin, View):
    login_url = "accounts:login"
    template_name = "transactions/category_confirm_delete.html"

    def get_category(self, request, pk):
        return get_object_or_404(Category, pk=pk, user=request.user, is_default=False, is_uncategorized=False)

    def get(self, request, pk):
        category = self.get_category(request, pk)
        return render(request, self.template_name, {"category": category})

    def post(self, request, pk):
        category = self.get_category(request, pk)
        with db_transaction.atomic():
            uncategorized = get_object_or_404(Category, user=request.user, is_uncategorized=True)
            now = timezone.now()
            Transaction.objects.filter(user=request.user, category=category).update(category=uncategorized, updated_at=now)
            RecurringTransaction.objects.filter(user=request.user, category=category).update(category=uncategorized, updated_at=now)
            category.delete()  # FT-33: Associated category budgets are removed by their FK cascade.
        messages.success(request, "Category deleted. Its transactions were moved to Uncategorized and its budgets were removed.")
        return redirect("transactions:categories")
