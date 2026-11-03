"""Synthetic-only supervisor tests: no Docker, DB, parser or network."""

from uuid import uuid4

from app.workers.synthetic_supervisor import SyntheticSupervisor
from app.workers.worker_lease import WorkerLease


class FakeLeases:
    def __init__(self, *, revoke_after: int = 0) -> None:
        self.calls = 0
        self.revoke_after = revoke_after
        self.completions: list[bool] = []

    def heartbeat(self, lease: WorkerLease) -> bool:
        self.calls += 1
        return not (self.revoke_after and self.calls >= self.revoke_after)

    def finish(self, lease: WorkerLease, *, succeeded: bool) -> bool:
        self.completions.append(succeeded)
        return True


def lease() -> WorkerLease:
    return WorkerLease(uuid4(), uuid4(), 1)


def test_synthetic_success_is_recorded() -> None:
    store = FakeLeases()
    result = SyntheticSupervisor(store).run(lease(), synthetic_mode="exit")
    assert result.outcome == "succeeded"
    assert result.returncode == 0
    assert store.completions == [True]


def test_revoked_before_launch_never_finishes() -> None:
    store = FakeLeases(revoke_after=1)
    result = SyntheticSupervisor(store).run(lease(), synthetic_mode="sleep")
    assert result.outcome == "revoked"
    assert result.returncode is None
    assert store.completions == []


def test_revoked_running_process_does_not_finish() -> None:
    store = FakeLeases(revoke_after=3)
    result = SyntheticSupervisor(store).run(lease(), synthetic_mode="sleep")
    assert result.outcome == "revoked"
    assert store.completions == []


def test_timeout_marks_failure_not_success() -> None:
    store = FakeLeases()
    result = SyntheticSupervisor(store, max_seconds=0.1).run(lease(), synthetic_mode="sleep")
    assert result.outcome == "timeout"
    assert store.completions == [False]


def test_rejects_arbitrary_mode() -> None:
    store = FakeLeases()
    try:
        SyntheticSupervisor(store).run(lease(), synthetic_mode="not-a-command")  # type: ignore[arg-type]
    except ValueError:
        pass
    else:
        raise AssertionError("unreviewed mode accepted")
