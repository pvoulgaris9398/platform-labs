# AWS Developer Platform

Proof-of-concept internal developer portal specified in
`../.kiro/specs/aws-developer-platform/`.

## Local development

Run repository commands from Git Bash unless a section explicitly says otherwise.

```bash
python -m venv .venv
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

On Windows, pnpm does not need to be installed globally. With Node.js 22+ and npm available, run
frontend commands through `npx`:

```bash
cd frontend
npx --yes pnpm@latest-11 install
npx --yes pnpm@latest-11 dev
```

For a longer Git Bash session, define a convenience function:

```bash
pnpmw() { npx --yes pnpm@latest-11 "$@"; }
pnpmw install
pnpmw test
```

The default database is SQLite for local development. Set `DATABASE_URL` to an async PostgreSQL URL
in deployed environments. External AWS, GitHub, and Terraform Cloud integrations are represented by
injectable clients and are never invoked unless configured.

Run backend checks with `ruff check .`, `ruff format --check .`, and `pytest`. The frontend lives in
`frontend/`; install its dependencies and run `npm test` or `npm run build` there. Terraform code is
under `terraform/` and must be planned and reviewed before any apply.
