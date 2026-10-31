"""Per-test, local-only rate-limit substitute for legacy API unit tests.

SEC-04's production middleware uses shared Redis; tests needing real Redis must run
their dedicated integration checks, not this pytest substitute.
"""
import pytest


@pytest.fixture(autouse=True)
def isolated_auth_rate_limiter(monkeypatch):
    import main

    counts = {}

    def fake_rate_script(*, keys, args):
        # Match the Redis Lua script's output shape: [count, remaining TTL].
        key = keys[0]
        counts[key] = counts.get(key, 0) + 1
        return [counts[key], int(args[0])]

    monkeypatch.setattr(main, "rate_script", fake_rate_script)
