# D2-A — Backend regression: 72 PASS

**Date:** 2026-10-31
**Branch:** `test/sec05-stripe-prebeta`
**Status:** PASS reported by operator; backend regression only.

## Command/context
Operator ran the broad backend pytest suite while excluding the three SEC05 PostgreSQL-specific tests, using a test SQLite environment. The previous command was:
```bash
python -m pytest tests/ \
  --ignore=tests/test_sec05_postgres_live.py \
  --ignore=tests/test_sec05_postgres_race.py \
  --ignore=tests/test_sec05_stripe_sdk_signed.py \
  -v --tb=short
```

## Terminal evidence
```text
72 passed, 2 warnings in 18.74s
```

Two warnings were reported:
1. StarletteDeprecationWarning from FastAPI TestClient concerning httpx.
2. DeprecationWarning concerning `data=` when uploading raw content in `tests/test_production.py::test_webhook_requires_config`.

The report includes passing tests of authentication, account lifecycle, user isolation, resume ingestion, import preview, deduplication, profile/ledger, diagnostics, technical assessment, security, checkout gates and other APIs.

## What this does NOT prove
- No frontend TypeScript typecheck, lint, vitest or Vite production build result has been provided yet.
- No full browser journey evidence from first login to human-usable job guidance; D2-B remains pending.
- The three PostgreSQL-specific finance tests were deliberately excluded; they have separate prior evidence and were not rerun here.
- No test Stripe live account or Stripe Test Mode checkout; FC06B–D still deferred.
- A green pytest suite does not prove extraction accuracy on diverse real CVs nor customer willingness to pay.

## Next acceptance gates
1. **D2-A frontend:** `npm ci` with existing lockfile; `npm run typecheck`, `npm run lint`, `npm run test`, `npm run build`. Capture each exit result.
2. **D2-B journey:** new isolated end-to-end API tests: register/login -> CV preview -> manual confirm -> profile/ledger persistence -> job requirements -> grounded diagnostic -> grounded resume -> logout/login -> separate-user isolation.
3. **D2-C:** adversarial CV corpus and review UX, distinct experiences/dates, near-duplicate and conflicting facts, no fabrication.
4. Pilot actual user value with consent before paid release.

## Isolation
No `main` merge, PR #2 merge, original DB or original worktree modifications. Stripe Test Mode intentionally paused.
