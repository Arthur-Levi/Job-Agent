# D2-E — Persona corpus RED -> awaiting re-test
Date: 2026-10-31
Branch: `test/sec05-stripe-prebeta`

## Operator evidence (first run)
- `3 passed, 2 failed, 1 warning in 0.19s`
- `test_adversarial_cases_are_present`: employer discrepancy in P03; `Auxiliar de Estoque` incorrectly recorded as employer.
- `test_all_source_dates_and_labels_are_bounded`: missing `end` field.
- This was a **synthetic fixture generation problem**, NOT a failure in the deployed Job Agent account/authentication logic.

## Corrections committed
- Corrected field mapping for all P01-P10 sections (employer, role, start, end).
- Preserved 3 distinct sequential roles at same fictional employer for P03.
- P05 retains project classification rather than fabricated employment; P02 also classified as project.
- Extended tests to assert distinct roles, career date sequence, required schema keys and valid YYYY-MM formatting.

## Next execution
```bash
cd /workspaces/Job-Agent-SEC05
git fetch origin test/sec05-stripe-prebeta
git merge --ff-only origin/test/sec05-stripe-prebeta
cd backend
.venv/bin/python -m pytest tests/acceptance/test_d2e_persona_corpus.py -v --tb=short
```
**No new PASS is claimed.** Confirm after re-run.

## Next functional work
E1 real multiuser authentication and 10-account ownership tests. E2-E6 yet to be integrated. All destructive PostgreSQL integration tests must remain confined to the verified disposable React DB. Stripe paused.
