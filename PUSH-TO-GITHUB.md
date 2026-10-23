# GitHub upload — Job Agent v12.5

Repository: https://github.com/Arthur-Levi/Job-Agent

The repository is public. Review source and examples before publication. Never commit .env, tokens, production database dumps or customer resumes.

## Recommended safe workflow

1. Clone the existing repository, preserving its history:

```bash
git clone https://github.com/Arthur-Levi/Job-Agent.git
cd Job-Agent
git switch -c release/v12.5-postgres-homologation
```

2. Copy the **contents** of this `job-agent/` directory into the cloned `Job-Agent/` directory (not a nested `job-agent/`). Review changes:

```bash
git status --short
git diff --stat
git diff --check
```

3. Confirm secrets are not staged and publish the review branch:

```bash
git add -A
git diff --cached --name-only
git diff --cached --check
git commit -m "chore: prepare Job Agent v12.5 for PostgreSQL homologation"
git push -u origin release/v12.5-postgres-homologation
```

4. Open a Pull Request into `main` and keep it unmerged until release gates pass.

## PostgreSQL staging gate

Provision a disposable PostgreSQL 16 instance with a dedicated user and database. Set DATABASE_URL to a staging database only; never paste credentials into a chat, issue or commit.

```bash
cd production_api
python -m pip install -r requirements.txt
export APP_ENV=staging
export DATABASE_URL='postgresql+psycopg://USER:PASSWORD@HOST:5432/job_agent_staging'
unset ALLOW_TEST_SQLITE
bash run-release-gate.sh
```

Expected: `POSTGRES_SCHEMA_PASS` and successful tests. Do not report approval until actually run against PostgreSQL.
