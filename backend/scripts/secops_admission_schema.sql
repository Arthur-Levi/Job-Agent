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
COMMIT;
