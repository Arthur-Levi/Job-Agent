# INFRA-01D — Named-volume persistence restart acceptance

Date: 2026-10-31
Branch: `test/sec05-stripe-prebeta`
Status: **PASS (operator-reported)**.

## Observed evidence
The operator ran the explicitly scoped test for the disposable PostgreSQL container and reported:

```text
INFRA-01D: PERSISTENCE PASS
```

## Procedure covered by this PASS
The supplied shell script checked:
- The target container is `jobagent-sec05-db`, bound to `127.0.0.1:55434`.
- The Docker mount for `/var/lib/postgresql/data` is the named volume `jobagent-sec05-pgdata`.
- Alembic revision is `0006_subscription_price_guard`.
- A randomly identified `audit` marker was inserted.
- Only the new SEC-05 container was restarted; health returned `healthy`.
- The marker count after restart was exactly one.
- The script removed the marker and printed the PASS line.

No independent re-run by the assistant was performed. This proves persistence for **one controlled container restart**. It is not proof of Codespaces lifecycle durability, storage backup, or disaster recovery.

## Next gates
1. Safely parameterize FC04 and FC05 integration tests for the new port `55434` and local credential file; preserve strict database/volume identity guards.
2. Rerun FC04, then reproduce/constrain FC05 concurrent duplicate webhook behavior; repair transaction/idempotency issues if demonstrated.
3. Test actual Stripe Test Mode signature + lifecycle, billing reconciliation, and failure recovery.
4. Resolve mutable historic `0001_initial` migration and formalize a reproducible container setup without secrets.

Never modify original DB containers, `main`, or PR #2. Never commit credentials or `.env` files.
