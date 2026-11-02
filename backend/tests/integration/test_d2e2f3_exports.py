"""D2-E2.F.3: source-backed, approved PDF/DOCX acceptance.

Only execute with disposable CI PostgreSQL: integration fixture resets public schema.
"""

import io
import json
from zipfile import ZipFile

from docx import Document
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.models import User
from tests.integration.test_d2e2e_diagnostic import _fact, _user


def _authenticate(client: TestClient, user: User) -> None:
    app = client.app
    assert isinstance(app, FastAPI)
    app.dependency_overrides[get_current_user] = lambda: user


def _entry(
    db: Session, user: User, title: str, category: str,
    description: str = "Trabalho sintético com planilhas",
    status: str = "ACTIVE",
) -> None:
    _fact(
        db,
        user,
        title=title,
        category=category,
        status=status,
        value=json.dumps({
            "title": title,
            "description": description,
            "organization": "Empresa Sintética",
            "start_date": "2023",
            "end_date": "2024",
        }, ensure_ascii=False),
    )


def test_pdf_and_docx_only_contain_owned_active_evidence(
    api_client: TestClient, db_session: Session
) -> None:
    user = _user(db_session)
    other = _user(db_session)
    _entry(db_session, user, "Analista de Dados", "experience")
    _entry(db_session, user, "Excel", "skill", "Planilhas e fórmulas")
    _entry(db_session, user, "Emprego antigo", "experience", status="SUPERSEDED")
    _entry(db_session, other, "Cargo secreto", "experience")
    _authenticate(api_client, user)

    preview = api_client.get("/api/v1/career/resume-export/preview")
    assert preview.status_code == 200
    assert preview.json()["approval_required"] is True
    assert preview.json()["page_limit"] == 1
    digest = preview.json()["approval_sha256"]
    assert len(digest) == 64
    for fmt in ("pdf", "docx"):
        response = api_client.post(
            f"/api/v1/career/resume-export/{fmt}",
            json={"approved": True, "approval_sha256": digest},
        )
        assert response.status_code == 200, response.text
        assert response.headers["cache-control"] == "no-store, private"
        assert response.headers["content-disposition"].endswith(f'job-agent-resume.{fmt}"')
        if fmt == "pdf":
            reader = PdfReader(io.BytesIO(response.content))
            assert len(reader.pages) == 1
            text = reader.pages[0].extract_text()
        else:
            document = Document(io.BytesIO(response.content))
            text = "\n".join(paragraph.text for paragraph in document.paragraphs)
        assert "Analista de Dados" in text
        assert "Planilhas e fórmulas" in text
        assert "Empresa Sintética" in text
        assert "Emprego antigo" not in text
        assert "Cargo secreto" not in text
        assert "99%" not in text
        assert "EXPERIÊNCIA PROFISSIONAL" in text


def test_review_is_mandatory_and_stale_after_fact_change(
    api_client: TestClient, db_session: Session
) -> None:
    user = _user(db_session)
    _entry(db_session, user, "Assistente", "experience")
    _authenticate(api_client, user)
    digest = api_client.get("/api/v1/career/resume-export/preview").json()["approval_sha256"]
    denied = api_client.post(
        "/api/v1/career/resume-export/pdf",
        json={"approved": False, "approval_sha256": digest},
    )
    assert denied.status_code == 422
    assert denied.json()["error"]["code"] == "RESUME_REVIEW_REQUIRED"
    _entry(db_session, user, "Projeto atualizado", "project")
    stale = api_client.post(
        "/api/v1/career/resume-export/docx",
        json={"approved": True, "approval_sha256": digest},
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "RESUME_APPROVAL_STALE"
    current = api_client.get("/api/v1/career/resume-export/preview").json()
    assert current["approval_sha256"] != digest


def test_empty_and_overflow_fail_closed(api_client: TestClient, db_session: Session) -> None:
    user = _user(db_session)
    _authenticate(api_client, user)
    digest = api_client.get("/api/v1/career/resume-export/preview").json()["approval_sha256"]
    empty = api_client.post(
        "/api/v1/career/resume-export/pdf",
        json={"approved": True, "approval_sha256": digest},
    )
    assert empty.status_code == 422
    assert empty.json()["error"]["code"] == "RESUME_EMPTY"

    _entry(
        db_session, user, "Muito texto", "experience",
        description="Detalhes sintéticos " * 2400,
    )
    digest = api_client.get("/api/v1/career/resume-export/preview").json()["approval_sha256"]
    for fmt in ("pdf", "docx"):
        response = api_client.post(
            f"/api/v1/career/resume-export/{fmt}",
            json={"approved": True, "approval_sha256": digest},
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "RESUME_ONE_PAGE_LIMIT"


def test_docx_is_safe_zip_and_pdf_does_not_execute_markup(
    api_client: TestClient, db_session: Session
) -> None:
    user = _user(db_session)
    _entry(
        db_session, user, "Projeto de Dados", "project",
        description="<script>alert('fake')</script> & trabalho real",
    )
    _authenticate(api_client, user)
    digest = api_client.get("/api/v1/career/resume-export/preview").json()["approval_sha256"]
    pdf = api_client.post(
        "/api/v1/career/resume-export/pdf",
        json={"approved": True, "approval_sha256": digest},
    )
    assert pdf.status_code == 200
    assert "<script>" in PdfReader(io.BytesIO(pdf.content)).pages[0].extract_text()

    docx = api_client.post(
        "/api/v1/career/resume-export/docx",
        json={"approved": True, "approval_sha256": digest},
    )
    assert docx.status_code == 200
    with ZipFile(io.BytesIO(docx.content)) as container:
        assert "[Content_Types].xml" in container.namelist()
        assert "word/document.xml" in container.namelist()
        assert not any(path.endswith("vbaProject.bin") for path in container.namelist())
