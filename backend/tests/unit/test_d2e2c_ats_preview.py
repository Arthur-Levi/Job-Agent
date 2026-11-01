"""D2-E2.C bounded parser tests, no DB or personal resumes."""

from io import BytesIO
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.core.config import Settings
from app.core.errors import UnprocessableError
from app.main import create_app
from app.services.resume_preview import MAX_FILE_BYTES, build_preview, extract_text

SYNTHETIC_CV = """Candidato Sintético
email@exemplo.test
(11) 91234-5678

Experiência profissional
Empresa Aurora | Auxiliar Administrativo | 2022-2023
Atualização de planilhas e dados internos.
Empresa Aurora | Analista de Dados | 2023-2024
Dashboards de Power BI e Excel.
Empresa Horizonte | Assistente | 2024-2025
Conferência de relatórios.

Formação acadêmica
Tecnólogo em Dados | Escola Exemplo | 2024

Habilidades
Excel
Power BI
"""


def test_ats_preview_separates_three_roles_including_same_employer() -> None:
    result = build_preview("resume.txt", SYNTHETIC_CV.encode())
    roles = [i for i in result["items"] if i["category"] == "experience"]
    assert len(roles) == 3
    assert [item["title"] for item in roles] == [
        "Auxiliar Administrativo",
        "Analista de Dados",
        "Assistente",
    ]
    assert [item["organization"] for item in roles] == [
        "Empresa Aurora",
        "Empresa Aurora",
        "Empresa Horizonte",
    ]
    assert [item["start_date"] for item in roles] == ["2022", "2023", "2024"]
    assert result["fields_detected"] == {"email": True, "phone": True}
    assert result["ats_check"]["text_extractable"] is True
    assert all(item["review_status"] == "pending" for item in roles)


def test_parser_does_not_infer_missing_employer_or_dates() -> None:
    result = build_preview(
        "resume.txt",
        b"Candidate Synthetic\nWork experience\nBuilt internal sample dashboards without dates\n"
        b"Education\nSample university degree\n",
    )
    assert result["items"]
    assert all(item["organization"] is None for item in result["items"])
    assert all(item["start_date"] is None for item in result["items"])
    assert result["fields_detected"]["email"] is False


@pytest.mark.parametrize(
    ("filename", "payload"),
    [
        ("resume.exe", b"synthetic but unsupported file content xxxxxxxxxxxxxxx"),
        ("resume.txt", b"\x00" * 100),
        ("resume.txt", b"\xff" * 100),
        ("resume.pdf", b"not-a-pdf xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"),
        ("resume.docx", b"not-a-zip xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"),
        ("resume.txt", b"x" * (MAX_FILE_BYTES + 1)),
    ],
)
def test_rejects_invalid_or_oversized_content(filename: str, payload: bytes) -> None:
    with pytest.raises(UnprocessableError):
        extract_text(filename, payload)


def test_docx_parses_tables_in_source_order() -> None:
    from docx import Document

    doc = Document()
    doc.add_paragraph("Candidato Sintético")
    doc.add_paragraph("Experiência profissional")
    table = doc.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Empresa Aurora"
    table.cell(0, 1).text = "Analista de Dados | 2024"
    table.cell(1, 0).text = "Empresa Horizonte"
    table.cell(1, 1).text = "Auxiliar Administrativo | 2022"
    out = BytesIO()
    doc.save(out)
    preview = build_preview("sample.docx", out.getvalue())
    assert len([x for x in preview["items"] if x["category"] == "experience"]) == 2


def test_pdf_text_extraction_and_scanned_pdf_failure() -> None:
    from pypdf import PdfWriter

    pdf = PdfWriter()
    pdf.add_blank_page(width=300, height=300)
    out = BytesIO()
    pdf.write(out)
    with pytest.raises(UnprocessableError, match="escaneado"):
        build_preview("scanned.pdf", out.getvalue())


def test_preview_endpoint_requires_auth_without_db() -> None:
    app = create_app(
        Settings(
            _env_file=None,
            app_env="test",
            database_url="postgresql+psycopg://synthetic@localhost/demo_test",
        )
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/resume-imports/preview",
            files={"file": ("resume.txt", SYNTHETIC_CV.encode(), "text/plain")},
        )
    assert response.status_code == 401


def test_preview_endpoint_with_mock_user_does_not_commit_or_store_cv() -> None:
    app = create_app(
        Settings(
            _env_file=None,
            app_env="test",
            database_url="postgresql+psycopg://synthetic@localhost/demo_test",
        )
    )
    app.dependency_overrides[get_current_user] = lambda: Mock(id="synthetic-user")
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/resume-imports/preview",
            files={"file": ("resume.txt", SYNTHETIC_CV.encode(), "text/plain")},
        )
    assert response.status_code == 200, response.text
    assert response.json()["format"] == "txt"
    assert response.json()["items"][0]["category"] == "experience"


def test_chunked_body_size_limit_checked_before_parser() -> None:
    # The ASGI upload gate is exercised through the normal TestClient request path.
    app = create_app(
        Settings(
            _env_file=None,
            app_env="test",
            database_url="postgresql+psycopg://synthetic@localhost/demo_test",
        )
    )
    app.dependency_overrides[get_current_user] = lambda: Mock(id="synthetic-user")
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/resume-imports/preview",
            files={"file": ("resume.txt", b"x" * (2_150_000 + 1), "text/plain")},
        )
    assert response.status_code == 413
