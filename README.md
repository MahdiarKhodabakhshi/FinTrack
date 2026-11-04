# FinTrack

FinTrack is a personal finance web app for a three-person university Scrum project. Users can register, sign in, record income and expenses, manage expense categories and monthly budgets, and review private financial summaries, charts and spending comparisons. Search, filters, recurring entries, CSV export and budget warnings support day-to-day tracking.

| Team member | Scrum role |
| --- | --- |
| Saad Ijaz | Product Owner |
| Tom Croux | Scrum Master |
| Mahdiar Khodabakhshi | Developer |

## Tech stack

Python 3.12, Django 5.2 LTS, Django templates, Argon2, python-dotenv,
dj-database-url, psycopg, SQLite locally, PostgreSQL when deployed,
Django's built-in tests, coverage, GitHub Actions, and vendored Bootstrap 5.3.8.

See [CONTRIBUTING.md](CONTRIBUTING.md) for branching and review rules (FT-01).

## Backend contract for templates

FT-02: `templates/base.html` exposes `title` and `content` blocks, plus shared
`user`, `request`, and `messages` context. All forms use POST with a CSRF token.

### Authentication (FT-07, FT-11, FT-13, FT-14)

| URL name | Path | Template | Context |
| --- | --- | --- | --- |
| `accounts:register` | `/accounts/register/` | `accounts/register.html` | `form`: RegistrationForm with name, email, password1, password2 |
| `accounts:login` | `/accounts/login/` | `accounts/login.html` | `form`: LoginForm with username (label Email) and password; `next`, `site`, `site_name` |
| `accounts:logout` | `/accounts/logout/` | None (POST then redirect) | No page context |

Registration signs the new user in and redirects to `transactions:list` with a
success message. Login respects a safe `next` destination, otherwise it redirects
to `transactions:list`. Already signed-in users skip login and registration.
Logout ends the session and redirects to `accounts:login`; GET returns 405 for a
signed-in user. Passwords use Argon2 and Django's baseline validators.

Registration (FT-05) and login (FT-10) share accessible field rendering and
non-field error alerts (FT-12). The login POST field name stays
`username` even though its label and widget are Email. Render field errors and
`form.non_field_errors`, and retain login's hidden `next` field.
Registration validation (FT-06) and friendly case-insensitive duplicate-email
errors (FT-08) live in `accounts/forms.py`. Feature tests are in
`accounts/tests/test_registration.py` (FT-09) and `accounts/tests/test_login.py`
(FT-15). Security checks remain in `accounts/tests/test_security.py`.

### Transactions (FT-18, FT-21)

| URL name | Path | Template | Context |
| --- | --- | --- | --- |
| `home` | `/` | Redirect | Signed-in users go to the dashboard; signed-out users go to login |
| `transactions:comparison` | `/transactions/compare/` | `transactions/month_comparison.html` | `form`, `month_a`, `month_b`, `comparison_rows`, `total_a`, `total_b`, `total_change`: current user's expense comparison |
| `transactions:savings_goals` | `/transactions/savings/` | `transactions/savings_goal_list.html` | `goals`: owner-scoped targets, saved/remaining amounts, progress and contribution history |
| `transactions:savings_goal_add` | `/transactions/savings/add/` | `transactions/savings_goal_form.html` | `form`: goal name, positive target amount and target date |
| `transactions:savings_goal_contribute` | `/transactions/savings/<pk>/contribute/` | Redirect to goal list | POST-only dated contribution; owner-scoped goal lookup |
| `transactions:list` | `/transactions/` | `transactions/transaction_list.html` | `transactions` and `object_list`: signed-in user's records, ordered by descending date then creation time; `view`, `is_paginated=False`, `paginator=None`, `page_obj=None` |
| `transactions:add` | `/transactions/add/` | `transactions/transaction_form.html` | `form`: TransactionForm with transaction_type, amount, date, description and the current user's categories; `view`, `object=None` |

Both pages require login. A valid
add POST assigns the session user, adds a success message, and redirects to
`transactions:list`. The form never includes `user`; forged ownership is ignored.
Amounts are Decimal values; type is `income` or `expense`. The date widget uses
`type="date"`. Templates share `user`, `request`, and `messages` context.

