"""Synthetic CV extraction/review contract; NOT end-to-end production acceptance.

Direct preview invocation is deliberately restricted to in-memory fake resumes.
No untrusted documents, API upload, DB, network, real parser/broker or persistence.
"""

from io import BytesIO

import pytest
from docx import Document
from reportlab.pdfgen.canvas import Canvas

from app.core.errors import UnprocessableError
from app.services.resume_preview import build_preview

FAKE_RESUME = (
    "Resumo profissional\n"
    "Profissional ficticio buscando cargo administrativo.\n\n"
    "Experiencia profissional\n"
    "Empresa Exemplo A | Auxiliar Administrativo | 2022-2023\n"
    "Atualizou planilhas de controle interno.\n\n"
    "Empresa Exemplo B | Assistente de Logistica | 2024-2025\n"
    "Conferiu registros de estoque e documentos.\n\n"
    "Formacao\n"
    "Curso ficticio de processos logisticos.\n\n"
    "Competencias\n"
    "Excel\n"
    "Organizacao de documentos\n"
)


def make_docx() -> bytes:
    document = Document()
    for line in FAKE_RESUME.splitlines():
        document.add_paragraph(line)
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def make_pdf() -> bytes:
    buffer = BytesIO()
    pdf = Canvas(buffer)
    y = 800
    for line in FAKE_RESUME.splitlines():
        if line:
            pdf.drawString(40, y, line)
        y -= 18
    pdf.save()
    return buffer.getvalue()


@pytest.mark.parametrize(
    ("filename", "fixture"),
    [
        ("synthetic.txt", lambda: FAKE_RESUME.encode("utf-8")),
        ("synthetic.docx", make_docx),
        ("synthetic.pdf", make_pdf),
    ],
)
def test_synthetic_resume_extraction_requires_review(filename: str, fixture: object) -> None:
    assert callable(fixture)
    preview = build_preview(filename, fixture())
    assert preview["format"] == filename.split(".")[-1]
    assert "experience" in preview["sections_detected"]
    experience = [item for item in preview["items"] if item["category"] == "experience"]
    assert len(experience) == 2
    assert experience[0]["title"] == "Auxiliar Administrativo"
    assert experience[0]["organization"] == "Empresa Exemplo A"
    assert experience[1]["title"] == "Assistente de Logistica"
    assert experience[1]["organization"] == "Empresa Exemplo B"
    assert "estoque" not in experience[0]["description"]
    assert "planilhas" not in experience[1]["description"]
    assert all(item["review_status"] == "pending" for item in preview["items"])
    assert preview["ats_check"]["method"] == "local_text_parser"


def test_ambiguous_experience_is_never_confirmed_automatically() -> None:
    raw = (
        b"Experiencia profissional\n"
        b"Coordenacao de relatorios internos entre 2021 e 2023.\n"
        b"Equipe diversa; cargo e empregador nao confirmados.\n\n"
        b"Competencias\n"
        b"Excel\n"
    )
    preview = build_preview("synthetic.txt", raw)
    experience = [item for item in preview["items"] if item["category"] == "experience"]
    assert len(experience) == 1
    assert experience[0]["organization"] is None
    assert experience[0]["review_status"] == "pending"
    assert experience[0]["start_date"] is None


def test_executable_and_binary_payloads_fail_before_review() -> None:
    with pytest.raises(UnprocessableError):
        build_preview("synthetic.exe", FAKE_RESUME.encode())
    with pytest.raises(UnprocessableError):
        build_preview("synthetic.txt", b"\x00" + FAKE_RESUME.encode())


def test_preview_never_claims_ats_approval() -> None:
    preview = build_preview("synthetic.txt", FAKE_RESUME.encode())
    assert preview["ats_check"]["text_extractable"] is True
    assert "não pontuação" in preview["ats_check"]["notice"]
    assert all(item["review_status"] != "confirmed" for item in preview["items"])
