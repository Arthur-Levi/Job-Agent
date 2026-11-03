-- SEC-OPS E2.2-D: execute ONLY in a newly created, disposable test database.
-- Deliberately not part of application Alembic migrations or production startup.
-- No resume/document body is stored.
BEGIN;
CREATE SCHEMA IF NOT EXISTS secops_admission;
CREATE TABLE IF NOT EXISTS secops_admission.nonces (
    service_id text NOT NULL,
    nonce text NOT NULL,
    expires_at timestamptz NOT NULL,
    PRIMARY KEY (service_id, nonce)
);
CREATE TABLE IF NOT EXISTS secops_admission.jobs (
    job_id uuid PRIMARY KEY,
    tenant_id varchar(64) NOT NULL,
    user_id uuid NOT NULL,
    idem_key varchar(128) NOT NULL,
    fingerprint bytea NOT NULL,
    status text NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled', 'expired')),
    expires_at timestamptz NOT NULL DEFAULT (now() + interval '10 minutes'),
    UNIQUE (tenant_id, user_id, idem_key)
);
CREATE INDEX IF NOT EXISTS ix_secops_jobs_active
    ON secops_admission.jobs (status, expires_at);
CREATE INDEX IF NOT EXISTS ix_secops_jobs_owner
    ON secops_admission.jobs (tenant_id, user_id);
-- E2.2-E: durable fenced ownership; no document body is stored.
CREATE TABLE IF NOT EXISTS secops_admission.leases (
    job_id uuid PRIMARY KEY REFERENCES secops_admission.jobs(job_id) ON DELETE CASCADE,
    worker_id uuid NOT NULL,
    generation bigint NOT NULL CHECK (generation > 0),
    deadline timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_secops_leases_deadline
    ON secops_admission.leases (deadline);
COMMIT;