The form (FT-16), history table (FT-20), and empty-state card (FT-22) share
the frontend conventions below. Input validation (FT-17) is in `transactions/forms.py`.
Feature tests are in `transactions/tests/test_add_transaction.py` (FT-19) and
`transactions/tests/test_history.py` (FT-23); model validators and DB constraints
remain in force.
Mahdiar's ownership tests are in `transactions/tests/test_ownership.py`.
Sprint 2 edit/delete views use `get_user_transaction_or_404(user, pk)`; another
user's record returns 404. Expense forms require one of the signed-in user's
categories. Income transactions do not have a spending category.

### Frontend conventions (FT-04)

New pages extend `base.html` and use an `h1.h3` page title.
Use `{% include "includes/form_field.html" with field=form.email autocomplete="email" only %}`
for fields; optional arguments are `autocomplete`, `autofocus`, `inputmode`,
`placeholder`, and `prefix` (such as `$`). Error/help IDs match Django's ARIA references.
Use `{% include "includes/form_errors.html" with form=form %}` for non-field alerts.
Password help HTML renders directly; do not add `safe` or escape it again.
Load `{% load ui %}` for `field_widget`, `money`, and `nav_active`.
`{% field_widget field autofocus=False aria_label="Email" %}` preserves Django's
widget attributes; `aria_` and `data_` keyword underscores become hyphens.
`{{ transaction.signed_amount|money:"signed" }}` gives `+$1,234.50` or `−$20.00`;
plain `money` omits a positive sign and uses ROUND_HALF_UP to two decimal places.
`{% nav_active request "transactions:list" as active %}` gives `active` for that route;
set `aria-current="page"` only when active.
Brand tokens live in `static/css/fintrack.css`: primary/hover, income/expense,
background/surface, border, and muted text. Bootstrap variables apply the brand.
Bootstrap 5.3.8 CSS, JS, maps, and MIT license are in `static/vendor/bootstrap-5.3.8/`.
Load assets using `{% static %}`; runtime CDN access and a build step are unnecessary.
`extra_head` and `extra_js` are extension blocks for later sprints.
The frontend-only `ui` app owns tags and tests and has no models.

### Search, filters and CSV (FT-48 to FT-52, FT-72)

`transactions:list` accepts optional GET fields `q`, `type`, `category`, `date_from`,
`date_to`, and `sort`. Search is stripped and case-insensitive. Dates are inclusive;
reversed ranges show an error and ignore both dates while retaining valid filters.
Sort values are whitelisted: `newest`, `oldest`, `amount_high`, `amount_low`.
Unknown sorts fall back to newest. The category select contains only the signed-in user's categories.
Additional list context: `filter_form`, `filters_active`, `result_count`,
`has_any_transactions`, `export_query`, and `sort_label`. The empty-history card
is retained; zero filtered results have a separate no-match card.
`transactions:export` is GET `/transactions/export/`, requires login, and accepts
the same filters/sort. It returns CSV with a UTF-8 BOM, Date/Type/Description/Amount
columns, ISO dates, signed plain decimals, and `Cache-Control: no-store`.
Formula-leading descriptions are prefixed with an apostrophe for spreadsheet safety.
Only the signed-in user's rows are queried for display or export.

### Recurring transactions (FT-75, FT-76)

| URL name | Path | Template / context |
| --- | --- | --- |
| `transactions:recurring_list` | `/transactions/recurring/` | `transactions/recurring_list.html`, `rules`: user's schedules |
| `transactions:recurring_add` | `/transactions/recurring/add/` | `transactions/recurring_form.html`, `form`: type, amount, description, frequency, start/end dates |
| `transactions:recurring_toggle` | `/transactions/recurring/<pk>/toggle/` | POST-only pause/resume, then redirect |
| `transactions:recurring_delete` | `/transactions/recurring/<pk>/delete/` | GET `transactions/recurring_confirm_delete.html`, `object`; POST deletes rule |

