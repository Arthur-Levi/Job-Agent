# D2-E1.5 — Public exposure security gate

**Status: implementation under CI review; NOT APPROVED for public exposure.**
**Scope:** isolated feature branch and PR #3. No deployments, database resets, original DB changes, or merge.

## Implemented

1. Protected registration when `REGISTRATION_PRIVACY_ENABLED=true`: both a new account and an already existing account return exactly HTTP 202 and the same generic JSON body, without email, ID or existence disclosure. An additional Argon2 hash is executed on duplicates to reduce gross timing differences. In development/test the legacy 201/409 contract remains by default; production settings require the privacy flag. This is a mitigation, not robust timing-indistinguishability or full verification; account enrollment/email verification and abuse controls require separate launch review.
2. Defensive API response headers: `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `X-Frame-Options: DENY`. Every `/api/v1/auth/*` response is `Cache-Control: no-store` and `Pragma: no-cache`; production API receives `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'`. HSTS must be enforced at the verified HTTPS ingress, not indiscriminately on an HTTP development API.
3. Trusted proxy guard `scripts/d2e15_proxy_policy.py`: validate loopback-only FastAPI bind, explicit small private/loopback proxy allowlist (never `*`), and frontend HTTPS origin. This is **dry run**: does not launch Uvicorn or configure cloud networking.
4. Unit test for Uvicorn trusted proxy semantics; unauthorised remote peer's spoofed `X-Forwarded-For` must be ignored.
5. New disposable-Postgres acceptance tests for identical registration responses and cache headers.

## Operational security requirements (MUST before live traffic)

- Deploy public TLS 1.2/1.3 HTTPS for the frontend and API; redirect HTTP, configure HSTS at terminating ingress after verifying HTTPS end-to-end.
- Bind Uvicorn to internal loopback; never allow public direct access to port 18081/8000. A real proxy must overwrite, **not append client-supplied**, `X-Forwarded-For` and forward correct scheme/host. Configure Uvicorn `--proxy-headers --forwarded-allow-ips <exact proxy IP/CIDR>` only if that peer and routing are confirmed. Avoid `--forwarded-allow-ips '*'`.
- Maintain explicit frontend CORS origins with HTTPS, never `*` in production. CORS does not replace authentication or network firewall.
- Security limits remain backed by PostgreSQL revision 0003. In deployment use a persistent secret (32+ characters) shared by all API workers and restarts; never rotate without coordinating active counters. No production credentials in repo.
- Observe and alert on 401, 429, 503, suspicious account-registration spikes, store unavailability, errors, and latency. Do not log passwords, bearer tokens, raw IPs or emails; access logs should avoid query strings and redact headers. Mask DB passwords in logs.
- Verify session revocation on logout, fixed TTL, no accidental localStorage persistence, correct 401 on expired sessions, and CSRF posture if browser auth ever switches to cookies.
- **Not implemented by D2-E1.5:** verified email ownership, password reset/email delivery, MFA, disaster recovery, external penetration tests, WAF/CDN, and tested reverse-proxy deployment. Do not open public registration or mark ready for public launch without clear owner-approved decisions on these release gates.

## Dry-run commands only (no DB or deployment)

```bash
cd /workspaces/Job-Agent-D2-E1-UI
PY=/workspaces/Job-Agent-SEC05/backend/.venv/bin/python
"$PY" scripts/d2e15_proxy_policy.py \
  --bind 127.0.0.1 --trusted-proxy 127.0.0.1 --https-origin https://app.example.com
```

The `example.com` address is a documentation placeholder, **not** a real deployment URL.

## Evidence and acceptance

Run GitHub CI backend Ruff/MyPy/pytest, frontend lint/build/tests, security audit. The proxy dry-run and synthetic proxy tests validate policy logic only. Full D2-E1.5 requires evidence of a real HTTPS reverse proxy setup, effective forwarding/IP tests from distinct clients, registration privacy with protections enabled, and safe operations before the PR can leave draft.
