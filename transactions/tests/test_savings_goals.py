# FT-73, FT-74: Goal creation, owner privacy and contribution-driven progress.
from datetime import date
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from transactions.models import SavingsContribution, SavingsGoal


class SavingsGoalTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("saver@example.com", name="Saver")
        self.other = User.objects.create_user("other-saver@example.com", name="Other Saver")
        self.client.force_login(self.user)

    def create_goal(self, **overrides):
        data = {"name": "Emergency fund", "target_amount": "1000.00", "target_date": "2027-06-01"}
        data.update(overrides)
        return self.client.post(reverse("transactions:savings_goal_add"), data)

    def contribute(self, goal, **overrides):
        data = {f"goal-{goal.pk}-amount": "150.00", f"goal-{goal.pk}-date": "2026-11-04", f"goal-{goal.pk}-note": "Monthly savings"}
        data.update(overrides)
        return self.client.post(reverse("transactions:savings_goal_contribute", args=[goal.pk]), data)

    def test_goal_creation_assigns_the_signed_in_owner(self):
        response = self.create_goal(name="  Trip fund  ")
        self.assertRedirects(response, reverse("transactions:savings_goals"), fetch_redirect_response=False)
        goal = SavingsGoal.objects.get(name="Trip fund")
        self.assertEqual(goal.user, self.user)
        self.assertEqual(goal.target_amount, Decimal("1000.00"))
        self.assertEqual(goal.target_date, date(2027, 6, 1))
        page = self.client.get(reverse("transactions:savings_goal_add"))
        self.assertContains(page, '>Savings goals</a>')
        self.assertContains(page, 'aria-current="page"')

    def test_contributions_update_progress_and_show_auditable_history(self):
        goal = SavingsGoal.objects.create(user=self.user, name="Emergency fund", target_amount="1000.00", target_date=date(2027, 6, 1))
        self.assertEqual(self.contribute(goal).status_code, 302)
        self.contribute(goal, **{f"goal-{goal.pk}-amount": "25.50", f"goal-{goal.pk}-note": "Extra deposit"})
        response = self.client.get(reverse("transactions:savings_goals"))
        rendered_goal = response.context["goals"][0]
        self.assertEqual(rendered_goal.saved_amount, Decimal("175.50"))
        self.assertEqual(rendered_goal.remaining_amount, Decimal("824.50"))
        self.assertEqual(rendered_goal.progress_percent, 17)
        self.assertContains(response, "17% saved")
        self.assertContains(response, "$175.50 saved")
        self.assertContains(response, "Monthly savings")
        self.assertContains(response, "Extra deposit")

    def test_progress_caps_at_complete_without_losing_over_target_contributions(self):
        goal = SavingsGoal.objects.create(user=self.user, name="Laptop", target_amount="500.00", target_date=date(2027, 1, 1))
        self.contribute(goal, **{f"goal-{goal.pk}-amount": "600.00"})
        response = self.client.get(reverse("transactions:savings_goals"))
        row = response.context["goals"][0]
        self.assertTrue(row.is_complete)
        self.assertEqual(row.progress_percent, 100)
        self.assertEqual(row.remaining_amount, Decimal("0.00"))
        self.assertContains(response, "Goal reached")
        self.assertContains(response, "$600.00 saved")

    def test_goal_and_contribution_forms_reject_nonpositive_amounts(self):
        response = self.create_goal(target_amount="0")
        self.assertEqual(response.status_code, 200)
        self.assertIn("target_amount", response.context["form"].errors)
        goal = SavingsGoal.objects.create(user=self.user, name="Bike", target_amount="800.00", target_date=date(2027, 1, 1))
        response = self.contribute(goal, **{f"goal-{goal.pk}-amount": "0"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("amount", response.context["goals"][0].contribution_form.errors)
        self.assertFalse(SavingsContribution.objects.filter(goal=goal).exists())

    def test_user_cannot_read_another_users_goals_or_contribute_to_them(self):
        private_goal = SavingsGoal.objects.create(user=self.user, name="Private goal marker", target_amount="400.00", target_date=date(2027, 1, 1))
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get(reverse("transactions:savings_goals")), "Private goal marker")
        self.assertEqual(self.contribute(private_goal).status_code, 404)
        self.assertFalse(SavingsContribution.objects.filter(goal=private_goal).exists())

    def test_signed_out_pages_redirect_and_contribution_is_post_only(self):
        goal = SavingsGoal.objects.create(user=self.user, name="Travel", target_amount="900.00", target_date=date(2027, 1, 1))
        self.assertEqual(self.client.get(reverse("transactions:savings_goal_contribute", args=[goal.pk])).status_code, 405)
        self.client.logout()
        for url in (reverse("transactions:savings_goals"), reverse("transactions:savings_goal_add")):
            self.assertRedirects(self.client.get(url), reverse("accounts:login") + f"?next={url}")

    def test_database_rejects_nonpositive_goal_target(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            SavingsGoal.objects.create(user=self.user, name="Invalid", target_amount="0.00", target_date=date(2027, 1, 1))
