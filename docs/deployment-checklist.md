# Deployment checklist (FT-70)

The application is production-capable but still needs a hosting account, a persistent PostgreSQL database, a public hostname and deployment credentials. Keep all secrets in the host's environment-variable store; do not place `.env` or database credentials in Git.

## Host requirements

- Python 3.12 and a web-process command equivalent to `gunicorn config.wsgi:application`.
- A persistent PostgreSQL database exposed as `DATABASE_URL`.
- HTTPS termination at the host's reverse proxy and the original scheme forwarded as `X-Forwarded-Proto: https`.
- A persistent environment-variable store and an automated, recoverable database backup plan.
- A daily scheduler for `python manage.py generate_recurring_transactions`.

## Production environment

Set the following values in the hosting dashboard:

```text
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=<host-generated random secret>
DJANGO_ALLOWED_HOSTS=<the assigned public host name>
DJANGO_CSRF_TRUSTED_ORIGINS=https://<the assigned public host name>
DJANGO_SECURE_SSL_REDIRECT=True
DJANGO_SECURE_HSTS_SECONDS=0
DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=False
DJANGO_SECURE_HSTS_PRELOAD=False
DATABASE_URL=<private PostgreSQL connection URL>
```

After HTTPS and the hostname have been verified, set `DJANGO_SECURE_HSTS_SECONDS` to a deliberate positive value. Do not enable HSTS before confirming HTTPS. Enable `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS` only when every affected subdomain is HTTPS-only. HSTS preload is a separate, difficult-to-reverse browser policy; enable it only after verifying preload requirements and explicitly choosing that policy. Configure automated database backups and verify a restore before storing real user data.

## Release sequence

1. Connect the GitHub repository and set the production environment values.
2. Install dependencies from `requirements.txt`.
3. Run `python manage.py check --deploy`, review every deployment warning and set only the security policies that match the verified host/domain configuration.
4. Run `python manage.py migrate` as a release/pre-deploy command, then `python manage.py collectstatic --no-input` during build.
5. Start `python -m gunicorn config.wsgi:application` and verify the login page, static CSS/JS, registration, database writes and HTTPS redirects.
6. Create the admin account through a protected host shell; never hard-code credentials.
7. Configure the daily recurrence command, backups, error monitoring and a rollback path.
8. Complete a smoke test and record the public URL in the presentation materials.

Render is one supported option. Its [Django deployment guide](https://render.com/docs/deploy-django) describes PostgreSQL, WhiteNoise, a build command and a Blueprint workflow. Render's [free service limitations](https://render.com/docs/free) state that free Postgres databases expire after 30 days, so they are suitable for a temporary demo only and must not hold data that needs to persist. The actual service and database should be created only after the project owner chooses a host and accepts its cost and data-retention terms.
