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

FT-02: The shared template is `templates/base.html`, with `title` and `content`
blocks and Django's `user` and `messages` context. Authentication and transaction
URL contracts will be added in Phases 2 and 3.
