"""D2-E2.F.5: transactional read-only export and fault injection acceptance.

Only disposable GitHub CI PostgreSQL: migrated_engine recreates public schema.
Never run on a preserved Codespaces, staging or production database.
"""

import io
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from pypdf import PdfReader
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, UnprocessableError
from app.models import CareerFact, User
from app.services.career_facts import correct_fact, list_facts
from app.services.resume_export import approved_export, export_preview
from tests.integration.test_d2e2d1_d_transactional import _cleanup, _committed_user


def _prepare_fact(engine: Engine, user_id: object, title: str) -> None:
    with Session(engine) as db:
        user = db.get(User, user_id)
        assert user is not None
        db.add(
            CareerFact(
                user_id=user.id,
                import_id=None,
                subject=title,
                predicate="experience",
                value=json.dumps(
                    {
                        "title": title,
                        "description": "Dados sinteticos de teste",
                        "organization": "Empresa Sintetica",
                        "start_date": "2023",
                        "end_date": "2024",
                    }
                ),
                source_type="user_statement",
                source_reference="synthetic-f5",
                verification="USER_DECLARED",
                status="ACTIVE",
            )
        )
        db.commit()


def test_parallel_document_reads_are_tenant_isolated(migrated_engine: Engine) -> None:
    left = _committed_user(migrated_engine)
    right = _committed_user(migrated_engine)
    try:
        _prepare_fact(migrated_engine, left, "Cargo Exclusivo A")
        _prepare_fact(migrated_engine, right, "Cargo Exclusivo B")
        barrier = Barrier(2)

        def perform(user_id: object) -> tuple[str, str]:
            with Session(migrated_engine) as db:
                user = db.get(User, user_id)
                assert user is not None
                review = export_preview(db, user)
                barrier.wait(timeout=15)
                content = approved_export(db, user, "pdf", True, review["approval_sha256"])
                assert len(PdfReader(io.BytesIO(content)).pages) == 1
                extracted = PdfReader(io.BytesIO(content)).pages[0].extract_text()
                return review["approval_sha256"], extracted

        with ThreadPoolExecutor(max_workers=2) as executor:
            a = executor.submit(perform, left)
            b = executor.submit(perform, right)
            digest_a, content_a = a.result(timeout=40)
            digest_b, content_b = b.result(timeout=40)
        assert digest_a != digest_b
        assert "Cargo Exclusivo A" in content_a and "Cargo Exclusivo B" not in content_a
        assert "Cargo Exclusivo B" in content_b and "Cargo Exclusivo A" not in content_b
        with Session(migrated_engine) as db:
            assert len(list_facts(db, left)) == 1
            assert len(list_facts(db, right)) == 1
    finally:
        _cleanup(migrated_engine, left)
        _cleanup(migrated_engine, right)


def test_old_approval_is_refused_after_committed_correction(migrated_engine: Engine) -> None:
    user_id = _committed_user(migrated_engine)
    try:
        _prepare_fact(migrated_engine, user_id, "Analista Sintetico")
        with Session(migrated_engine) as initial:
            user = initial.get(User, user_id)
            assert user is not None
            digest = export_preview(initial, user)["approval_sha256"]
            fact_id = list_facts(initial, user_id)[0].id
        with Session(migrated_engine) as correction:
            correct_fact(correction, user_id, fact_id, "Texto corrigido", "Teste concorrente")
        with Session(migrated_engine) as later:
            user = later.get(User, user_id)
            assert user is not None
            with pytest.raises(ConflictError) as stale:
                approved_export(later, user, "pdf", True, digest)
            assert stale.value.code == "RESUME_APPROVAL_STALE"
            assert len(list_facts(later, user_id)) == 1
            assert len(list_facts(later, user_id, include_history=True)) == 2
    finally:
        _cleanup(migrated_engine, user_id)


def test_renderer_error_never_modifies_fact_ledger(
    migrated_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = _committed_user(migrated_engine)
    try:
        _prepare_fact(migrated_engine, user_id, "Teste de Falha")
        with Session(migrated_engine) as db:
            user = db.get(User, user_id)
            assert user is not None
            digest = export_preview(db, user)["approval_sha256"]
            before = [(f.id, f.status, f.value) for f in list_facts(db, user_id, True)]

            def crash(_name: str, _sections: object) -> bytes:
                raise UnprocessableError("Falha sintética", code="SYNTHETIC_RENDER_FAILURE")

            monkeypatch.setattr("app.services.resume_export._pdf", crash)
            with pytest.raises(UnprocessableError) as failure:
                approved_export(db, user, "docx", True, digest)
            assert failure.value.code == "SYNTHETIC_RENDER_FAILURE"
            after = [(f.id, f.status, f.value) for f in list_facts(db, user_id, True)]
            assert before == after
        with Session(migrated_engine) as reopened:
            assert len(list_facts(reopened, user_id)) == 1
    finally:
        _cleanup(migrated_engine, user_id)