Rules are user-owned; every object lookup includes the user and returns 404 for
another user's rule. Description is required. Start dates can be at most 366 days
in the past. End dates are inclusive. Weekly, every-two-weeks and monthly rules
are supported. Monthly dates anchor to the original start day: Jan 31 → Feb 28
(or 29) → Mar 31, without drift. The frequency field explains this behaviour.
Due entries are generated when visiting history or recurring rules and immediately
after creating a rule. There is no background worker: without a visit or scheduled
command, entries catch up on the next visit. Each run processes at most 400
occurrences per rule; later runs continue the catch-up. Database uniqueness on
rule/date and atomic row locking prevent duplicate occurrences.
Resume advances to the first scheduled date on or after Toronto-local today,
without paused-period backfill. Expired rules stay ended if Resume is pressed.
Deleting a rule retains generated history, clears its source, and removes its
Recurring badge. `nav_active_prefix` marks all recurring pages active.

For a future deployment scheduler, run daily in the deployed environment:

```bash
python manage.py generate_recurring_transactions
```

The command processes all users and reports the number created. PostgreSQL provides
row locks; SQLite enforces occurrence uniqueness but serializes concurrent writers.
Migration `0002_recurring_transactions` adds the rules, nullable source FK, indexes,
and positive-amount/end-date/occurrence constraints. Existing history is preserved.

### Categories, budgets and dashboard (Sprint 2, FT-24 to FT-43)

| URL name | Path | Page and purpose |
| --- | --- | --- |
| `transactions:dashboard` | `/transactions/dashboard/` | `transactions/dashboard.html`: month selector, income, expenses, net cash flow and category budget rows |
| `transactions:categories` | `/transactions/categories/` | `transactions/category_list.html`: starter and custom categories |
| `transactions:category_add` | `/transactions/categories/add/` | POST adds a custom category; errors render on the category page |
| `transactions:category_edit` | `/transactions/categories/<pk>/edit/` | `transactions/category_form.html`: rename a custom category |
| `transactions:category_delete` | `/transactions/categories/<pk>/delete/` | `transactions/category_confirm_delete.html`: GET confirmation, POST removal |
| `transactions:budgets` | `/transactions/budgets/` | `transactions/budget_list.html`: set/update a category limit and view spent/remaining amounts |
| `transactions:edit` | `/transactions/<pk>/edit/` | `transactions/transaction_form.html`: prefilled, owner-only transaction edit |
| `transactions:delete` | `/transactions/<pk>/delete/` | `transactions/transaction_confirm_delete.html`: GET confirmation, POST deletion |

Each account receives Food, Housing, Transport, Utilities, Health, Personal,
Entertainment, and a protected Uncategorized category. Migration `0003` creates
these for existing accounts and assigns their uncategorized expenses. Category and
budget forms only accept records owned by the signed-in user. Deleting a custom
category moves its transactions and recurring rules to that user's Uncategorized
category; its monthly budgets are removed and the confirmation page says so.
System categories cannot be renamed or deleted.

`Transaction.category` is nullable because income has no category; expense forms
require a category. Recurring expense forms can choose a category, and generated
transactions inherit it. Older rules without one use Uncategorized. Category names
are unique per user without regard to case. Budgets store the first day of the month
as `month_start`, with one positive amount per user/category/month. Spending counts
only that user's expenses dated from the month's first day up to (but not including)
the next month. Remaining is budget minus spending and can be negative.

The dashboard defaults to the Toronto-local current month. Its GET `month` value is
`YYYY-MM`; malformed values show a field error while safely displaying the current
month. Summary calculations use Decimal aggregation and never mix accounts. The
signed-in home route redirects to the dashboard; login and registration continue
to send users to transaction history. Category, budget, dashboard and transaction
management tests live in `transactions/tests/test_sprint2_*.py`.

## Setup (FT-02)

Install Python **3.12** and Git first. On Debian/Ubuntu Linux, also install the
`python3.12-venv` package if virtual environment creation reports missing ensurepip.

### macOS / Linux

```bash
git clone https://github.com/MahdiarKhodabakhshi/FinTrack.git
cd FinTrack
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Windows (PowerShell)

```powershell
git clone https://github.com/MahdiarKhodabakhshi/FinTrack.git
cd FinTrack
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

If PowerShell blocks activation, allow scripts for the current session with
`Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`, then activate again.
Open <http://127.0.0.1:8000/>. The superuser prompt asks for email, name, and password.
Stop the development server with Ctrl+C.

