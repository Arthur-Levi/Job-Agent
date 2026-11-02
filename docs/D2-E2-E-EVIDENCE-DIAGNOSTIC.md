# D2-E2.E — Evidence-grounded Career Diagnostic (MVP)

Status: **MVP BACKEND PASS / BETA NO-GO**.

**Evidence:** commit `2562f87f8035fa9c4c0895f6fc1a146fa3194cf3`, https://github.com/Arthur-Levi/Job-Agent/actions/runs/41453862021. Backend **304 passed, 3 xfailed, 1 warning**. Six jobs PASS, including disposable real browser/API/PostgreSQL E2E carried over from D2-E2.D.1-D. Diagnostic coverage tests are independent of browser E2E; this commit does **not** add diagnostic React UI.

## API contract

`GET /api/v1/career/diagnostic` — requires authenticated user; no uploads, payments or calls to external LLMs.

- `basis=active_fact_ledger` and `status=preliminary`.
- `coverage[]` has experience, education, project, skill in deterministic order, `documented|not_documented` and `evidence[]` with source fact IDs.
- `review_actions[]` requests confirmation of missing **records** and missing organization/start date for an existing structured experience. It never claims the candidate lacks those skills or experiences.
- `limitations[]` explicitly disclaim external verification, ATS passes, interviews and hiring predictions.
- Read-only: no writes, hallucinated qualifications, generated salary claims or ungrounded scores.
- History entries marked SUPERSEDED and other users' facts must not influence the result.

## Security/acceptance boundaries

- All integration testing must run **only** against a fresh disposable PostgreSQL in GitHub Actions; the fixture can drop the public schema.
- Never expose source excerpts, unencrypted preview tickets or raw CV files in diagnostic output.
- No inference from missing facts beyond a documentation checklist.
- This is an early diagnostic MVP, **not** automated matching, CV creation, LLM recommendations or proof of outcomes.
- The production résumé upload gate `CV_SANDBOX_REQUIRED` remains active; this feature does not authorize real résumés or beta deployment.

## Next enhancements

1. Review actions connected to editable structured fields and candidate confirmation.
2. Explainability for targeted vacancy requirements using evidence references and explicit unknowns, not a fabricated success percentage.
3. Diagnostic React page and candidate usability testing.
4. Hold all production gates until sandbox, privacy and operational review are passed.
