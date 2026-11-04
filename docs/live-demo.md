# FinTrack live demo runbook (FT-71)

## Before presenting

- Run `python manage.py migrate` and `python manage.py check` on the demo environment.
- Create a demo account with a password that is not used anywhere else.
- Add a Food budget for the current month, then add one income and several expenses across at least two categories. Keep one expense below 80% and one that crosses a budget threshold.
- Add a recurring rule with a due date on or before today, and confirm its generated entry is visible.
- Check that the dashboard chart, month comparison, transaction filters and CSV export show the same records as the history.
- Open a private browser window and verify that a signed-out user sees the login page.
- Keep a second browser window signed into another account if demonstrating data isolation.

## Five-minute walkthrough

1. **Account and privacy:** show the sign-in page, sign in as the demo user, and point out that the navigation is account-specific.
2. **Transactions:** add a small expense with a category, then show it at the top of history. Search for it, filter by category/type, and show the date/sort controls.
3. **Budget feedback:** open the dashboard. Show income, expenses and net cash flow; point to category totals, the chart, and an 80%/100% warning. Show that an over-budget expense is recorded with a warning rather than rejected.
4. **Planning:** open Compare months and choose two months with different category spending. Explain that the table shows category and overall changes.
5. **Goals and automation:** record a contribution on a savings goal and show the updated progress. Open Recurring to show an automatically generated entry and the recurring badge.
6. **Export and access control:** export the current history filter to CSV and note that it includes only matching owner rows. Sign out; optionally open the second account and show its independent categories and empty/private history.

## Recovery notes

If the demo database is empty, create the demo data before the session rather than spending presentation time entering many records. If a recurring entry is not due yet, use a rule whose next due date is today or earlier; visiting the history or recurring page runs the catch-up. Do not display a real account, password, secret key or personal CSV during the presentation.
