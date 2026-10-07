# Contributing — FT-01

`main` always works. Phase 1 initializes this empty repository directly on `main`;
once protection is enabled, nobody commits to it directly.

Use branches named `feature/FT-NN-short-name` or `fix/FT-NN-short-name`.
Commit messages start with the task ID, for example `FT-11: Add session-based login view`.
Every change requires a pull request, passing CI, and one approving review from
another team member. Never merge your own backend PR: Saad or Tom reviews it.
Merge using **Create a merge commit** so everyone's commits stay visible.
Never force-push, rewrite pushed history, or change commit dates.

Run `python manage.py test` before opening a PR. Include migrations when models
change. Never commit secrets, `.env`, local databases, or virtual environments.
Keep each change within your assigned tasks; template styling belongs to Saad,
and custom validation and feature tests belong to Tom.
