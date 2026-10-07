# FinTrack

FinTrack is a personal finance web app for a three-person university Scrum project. Sprint 1 lets users register, sign in, record income and expenses, and view their own transaction history. Later sprints add categories, budgets, a dashboard and charts.

| Team member | Scrum role |
| --- | --- |
| Saad Ijaz | Product Owner |
| Tom Croux | Scrum Master |
| Mahdiar Khodabakhshi | Developer |

## Tech stack

Python 3.12, Django 5.2 LTS, Django templates, Argon2, python-dotenv,
dj-database-url, psycopg, SQLite locally, PostgreSQL when deployed,
Django's built-in tests, coverage, and GitHub Actions. Saad adds Bootstrap 5 later.

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

Saad owns the unstyled registration (FT-05) and login (FT-10) placeholders and
styles `form.non_field_errors` for FT-12. The login POST field name stays
`username` even though its label and widget are Email. Render field errors and
`form.non_field_errors`, and retain login's hidden `next` field.
Tom adds FT-06 and FT-08 rules at the markers in `accounts/forms.py`, and owns
`accounts/tests/test_registration.py` (FT-09) and `accounts/tests/test_login.py`
(FT-15). Mahdiar's security checks are in `accounts/tests/test_security.py`.
The transaction contract arrives in the independent Phase 3 PR.

### Transactions (FT-18, FT-21)

| URL name | Path | Template | Context |
| --- | --- | --- | --- |
| `transactions:list` | `/transactions/` | `transactions/transaction_list.html` | `transactions` and `object_list`: signed-in user's records, ordered by descending date then creation time; `view`, `is_paginated=False`, `paginator=None`, `page_obj=None` |
| `transactions:add` | `/transactions/add/` | `transactions/transaction_form.html` | `form`: TransactionForm with transaction_type, amount, date, description; `view`, `object=None` |

Both pages require login, even before the authentication PR is merged. A valid
add POST assigns the session user, adds a success message, and redirects to
`transactions:list`. The form never includes `user`; forged ownership is ignored.
Amounts are Decimal values; type is `income` or `expense`. The date widget uses
`type="date"`. Templates share `user`, `request`, and `messages` context.

Saad replaces the unstyled form (FT-16), history table (FT-20), and marked empty
row (FT-22). Tom adds FT-17 validation at the marker in `transactions/forms.py`
and owns `transactions/tests/test_add_transaction.py` (FT-19) and
`transactions/tests/test_history.py` (FT-23). Model validation remains the baseline.
Mahdiar's ownership tests are in `transactions/tests/test_ownership.py`.
Sprint 2 edit/delete views (FT-24 to FT-27) must use
`get_user_transaction_or_404(user, pk)`; another user's record returns 404.

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

Phase 1 supplies login/register page placeholders and protected transaction route
placeholders. Authentication and transaction forms arrive through separate Phase 2
and Phase 3 PRs. No functional registration or transaction entry exists yet.

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

Mahdiar owns `accounts/tests/test_models.py` and
`transactions/tests/test_models.py`; Tom will add the registration, login,
add-transaction and history feature test files. Model tests cover lowercase email
identity, superuser flags, transaction ordering, positive amounts, signed amounts,
and cascading deletion (FT-03).