`.env` is local and ignored. `DJANGO_DEBUG` defaults to False; without a secret key,
non-debug startup fails intentionally. The supplied values are development-only.
`DJANGO_ALLOWED_HOSTS` is comma-separated. Leave `DATABASE_URL` unset to use
SQLite; set it to a PostgreSQL connection URL when deployed. Cookies require HTTPS
when debug is off. All dates use America/Toronto, with timezone-aware timestamps.
Never deploy using the example secret.

## Tests and coverage (FT-02, FT-03)

With the virtual environment active and `.env` copied:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
coverage run manage.py test
coverage report
```

Optional: `coverage html` creates the ignored `htmlcov/` report.
CI runs these checks on Python 3.12 with non-debug settings. The required GitHub
check is the `test` job in the `CI` workflow.

Model tests are in `accounts/tests/test_models.py` and
`transactions/tests/test_models.py`; registration, login/logout, transaction entry,
history, search/export, recurring transactions and Sprint 2 workflows have dedicated
feature tests. Model tests cover lowercase email
identity, superuser flags, transaction ordering, positive amounts, signed amounts,
and cascading deletion (FT-03).


### Sprint 1 validation and acceptance tests (FT-06, FT-08, FT-09, FT-15, FT-17, FT-19, FT-23)

Registration normalizes emails to lowercase and checks format using Django's
EmailField. Django's configured password validators check length, common passwords,
numeric-only passwords and similarity to user data; BaseUserCreationForm checks
matching passwords. Required names remain limited to 150 characters.
Existing email case variants show "An account with this email already exists."
on the email field. A database uniqueness collision after validation shows the same
message; unrelated database failures are not hidden. Password hashing and login
session handling continue through Django's built-in APIs.
Transaction type, amount and date are required. Amounts must be positive, fit the
12-digit/two-decimal model field, and pass its validators. DateField validates calendar
dates, including leap years. Description is optional and limited to 255 characters.
Future transaction dates are allowed; Sprint 1 has no rule banning them.
All validation errors use the existing accessible template partials automatically.
The four feature suites cover successful saves, invalid input, duplicate/racing
registrations, safe redirects, CSRF, logout, user isolation, ordering and HTML escaping.

Sprint 1 (FT-01 to FT-23), pulled-forward search/export (FT-48 to FT-52 and FT-72),
and recurring transactions (FT-75 to FT-76) are merged into `main`.

## Sprint 3: warnings, charts and responsive dashboard (FT-44 to FT-58)

Monthly budget warnings use 80% and 100% thresholds. New expenses are never blocked;
an expense that would exceed its category's budget is saved and followed by a warning.
The dashboard chart uses locally vendored Chart.js and sums category expenses for
the selected month; its values are tested against the expense summary. Search,
category/type/date filters and whitelisted sorting apply to both history and CSV.
Mobile styles keep tables inside scrollable regions and stack dashboard controls.
Budget thresholds and projection checks live in `transactions/budget_warnings.py`.
The dashboard supplies chart labels and Decimal strings to `static/js/dashboard.js`;
the Chart.js UMD bundle and MIT license are under `static/vendor/chart.js-4.5.1/`.
Months without expenses render a textual empty state instead of a blank chart.

## Sprint 4: month comparison and release quality (FT-59 to FT-69)

The comparison page reports each user's expense totals by category across two
selected months, plus the change and overall totals. The full built-in test suite
includes a registration-to-budget end-to-end workflow and cross-account access
checks. See the [User Guide](docs/user-guide.md) and
[Technical Documentation](docs/technical-documentation.md) for use and architecture.

The unassigned savings-goal backlog (FT-73, FT-74) is also implemented. Users can
create a named target with an amount and date, then record dated contributions.
Progress is calculated from contribution records, capped visually at 100%, while
the full amount and contribution history remain visible. Goals and contributions
are private to the goal owner.

## Release preparation (FT-70 to FT-71)

The project is prepared for deployment through Django's production settings and
environment variables, but its hosting service, production database, domain and
credentials must be supplied before a live deployment can be completed. The
offline [final presentation](docs/final-presentation.html) and
[live demo runbook](docs/live-demo.md) are included for the release walkthrough.
Follow the [deployment checklist](docs/deployment-checklist.md) after the host is
selected; no public service or paid resource has been created from this repository.
