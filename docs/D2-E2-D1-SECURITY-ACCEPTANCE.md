# D2-E2.D.1 — Transactional audit (partial, NOT beta acceptance)

Branch: `audit/d2-e2d1-security-acceptance`; base `e32c602`.

## Implemented
- Both `confirm_import` and `correct_fact` acquire a PostgreSQL `users` row lock for the same owner before reading/updating career facts. This serializes same-user writes under the current PostgreSQL transaction strategy, including the empty-ledger first-import case.
- Added a parallel confirmation integration test using two independent SQLAlchemy sessions with different idempotency keys and equivalent synthetic facts.
- Correcting an imported structured fact now changes its description while preserving its original title, organization and period. A regression assertion checks these fields.

## Container prototype added (D2-E2.D.1-B)
- `backend/Dockerfile.resume-parser`: purpose-built parser-only image with unprivileged user.
- `resume_worker.py`: opt-in `RESUME_PARSER_MODE=container` using Docker CLI, no network, read-only filesystem, dropped capabilities, no-new-privileges, resource quotas and cleanup.
- Unit tests cover the runtime command and failure states without requiring Docker daemon or database.
- This is NOT a deployment-ready boundary: public API cannot be given Docker daemon power. Production keeps its explicit 503 gate.
- Previous CI run 41363339214 failed 2 user-count tests because an integration test left committed synthetic rows; the test fixture now cleans up. New CI has to prove correction.

## Not yet verified
- The new integration test has **not** been executed against an isolated PostgreSQL database by this audit. CI result must be checked.
- Per-user locking only works if **every** future writer of CareerFact follows the same locking discipline.
- Structured correction currently supports description-only changes; editing title, category, dates or provenance requires a separate versioned contract.
- Parser runs in a Linux subprocess with resource limits, **not** a network-restricted sandbox. `CV_SANDBOX_REQUIRED` must remain enabled in production.
- Review schema resets before test execution: never run database integration tests on preserved Codespaces data. Tests require an expressly provisioned disposable `*_test` PostgreSQL database.
- No permission to merge, deploy, process real CVs or charge customers.

## Acceptance gates
1. Validate CI Ruff / MyPy / backend+frontend tests on this exact commit.
2. Re-run true parallel-client tests on disposable PostgreSQL, including the same idempotency key and correction-versus-import race.
3. Audit the worker isolation, deny egress, enforce non-root / read-only filesystem / quotas / timeout, and test failure modes.
4. Verify cross-user authorization, backups/restore, retention, deletion and UI behavior separately.

**Status: IN PROGRESS / NOT APPROVED FOR REAL USERS.**
