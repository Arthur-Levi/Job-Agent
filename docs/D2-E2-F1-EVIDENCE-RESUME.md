# D2-E2.F.1 — Evidence-based resume engine

**State:** technical implementation awaiting CI acceptance, production and beta NO-GO.

Authenticated `GET /api/v1/career/resume-draft` returns a **read-only candidate-review draft**, exclusively from active, user-owned Fact Ledger entries, with each entry linked to its exact fact ID and verification status. Supported categories: experience, education, project and skill.

Safety and integrity: no guessed jobs, dates, metrics, education, qualifications or market claims; incomplete/unsupported/unstructured records are omitted explicitly, not silently converted to polished false facts. No text generation, auto-send, PDF/DOCX output, vacancy matching, or persistence. The response includes limitations and review status.

Coverage: integration tests against **disposable CI PostgreSQL** verify cross-user isolation, exclusion of superseded facts, exact fact provenance, omission of non-structured fields and empty state. The integration fixture may drop the `public` schema; never point it at preserved Codespaces DB.

Next D2-E2.F.2: compatibility analysis against user-supplied vacancy requirements with fact-linked evidence and uncertainty; after that PDF/DOCX + React approval. Production parser `CV_SANDBOX_REQUIRED` stays blocked, PR remains Draft and no main merge is authorized.
