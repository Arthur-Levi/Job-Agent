# D2-E — Multi-persona synthetic user acceptance lab
Date: 2026-10-31
Branch: test/sec05-stripe-prebeta
Status: TEST DESIGN, not executed or PASS

## Objective
Validate D2-E1 through D2-E6 as a single multi-tenant customer journey with multiple **synthetic** users, distinct professional histories, goals, source CV documents, conflicting facts and expected results. Synthetic fixtures and predetermined oracles; no personal data or false claims.

## Ten personas / fixture identities (fictional)
- P01 Lucas: 18, administrative apprentice, Excel/Power BI, seeking first full-time job.
- P02 Mariana: 22, junior developer, Python/React/PostgreSQL projects but little formal employment.
- P03 Roberto: 39, logistics supervisor, three sequential jobs at same employer; cannot merge distinct roles.
- P04 Camila: 30, teacher transitioning to data analysis; transferable skills vs gaps.
- P05 Gabriel: 17, first job, no formal employment; no fabricated jobs. Minor's test data entirely synthetic, no real minor user recruitment.
- P06 Fernanda: 27, financial analyst, reports and reconciliations; declared versus demonstrated proficiency.
- P07 André: 25, freelancer with irregular resume headings/dates; uncertain attributes stay uncertain.
- P08 Patrícia: 42, returning to workforce with gap; don't stigmatize or infer cause.
- P09 Rafael: 24, duplicated roles and contradictory dates across versions; flag rather than resolve automatically.
- P10 Beatriz: 29, bilingual IT support, Portuguese and English sections; preserve meaning and source.

## D2-E1 — Identity and isolation
- Implement one real auth/session/identity model in canonical React backend; default local-user resolver is development-only.
- For ALL 10 identities: register, duplicate rejection, login, invalid login, logout/session revocation, persistence, ownership across profile/jobs/career facts.
- Pairwise attempts to access another tenant's resources (10x9 ordered pairs x representative resource types); must reject unauthorized access with no leakage.
- Also test session expiration, changed password, rate limit and no uncontrolled public default-user fallback.
- Gate E1: all 10 users isolated and no horizontal privilege escalation, including after restarts.

## D2-E2 — Resume ingestion and review
- Produce corresponding synthetic PDF(text), DOCX and TXT; table formats, multiple jobs, languages, edge cases.
- Each input has gold-standard structured annotations: organizations, roles, date ranges, projects, education, skills mentioned, omissions.
- Test upload limits, malformed/oversized/scanned files (controlled error), preview and mandatory user correction before commit.
- Gate E2: zero invented facts; no silent merging of roles; every ambiguous field flagged; correct reconstruction of essential fields after user review. Distinguish import draft from verified facts.

## D2-E3 — Master Profile/Fact Ledger
- User-approved import creates exact owned records with explicit source links and USER_DECLARED status.
- Reimport same data -> no duplicate rows. Similar but not identical -> review queue.
- Correct a fact -> supersedes previous, history retained; detect date/source contradictions.
- Restart/login persistence, cross-user isolation.
- Gate E3: no lost facts, no wrong-user sources, no reactivation of superseded facts.

## D2-E4 — Diagnostic and matching
- Each persona receives one or more distinct synthetic job requirements with known supported/unknown/absent evidence.
- Ground every item in fact or explain missing support. Do not classify a skill mention as verified competence.
- Compare personalized output: different personas must receive evidence-specific recommendations, not one generic recommendation list.
- Gate E4: no invented hiring probability; no untraceable factual assertions; useful prioritized action per persona and gap coverage.

## D2-E5 — Professional resume
- Render draft targeted to real fixture job, only active facts selected and owned by candidate, no invented dates/employers/results.
- Human review/edit and export formatting are separate acceptance items.
- Gate E5: 0 unsupported claims, no cross-tenant facts, no superseded facts, professional readable layout in supported file output.

## D2-E6 — Browser E2E and value testing
- Full React journey: register -> login -> upload -> preview -> human confirmation -> master profile -> job -> diagnostic -> tailored resume -> logout/relogin.
- Desktop/mobile, empty/loading/errors, keyboard and accessibility, persistence and user ownership.
- Automation tool may use Playwright when added and configured in separate fixtures, but no claim that it currently exists.
- Pilot with 5–10 consenting adults; P05 is simulation only. Measure completion without assistance, time to first usable result, manual corrections, relevance and willingness to pay (hypotheses, not measured).

## Execution matrix
| Stage | 10 personas | Adversarial controls | Required evidence |
|---|---|---|---|
| E1 | auth x10 | unauthorized cross-user, wrong password, session rotation | tests + auth logs |
| E2 | CV x10, format variants | corrupted/scanned docs, mismatched headings, duplicate jobs | gold-field diff |
| E3 | facts x10 | corrections, duplicates, contradictory dates, replay | SQL count + trace |
| E4 | jobs x10 | different requirements, missing/weak evidence | fact-linked rationale |
| E5 | drafts x10 | injected/unverified claims, wrong user/fact | claim-by-claim diff |
| E6 | UI journeys x10 | interruptions, refresh, mobile, errors | E2E results + usability |

## Minimum evidence and reporting
For each persona and stage record input fixture ID, expected outcomes, actual outputs, per-field comparison, warnings, failures, and terminal PASS/FAIL. For qualitative value, real user interviews separately from deterministic automated assertions. Every stage may contain modules or fixtures expected to fail initially; do not modify expected outputs to conceal defects.

## Current code reality / blockers
- Existing React frontend lives on `/api/v1` and uses `backend/app` with auto-created local default identity in `get_current_user`.
- Auth, resume ingestion, Fact Ledger, grounded diagnostic/resume exist elsewhere in `production_api` with a different contract and DB model.
- E1-E6 unified journey is **NOT IMPLEMENTED or HOMOLOGATED** just because prior distinct suites yielded 353 passing tests.
- D2-D contract live: 5/5 PASS on separate backend React DB. Integration suite: 98/98 PASS.
- A ten-user simulation is not equivalent to ten real customer pilot interviews.

## Security / isolation
Work only in `test/sec05-stripe-prebeta`; preserve main, PR #2, original worktree and original DBs and SEC05 financial DB. The backend integration fixture performs DROP SCHEMA public CASCADE, so must use *only* dedicated disposable React test DB after strict verification. Do not commit personally identifying CVs/credentials. Do not expose a default shared identity as multi-user beta. Stripe Test Mode remains paused.

## First implementation sequence
1. E1: write 10 synthetic persona manifests and cross-account auth tests (expected red until canonical auth implemented).
2. Implement auth with explicit migrations on dedicated test database; no production migration.
3. Green E1 tests, then proceed E2 import engine into versioned API, etc.
