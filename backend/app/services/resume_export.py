"""D2-E2.F.3 — Candidate-approved, evidence-only one-page résumé exports.

A digest binds approval to the *current* active ledger and omitted item list.
No employer claims, generated achievements, inferred dates, LLM, or file storage.
PDF is rendered first as the one-page preflight for either output type.
"""

import hashlib
import io
import json
from html import escape
from typing import Any, Literal

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt
from pypdf import PdfReader
from reportlab.lib import colors  # type: ignore[import-untyped]
from reportlab.lib.enums import TA_CENTER  # type: ignore[import-untyped]
from reportlab.lib.pagesizes import A4  # type: ignore[import-untyped]
from reportlab.lib.styles import ParagraphStyle  # type: ignore[import-untyped]
from reportlab.platypus import Paragraph, SimpleDocTemplate  # type: ignore[import-untyped]
from reportlab.platypus.doctemplate import LayoutError  # type: ignore[import-untyped]
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, UnprocessableError
from app.models import User
from app.services.evidence_resume import resume_draft

HEADINGS = {
    "experience": "EXPERIÊNCIA PROFISSIONAL",
    "education": "FORMAÇÃO",
    "project": "PROJETOS",
    "skill": "COMPETÊNCIAS",
}
MAX_BYTES = 500_000


def _approval_payload(name: str, draft: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": name,
        "sections": draft["sections"],
        "omitted": draft["omitted"],
        "template_version": "ats-simple-a4-v1",
    }


def _digest(payload: dict[str, Any]) -> str:
    serialized = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def export_preview(db: Session, user: User) -> dict[str, Any]:
    draft = resume_draft(db, user.id)
    digest = _digest(_approval_payload(user.name, draft))
    return {
        **draft,
        "candidate_name": user.name,
        "approval_sha256": digest,
        "approval_required": True,
        "page_limit": 1,
        "export_formats": ["pdf", "docx"],
    }


def _lines(preview: dict[str, Any]) -> list[tuple[str, list[str]]]:
    result: list[tuple[str, list[str]]] = []
    for section in preview["sections"]:
        items: list[str] = []
        for entry in section["entries"]:
            parts = [entry["title"]]
            if entry.get("organization"):
                parts.append(entry["organization"])
            dates = [entry[field] for field in ("start_date", "end_date") if entry.get(field)]
            if dates:
                parts.append(" – ".join(dates))
            items.append(" | ".join(parts))
            if entry.get("description"):
                items.append(entry["description"])
        if items:
            result.append((HEADINGS[section["category"]], items))
    return result


def _pdf(name: str, sections: list[tuple[str, list[str]]]) -> bytes:
    output = io.BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=A4,
        topMargin=36,
        bottomMargin=36,
        leftMargin=42,
        rightMargin=42,
        title="Currículo profissional",
        author="Job Agent — exportação aprovada pelo candidato",
        pageCompression=1,
    )
    styles = {
        "name": ParagraphStyle(
            "Name",
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            alignment=TA_CENTER,
            spaceAfter=10,
        ),
        "section": ParagraphStyle(
            "Section",
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=12,
            textColor=colors.HexColor("#17324D"),
            spaceBefore=9,
            spaceAfter=4,
        ),
        "entry": ParagraphStyle(
            "Entry",
            fontName="Helvetica",
            fontSize=8.7,
            leading=11.4,
            spaceAfter=3,
            splitLongWords=True,
        ),
    }
    story: list[Any] = [Paragraph(escape(name), styles["name"])]
    for heading, items in sections:
        story.append(Paragraph(escape(heading), styles["section"]))
        for line in items:
            story.append(Paragraph(escape(line), styles["entry"]))
    try:
        doc.build(story)
    except LayoutError:
        raise UnprocessableError(
            "Conteúdo não pode ser organizado em uma página", code="RESUME_ONE_PAGE_LIMIT"
        ) from None
    data = output.getvalue()
    if len(data) > MAX_BYTES or len(PdfReader(io.BytesIO(data)).pages) != 1:
        raise UnprocessableError(
            "Currículo não cabe em uma página; revise os fatos antes de exportar",
            code="RESUME_ONE_PAGE_LIMIT",
        )
    return data


def _docx(name: str, sections: list[tuple[str, list[str]]]) -> bytes:
    document = Document()
    sec = document.sections[0]
    sec.page_height, sec.page_width = Inches(11.69), Inches(8.27)
    sec.top_margin = sec.bottom_margin = Inches(0.5)
    sec.left_margin = sec.right_margin = Inches(0.58)
    default = document.styles["Normal"]
    default.font.name = "Arial"
    default.font.size = Pt(8.5)
    default.paragraph_format.space_after = Pt(2)
    default.paragraph_format.line_spacing = 1.05

    title = document.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    name_run = title.add_run(name)
    name_run.bold = True
    name_run.font.size = Pt(14)

    for heading, items in sections:
        paragraph = document.add_paragraph()
        paragraph.paragraph_format.space_before = Pt(6)
        run = paragraph.add_run(heading)
        run.bold = True
        run.font.size = Pt(9.5)
        for line in items:
            document.add_paragraph(line)

    output = io.BytesIO()
    document.save(output)
    data = output.getvalue()
    if len(data) > MAX_BYTES:
        raise UnprocessableError("Arquivo de currículo excedeu o limite", code="RESUME_FILE_LIMIT")
    return data


def approved_export(
    db: Session,
    user: User,
    format_name: Literal["pdf", "docx"],
    approved: bool,
    approval_sha256: str,
) -> bytes:
    if not approved:
        raise UnprocessableError(
            "Revisão humana e aprovação explícita são obrigatórias",
            code="RESUME_REVIEW_REQUIRED",
        )
    preview = export_preview(db, user)
    if approval_sha256 != preview["approval_sha256"]:
        raise ConflictError(
            "Os fatos do currículo mudaram; revise a versão atual",
            code="RESUME_APPROVAL_STALE",
        )
    if not user.name.strip():
        raise UnprocessableError("Nome do candidato não informado", code="RESUME_NO_NAME")
    sections = _lines(preview)
    if not sections:
        raise UnprocessableError(
            "Não há fatos estruturados suficientes para exportar",
            code="RESUME_EMPTY",
        )
    # Always preflight the PDF first: reject overfull drafts without truncation.
    pdf_data = _pdf(user.name, sections)
    if format_name == "pdf":
        return pdf_data
    return _docx(user.name, sections)
