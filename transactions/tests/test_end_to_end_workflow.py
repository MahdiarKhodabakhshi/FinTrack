# FT-62 to FT-64, FT-67: Exercise the complete core finance workflow end to end.
from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from transactions.models import Budget, Category, Transaction
from transactions.models import SavingsContribution, SavingsGoal


class EndToEndWorkflowTests(TestCase):
    def test_register_record_budget_dashboard_edit_delete_and_logout(self):
        response = self.client.post(reverse("accounts:register"), {
            "name": "Workflow User",
            "email": "workflow@example.com",
            "password1": "Random-Secure-Phrase-9164!",
            "password2": "Random-Secure-Phrase-9164!",
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your account has been created")
        user = User.objects.get(email="workflow@example.com")
        self.assertTrue(response.wsgi_request.user.is_authenticated)

        food = Category.objects.get(user=user, name="Food")
        income_response = self.client.post(reverse("transactions:add"), {
            "transaction_type": "income", "amount": "2400.00", "date": "2026-10-01",
            "description": "October pay",
        })
        self.assertEqual(income_response.status_code, 302)
        expense_response = self.client.post(reverse("transactions:add"), {
            "transaction_type": "expense", "amount": "260.00", "date": "2026-10-02",
            "description": "Groceries", "category": food.pk,
        })
        self.assertEqual(expense_response.status_code, 302)
        expense = Transaction.objects.get(user=user, description="Groceries")
        self.assertEqual(expense.category, food)

        self.client.post(reverse("transactions:budgets"), {
            "category": food.pk, "month_start": "2026-10", "amount": "200.00",
        })
        self.assertEqual(Budget.objects.get(user=user, category=food).amount, Decimal("200.00"))
        dashboard = self.client.get(reverse("transactions:dashboard"), {"month": "2026-10"})
        self.assertContains(dashboard, "$2,400.00")
        self.assertContains(dashboard, "$260.00")
        self.assertContains(dashboard, "You have reached or exceeded this budget.")
        self.assertEqual(sum(map(Decimal, dashboard.context["chart_values"])), dashboard.context["expenses"])

        edit = self.client.post(reverse("transactions:edit", args=[expense.pk]), {
            "transaction_type": "expense", "amount": "210.00", "date": "2026-10-02",
            "description": "Groceries updated", "category": food.pk,
        })
        self.assertEqual(edit.status_code, 302)
        expense.refresh_from_db()
        self.assertEqual(expense.amount, Decimal("210.00"))
        self.assertEqual(expense.description, "Groceries updated")
        self.assertEqual(self.client.get(reverse("transactions:comparison"), {"month_a": "2026-09", "month_b": "2026-10"}).status_code, 200)
        self.assertEqual(self.client.get(reverse("transactions:list"), {"q": "updated", "category": food.pk}).status_code, 200)

        goal_create = self.client.post(reverse("transactions:savings_goal_add"), {
            "name": "Rainy day", "target_amount": "500.00", "target_date": "2027-06-01",
        })
        self.assertEqual(goal_create.status_code, 302)
        goal = SavingsGoal.objects.get(user=user, name="Rainy day")
        contribution = self.client.post(reverse("transactions:savings_goal_contribute", args=[goal.pk]), {
            f"goal-{goal.pk}-amount": "75.00", f"goal-{goal.pk}-date": "2026-10-15", f"goal-{goal.pk}-note": "First deposit",
        })
        self.assertEqual(contribution.status_code, 302)
        self.assertEqual(SavingsContribution.objects.get(goal=goal).amount, Decimal("75.00"))
        self.assertContains(self.client.get(reverse("transactions:savings_goals")), "$75.00 saved")

        self.assertEqual(self.client.get(reverse("transactions:delete", args=[expense.pk])).status_code, 200)
        deleted = self.client.post(reverse("transactions:delete", args=[expense.pk]))
        self.assertEqual(deleted.status_code, 302)
        self.assertFalse(Transaction.objects.filter(pk=expense.pk).exists())
        self.assertEqual(self.client.post(reverse("accounts:logout")).status_code, 302)
        self.assertFalse(self.client.session.get("_auth_user_id"))

    def test_all_authenticated_primary_pages_and_static_assets_are_connected(self):
        user = User.objects.create_user("routes@example.com", name="Routes")
        self.client.force_login(user)
        urls = [
            reverse("transactions:dashboard"), reverse("transactions:comparison"),
            reverse("transactions:list"), reverse("transactions:add"),
            reverse("transactions:categories"), reverse("transactions:budgets"),
            reverse("transactions:recurring_list"), reverse("transactions:recurring_add"),
            reverse("transactions:savings_goals"), reverse("transactions:savings_goal_add"),
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
        dashboard = self.client.get(reverse("transactions:dashboard"))
        self.assertContains(dashboard, reverse("transactions:comparison"))
        self.assertContains(dashboard, reverse("transactions:budgets"))
        self.assertContains(dashboard, "/static/css/fintrack.css")
