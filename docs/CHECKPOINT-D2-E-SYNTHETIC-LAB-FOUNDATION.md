# CHECKPOINT D2-E — Laboratório de dez candidatos sintéticos: base implementada
Date: 2026-10-31
Branch: `test/sec05-stripe-prebeta`
Status: DATASET + SELF-CHECK TESTS COMMITTED; EXECUTION NOT YET VERIFIED

## Goal
E1-E6 will be accepted only when 10 distinct synthetic candidate accounts complete the same unified React + FastAPI + PostgreSQL career journey without data leakage, unsupported claims, or unreviewed imports.

## What was delivered to GitHub
- `backend/tests/acceptance/d2e_personas.json`: 10 distinct fictional candidates P01–P10, target jobs, source resume information, mentioned skills, gaps to investigate, and explicit review guardrails.
- `backend/tests/acceptance/test_d2e_persona_corpus.py`: 5 Python tests for uniqueness of identities, diversity of cases/formats, gap-to-job traceability, adversarial controls, bounded dates.
- Adversarial cases: P03 three roles for same employer; P05 school project without employment; P09 conflicting date; P10 bilingual source.
- No real CVs, passwords, or personally identifying data.

## Precise execution state
- Tests in the new acceptance directory are **authored but not yet executed in the user's Codespaces**. Do not call them PASS until the operator runs them.
- E1 real registration/login/session and cross-account isolation **NOT IMPLEMENTED** in `backend/app` (currently default local identity).
- E2 CV upload/review, E3 Fact Ledger, E4 diagnostic, E5 grounded resume are present in `production_api` but **NOT integrated into the canonical React /api/v1 backend**.
- E6 full real-browser journey **NOT IMPLEMENTED / NOT HOMOLOGATED**.
- Existing previously reported passes: production_api 72, frontend 68, backend unit/API 110, backend PostgreSQL integration 98, live React contract 5; sum 353 from distinct test executions.

## Run synthetic corpus tests (no DB)
```bash
cd /workspaces/Job-Agent-SEC05
git fetch origin test/sec05-stripe-prebeta
git merge --ff-only origin/test/sec05-stripe-prebeta
cd backend
.venv/bin/python -m pytest tests/acceptance/test_d2e_persona_corpus.py -v --tb=short
```
The test suite only validates the corpus, not E1-E6 business behavior.

## E1 implementation acceptance (NEXT)
1. Decide unified auth architecture and document how to migrate identity from D1 default local user. No default identity in publicly accessible environment.
2. Add user credentials/session models, collision-resistant hashed tokens, secure password hashing, expiration/revocation, configuration and migrations to `backend/app`, avoiding schema conflict with `production_api`.
3. Add API auth routes register/login/logout/me, update `get_current_user` for token-based identity, and update frontend auth flow.
4. Convert existing backend tests that depend on default user to explicit isolated test identity or test-only override, preserving D1 suite.
5. Add E1 integration coverage for all 10 accounts, wrong password, token isolation, expiration/logout and pairwise cross-tenant ownership for profile/job/application. Run only on dedicated disposable React PostgreSQL after guarded identity check.
6. Then proceed to E2 CV import preview and confirmation with real ownership, E3 fact provenance, E4 grounded recommendations, E5 resume, E6 full UI acceptance and pilot.

## Safety
Do not run `backend/tests/integration` on original/SEC05 databases: fixtures issue `DROP SCHEMA public CASCADE`. Dedicated React test DB on 127.0.0.1:55435 only after exact identity validation. Preserve main, PR #2, worktree original, all original volumes. No Stripe live / no production launch approval.

## Stop condition and next checkpoint
The present checkpoint is a useful completed **foundation milestone**, not completion of E1-E6. Next checkpoint should require tested real authentication and 10 isolated accounts; do not label E1 PASS early.
