# FT-18, FT-21: Both endpoints explicitly require a signed-in user.
from django.urls import path

from .views import TransactionCreateView, TransactionListView, transaction_export_csv
from .budget_views import BudgetListView
from .category_views import CategoryCreateView, CategoryDeleteView, CategoryListView, CategoryUpdateView
from .dashboard_views import DashboardView
from .comparison_views import MonthComparisonView
from .transaction_management import TransactionDeleteView, TransactionUpdateView

from .recurring_views import RecurringCreateView, RecurringDeleteView, RecurringListView, recurring_toggle
from .savings_views import SavingsGoalCreateView, savings_goal_contribute, savings_goal_list

app_name = "transactions"
urlpatterns = [
    # FT-29 to FT-43: User-scoped category, budget, dashboard and transaction routes.
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    # FT-59, FT-60: Compare category expenses across months.
    path("compare/", MonthComparisonView.as_view(), name="comparison"),
    # FT-73, FT-74: Create goals and record private dated contributions.
    path("savings/", savings_goal_list, name="savings_goals"),
    path("savings/add/", SavingsGoalCreateView.as_view(), name="savings_goal_add"),
    path("savings/<int:pk>/contribute/", savings_goal_contribute, name="savings_goal_contribute"),
    path("categories/", CategoryListView.as_view(), name="categories"),
    path("categories/add/", CategoryCreateView.as_view(), name="category_add"),
    path("categories/<int:pk>/edit/", CategoryUpdateView.as_view(), name="category_edit"),
    path("categories/<int:pk>/delete/", CategoryDeleteView.as_view(), name="category_delete"),
    path("budgets/", BudgetListView.as_view(), name="budgets"),
    path("<int:pk>/edit/", TransactionUpdateView.as_view(), name="edit"),
    path("<int:pk>/delete/", TransactionDeleteView.as_view(), name="delete"),
    # FT-75: Every rule lookup checks ownership; changes use POST.
    path("recurring/", RecurringListView.as_view(), name="recurring_list"),
    path("recurring/add/", RecurringCreateView.as_view(), name="recurring_add"),
    path("recurring/<int:pk>/toggle/", recurring_toggle, name="recurring_toggle"),
    path("recurring/<int:pk>/delete/", RecurringDeleteView.as_view(), name="recurring_delete"),
    # FT-72: GET-only private CSV download.
    path("export/", transaction_export_csv, name="export"),
    path("", TransactionListView.as_view(), name="list"),
    path("add/", TransactionCreateView.as_view(), name="add"),
]
