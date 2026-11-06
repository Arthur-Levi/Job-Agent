# D2-E2.F.2 — explanatory matching for owned saved jobs

**Implementation scope:** additive, read-only integration of the EXISTING `/api/v1/career/vacancy-match` Fact Ledger engine with the existing `Job` and `JobRequirement` records.

## Audit

The existing `app.services.vacancy_matching.vacancy_match` already implements exact textual classification of active user-owned `CareerFact` entries, returning per-requirement evidence IDs, explanations, next steps, and the categories `documented_match`, `not_documented` and `explicit_incompatibility` (the last limited to explicit work-mode conflicts). It explicitly **does not** issue ATS scores, estimate hire probability, infer skills, or imply undocumented equals unqualified. Existing `JobMatch` is a persistence model, not proof of an algorithm. Rewriting the matching engine would add unnecessary inconsistency.

The missing integration was user-owned **saved** jobs with structured requirements. Added `app.services.saved_job_matching.explain_saved_job`, and authenticated `POST /api/v1/jobs/{job_id}/explain` endpoint. It validates the job's `user_id` in the query **before** reading its requirements; a non-owned or missing job returns the same `JOB_NOT_FOUND`. Explicit requirements with categories skill/experience/education/project/work_mode are converted to existing `VacancyMatchRequest` and dispatched unchanged to `vacancy_match`. `MUST_HAVE` maps to `required`, `IMPORTANT` and `NICE_TO_HAVE` to `preferred`. No data is inserted/updated, and no new migrations or scoring rules are introduced.

## Fail-closed limits

- A saved job without structured requirements cannot be scored or explained until a candidate has entered/reviewed those requirements.
- Requirements with unknown importance/category, invalid modes, duplicates or lengths beyond 20 are rejected for human review (422), not guessed from free-form description.
- This endpoint **does not automatically parse job descriptions** or scrape vacancies.
- It does not validate employer-supplied requirements, issue automated rejections, reveal other users' data, or replace human decisions.
- It does not trigger CV import or relax `503 CV_SANDBOX_REQUIRED`.
- The React UI for editing/reviewing saved-job structured requirements is a subsequent integration task. No claim that the complete F2 frontend or beta acceptance is finished.

## Verification

```bash
cd /workspaces/Job-Agent-SEC-OPS-01
git fetch origin
git pull --ff-only origin feature/sec-ops-01-broker-isolation
source backend/.venv-f124/bin/activate
cd backend
python -m pytest tests/unit/test_saved_job_matching.py -v
python -m ruff check .
python -m ruff format --check .
python -m mypy
git status --short --branch
```

**Operational status:** SEC/OPS Gate 1 remains NO-GO; the F124D.1 VM acceptance is deferred, not waived. No real CVs permitted.


## CI result — 2026-11-05

Implementation commit `93ddebf059654ccb99552b8a9d3bf6520f6d3a62` validated by [GitHub Actions run #42137147093](https://github.com/Arthur-Levi/Job-Agent/actions/runs/42137147093): backend **SUCCESS** — **512 passed, 21 skipped, 3 xfailed, 1 warning**, including 11 new saved-job matching unit cases. Ruff lint PASS, Ruff format PASS (184 files), MyPy strict PASS (174 source files). Audit, frontend, sandbox-smoke and browser-smoke SUCCESS. Real-browser-postgres-e2e was in progress when the record was made.

**Result does not certify real-tenant / real-candidate beta, or a React edit-and-review UX.** F124D.1 operational isolation remains deferred NO-GO; CV upload remains blocked.
