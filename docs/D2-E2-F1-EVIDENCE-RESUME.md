# D2-E2.F.1 — Evidence-based resume engine

**State:** technical PASS CONDITIONAL; production and beta NO-GO.

**CI evidence:** implementation commit `a07fb2c905f4a590987d146463a0b7df288ddf1f`, https://github.com/Arthur-Levi/Job-Agent/actions/runs/41488529973 — **307 passed, 3 xfailed, 1 warning** in backend; frontend, Chromium+real API+disposable PostgreSQL regression, browser smoke, sandbox smoke and advisory audit jobs SUCCESS. The new resume draft is verified via integration tests, not yet through a dedicated React page.

Authenticated `GET /api/v1/career/resume-draft` returns a **read-only candidate-review draft**, exclusively from active, user-owned Fact Ledger entries, with each entry linked to its exact fact ID and verification status. Supported categories: experience, education, project and skill.

Safety and integrity: no guessed jobs, dates, metrics, education, qualifications or market claims; incomplete/unsupported/unstructured records are omitted explicitly, not silently converted to polished false facts. No text generation, auto-send, PDF/DOCX output, vacancy matching, or persistence. The response includes limitations and review status.

Coverage: integration tests against **disposable CI PostgreSQL** verify cross-user isolation, exclusion of superseded facts, exact fact provenance, omission of non-structured fields and empty state. The integration fixture may drop the `public` schema; never point it at preserved Codespaces DB.

Next D2-E2.F.2: compatibility analysis against user-supplied vacancy requirements with fact-linked evidence and uncertainty; after that PDF/DOCX + React approval. Production parser `CV_SANDBOX_REQUIRED` stays blocked, PR remains Draft and no main merge is authorized.
