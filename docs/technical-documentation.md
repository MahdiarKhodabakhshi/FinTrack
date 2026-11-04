# FinTrack Technical Documentation (FT-69)

## Runtime and setup

FinTrack uses Python 3.12, Django 5.2, Django templates, SQLite by default, and PostgreSQL through `DATABASE_URL` when deployed. Bootstrap 5.3.8 and Chart.js are stored locally; the application does not require a JavaScript package manager or runtime CDN. The exact local setup and test commands are in the repository [README](../README.md).

The main settings are in `config/settings.py`; URL routing is in `config/urls.py` and `transactions/urls.py`. Account authentication is implemented in `accounts/`. Transactions, categories, budgets, recurrence, calculations and dashboards are implemented in `transactions/`. Shared template tags are in `ui/templatetags/ui.py`.

## Data model

- **User** (`accounts.User`): email is the unique, lowercased login identifier; name, password hash, active/staff flags and Django permissions are stored on the account.
- **Category**: belongs to one user, has a case-insensitive unique name for that user, and may be a protected starter category or the user's single Uncategorized category.
- **Transaction**: belongs to one user and stores income/expense type, positive decimal amount, date, description and optional category. A recurring source is nullable so deleting a recurrence preserves transaction history.
- **RecurringTransaction**: belongs to one user and stores type, amount, description, frequency, start/end dates, next due date, active state and optional expense category. A unique source/date constraint makes generated occurrences idempotent.
- **Budget**: belongs to one user and category, stores a first-of-month date and positive decimal limit, and permits one row per user/category/month.
- **SavingsGoal**: belongs to one user and stores a named positive target and target date. **SavingsContribution** records a positive amount, date and optional note against a goal; progress is aggregated from these records rather than a manually overwritten balance.

Model definitions and constraints are in `transactions/models.py`; schema history is in `accounts/migrations/` and `transactions/migrations/`. The category migration creates private defaults for existing users and preserves uncategorized history. Transaction and recurring forms scope category choices to their owner.

## Financial calculations and security

`transactions/months.py` uses Toronto-local month ranges and decimal aggregation for income, expense, category spending and budget remaining. `transactions/budget_warnings.py` defines 80% and 100% thresholds and checks projected expense totals without blocking a valid transaction. `transactions/comparison.py` aggregates expense totals for each signed-in user's two selected months. `transactions/recurring.py` calculates anchored monthly occurrences and catches up a maximum of 400 occurrences per rule per invocation. `transactions/savings_views.py` sums owner-scoped contribution amounts and displays target progress and dated history.

Authentication uses Django sessions and Argon2 as the preferred password hasher. `LoginRequiredMiddleware` protects views by default, while transaction/category/rule object lookups additionally scope to `request.user`. Financial queryset helpers begin with that user filter. CSV exports are private, uncached, formula-safe and include only filtered owner rows. Production uses secure session/CSRF cookies; HTTPS and deployment static-file serving must be configured by the hosting environment.

## Verification and operations

The built-in Django test suite covers models, forms, access control, calculations, exports, recurrence, warnings, comparisons and an end-to-end account workflow. Run `python manage.py check`, `python manage.py makemigrations --check --dry-run`, `python manage.py test`, then coverage commands from the README before release.

Due recurring entries are created lazily when the transaction history or recurring list is visited. A deployment scheduler should run `python manage.py generate_recurring_transactions` daily. SQLite is suitable for local development; use PostgreSQL for concurrent multi-user deployment because it provides row-level locks for schedule generation.

Deployment requires a production secret key, PostgreSQL URL, HTTPS, static file collection/serving and a hosting service. Gunicorn is the WSGI server and WhiteNoise serves collected static files; configure `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS` and `DJANGO_SECURE_SSL_REDIRECT` for the assigned host. Do not use the example secret in production. Keep environment variables and backups outside Git. See the [deployment checklist](deployment-checklist.md).
