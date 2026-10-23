import threading
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.domain.enums import ApplicationEventType, ApplicationStatus
from app.models import ApplicationEvent
from app.repositories.application import ApplicationRepository
from app.repositories.job import JobRepository
from app.schemas.application import ApplicationCreate, ApplicationUpdate
from app.services.application import ApplicationService
from tests.integration.factories import make_job, make_user


class EventFailure(RuntimeError):
    pass


class FailingEventRepository(ApplicationRepository):
    """Simula falha ao gravar o evento. `only` restringe o tipo de evento que falha."""

    def __init__(self, session: Session, only: ApplicationEventType) -> None:
        super().__init__(session)
        self._only = only

    def add_event(self, event: ApplicationEvent) -> ApplicationEvent:
        if event.event_type is self._only:
            raise EventFailure("event could not be written")
        return super().add_event(event)


def status_of(session: Session, application_id: Any) -> str:
    return str(
        session.execute(
            text("SELECT status FROM applications WHERE id = :id"), {"id": application_id}
        ).scalar_one()
    )


def event_count(session: Session) -> int:
    return int(session.execute(text("SELECT count(*) FROM application_events")).scalar_one())


def test_status_change_and_event_are_atomic(db_session: Session) -> None:
    user = make_user(db_session)
    job = make_job(db_session, user)
    ok_service = ApplicationService(
        ApplicationRepository(db_session), JobRepository(db_session), db_session
    )
    created = ok_service.create(user, ApplicationCreate(job_id=job.id))
    application_id = created.application.id
    assert event_count(db_session) == 1

    failing = ApplicationService(
        FailingEventRepository(db_session, ApplicationEventType.STATUS_CHANGED),
        JobRepository(db_session),
        db_session,
    )
    with pytest.raises(EventFailure):
        failing.update(user, application_id, ApplicationUpdate(status=ApplicationStatus.QUALIFIED))

    # Nem o status mudou, nem sobrou evento: tudo ou nada.
    assert status_of(db_session, application_id) == "DISCOVERED"
    assert event_count(db_session) == 1


def test_application_creation_and_created_event_are_atomic(db_session: Session) -> None:
    user = make_user(db_session)
    job = make_job(db_session, user)
    db_session.commit()
    failing = ApplicationService(
        FailingEventRepository(db_session, ApplicationEventType.CREATED),
        JobRepository(db_session),
        db_session,
    )
    with pytest.raises(EventFailure):
        failing.create(user, ApplicationCreate(job_id=job.id))
    count = db_session.execute(text("SELECT count(*) FROM applications")).scalar_one()
    assert count == 0


def test_clock_is_injected(db_session: Session) -> None:
    fixed = datetime(2026, 5, 17, 9, 30, tzinfo=UTC)
    user = make_user(db_session)
    job = make_job(db_session, user)
    service = ApplicationService(
        ApplicationRepository(db_session), JobRepository(db_session), db_session, lambda: fixed
    )
    application_id = service.create(user, ApplicationCreate(job_id=job.id)).application.id
    for status in (
        ApplicationStatus.QUALIFIED,
        ApplicationStatus.PREPARED,
        ApplicationStatus.READY,
        ApplicationStatus.APPLIED,
    ):
        result = service.update(user, application_id, ApplicationUpdate(status=status))
    assert result.application.applied_at == fixed


def test_get_with_lock_really_holds_a_row_lock(migrated_engine: Engine) -> None:
    """Dados COMMITADOS (sem a transação de teste): prova que FOR UPDATE é emitido de fato."""
    holder = Session(migrated_engine)
    try:
        user = make_user(holder)
        job = make_job(holder, user)
        service = ApplicationService(ApplicationRepository(holder), JobRepository(holder), holder)
        application_id = service.create(user, ApplicationCreate(job_id=job.id)).application.id
        user_id = user.id

        ApplicationRepository(holder).get(user_id, application_id, lock=True)  # tx aberta

        with migrated_engine.connect() as other, pytest.raises(OperationalError):
            other.execute(
                text("SELECT id FROM applications WHERE id = :id FOR UPDATE NOWAIT"),
                {"id": application_id},
            )
    finally:
        holder.rollback()
        holder.close()
        with migrated_engine.begin() as cleanup:
            cleanup.execute(text("TRUNCATE users CASCADE"))  # TRUNCATE não aciona o trigger


class HoldingRepository(ApplicationRepository):
    """Segura a transação aberta (com o lock) logo após gravar o evento, até ser liberada."""

    def __init__(self, session: Session, locked: threading.Event, release: threading.Event) -> None:
        super().__init__(session)
        self._locked = locked
        self._release = release

    def add_event(self, event: ApplicationEvent) -> ApplicationEvent:
        saved = super().add_event(event)
        self._locked.set()
        assert self._release.wait(timeout=10)
        return saved


def test_concurrent_status_changes_are_serialized(migrated_engine: Engine) -> None:
    """A segura o lock no meio da transação; B (mesma candidatura) tem de ESPERAR e então
    validar contra o estado já commitado por A, em vez do estado antigo."""
    setup = Session(migrated_engine)
    try:
        user = make_user(setup)
        job = make_job(setup, user)
        service = ApplicationService(ApplicationRepository(setup), JobRepository(setup), setup)
        application_id = service.create(user, ApplicationCreate(job_id=job.id)).application.id
        user_id = user.id
        setup.close()

        locked, release = threading.Event(), threading.Event()
        outcome: dict[str, str] = {}

        def run(name: str, target: ApplicationStatus, hold: bool) -> None:
            with Session(migrated_engine) as session:
                repo = (
                    HoldingRepository(session, locked, release)
                    if hold
                    else ApplicationRepository(session)
                )
                worker = ApplicationService(repo, JobRepository(session), session)
                try:
                    worker.update(
                        make_user_ref(session, user_id),
                        application_id,
                        ApplicationUpdate(status=target),
                    )
                    outcome[name] = "ok"
                except Exception as exc:  # noqa: BLE001
                    outcome[name] = getattr(exc, "code", type(exc).__name__)

        first = threading.Thread(target=run, args=("A", ApplicationStatus.WITHDRAWN, True))
        first.start()
        assert locked.wait(timeout=10)  # A tem o lock e ainda não commitou

        second = threading.Thread(target=run, args=("B", ApplicationStatus.QUALIFIED, False))
        second.start()
        second.join(timeout=0.5)
        assert second.is_alive()  # B está BLOQUEADO esperando o lock de A
        assert "B" not in outcome

        release.set()
        first.join(timeout=10)
        second.join(timeout=10)

        # B validou contra WITHDRAWN (estado commitado por A), não contra DISCOVERED.
        assert outcome == {"A": "ok", "B": "INVALID_STATUS_TRANSITION"}
        with Session(migrated_engine) as check:
            changes = check.execute(
                text("SELECT count(*) FROM application_events WHERE event_type = 'STATUS_CHANGED'")
            ).scalar_one()
        assert changes == 1
    finally:
        release.set()
        with migrated_engine.begin() as cleanup:
            cleanup.execute(text("TRUNCATE users CASCADE"))


def make_user_ref(session: Session, user_id: Any) -> Any:
    from app.models import User

    return session.get_one(User, user_id)
