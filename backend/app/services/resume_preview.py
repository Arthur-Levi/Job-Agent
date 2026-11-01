"""D2-E2.C: conservative, bounded ATS parse preview; never saves user CVs.

Only explicit text is used. No network, OCR, AI-inferred credentials or
persistence. Review items are local drafts, NOT confirmed career facts.
"""

from __future__ import annotations

import re
import unicodedata
import zipfile
from io import BytesIO
from typing import Any
from uuid import uuid4

from app.core.errors import UnprocessableError

MAX_FILE_BYTES = 2_000_000
MAX_TEXT_CHARS = 25_000
MAX_PDF_PAGES = 12
MAX_DOCX_UNCOMPRESSED = 10_000_000
MAX_DOCX_ENTRIES = 150

HEADINGS = {
    "experience": (
        r"(?:experi[eê]ncias?(?: profissionais?| de trabalho)?|"
        r"hist[oó]rico profissional|employment|work experience|professional experience)"
    ),
    "education": (
        r"(?:forma[cç][aã]o(?: acad[eê]mica)?|educa[cç][aã]o|"
        r"education|academic background|escolaridade)"
    ),
    "project": (
        r"(?:projetos?(?: pessoais| profissionais| relevantes)?|"
        r"projects|portfolio|portf[oó]lio)"
    ),
    "skill": (
        r"(?:habilidades|compet[eê]ncias(?: t[eé]cnicas)?|"
        r"tecnologias|skills|technical skills)"
    ),
    "summary": (
        r"(?:resumo(?: profissional)?|perfil profissional|"
        r"sobre mim|professional summary|about me)"
    ),
    "objective": r"(?:objetivo(?: profissional)?|cargo desejado|career objective|objective)",
}
DATE = re.compile(
    r"\b(?:19|20)\d{2}\b|\b(?:atual|presente|current|present)\b",
    flags=re.IGNORECASE,
)
MAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE = re.compile(r"(?<!\d)(?:\+?\d{1,3}[ -]?)?(?:\(?\d{2}\)?[ -]?)?\d{4,5}[ -]?\d{4}(?!\d)")


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return " ".join("".join(c for c in decomposed if not unicodedata.combining(c)).split())


def _heading(line: str) -> str | None:
    line = re.sub(r"^\s*(?:\d+[.)]\s*)?", "", line).strip("#* :\t-")
    if len(line) > 85:
        return None
    for key, pattern in HEADINGS.items():
        if re.fullmatch(pattern, line, re.IGNORECASE):
            return key
    return None


def _extract_docx(content: bytes) -> str:
    from docx import Document
    from docx.oxml.ns import qn
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    if not content.startswith(b"PK"):
        raise ValueError("Assinatura DOCX inválida")
    with zipfile.ZipFile(BytesIO(content)) as z:
        infos = z.infolist()
        if len(infos) > MAX_DOCX_ENTRIES or sum(i.file_size for i in infos) > MAX_DOCX_UNCOMPRESSED:
            raise ValueError("DOCX excede limites de expansão")
        for i in infos:
            name = i.filename.replace("\\", "/")
            if (
                name.startswith("/")
                or ".." in name.split("/")
                or name.lower().startswith(("word/activex/", "word/embeddings/"))
            ):
                raise ValueError("DOCX contém elemento não permitido")
    doc = Document(BytesIO(content))
    blocks: list[str] = []
    for element in doc.element.body.iterchildren():
        if element.tag == qn("w:p"):
            blocks.append(Paragraph(element, doc).text)
        elif element.tag == qn("w:tbl"):
            for row in Table(element, doc).rows:
                blocks.append(" | ".join(c.text.strip().replace("\n", "; ") for c in row.cells))
    return "\n".join(blocks)


def extract_text(filename: str, content: bytes) -> tuple[str, str]:
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if not content or len(content) > MAX_FILE_BYTES:
        raise UnprocessableError("Arquivo vazio ou acima de 2 MB", code="CV_SIZE")
    try:
        if suffix == "txt":
            if b"\x00" in content:
                raise ValueError("TXT binário não permitido")
            text = content.decode("utf-8-sig")
        elif suffix == "pdf":
            if not content.startswith(b"%PDF-"):
                raise ValueError("Assinatura PDF inválida")
            from pypdf import PdfReader

            reader = PdfReader(BytesIO(content), strict=True)
            if reader.is_encrypted or len(reader.pages) > MAX_PDF_PAGES:
                raise ValueError("PDF criptografado ou acima de 12 páginas")
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        elif suffix == "docx":
            text = _extract_docx(content)
        else:
            raise UnprocessableError("Formato permitido: PDF, DOCX ou TXT", code="CV_FORMAT")
    except UnprocessableError:
        raise
    except (ValueError, UnicodeError, zipfile.BadZipFile, KeyError, TypeError) as exc:
        raise UnprocessableError(str(exc), code="CV_PARSE") from None
    except Exception as exc:
        # Avoid reflecting attacker-controlled content and third-party parser errors.
        raise UnprocessableError(
            "Não foi possível extrair texto deste arquivo", code="CV_PARSE"
        ) from exc
    text = text.strip()
    if not 30 <= len(text) <= MAX_TEXT_CHARS:
        raise UnprocessableError(
            "Texto insuficiente ou acima de 25 mil caracteres; PDF escaneado pode exigir OCR",
            code="CV_TEXT",
        )
    return suffix, text


def _split_experiences(lines: list[str]) -> list[list[str]]:
    """Only split strong headings/dates. Ambiguous grouping stays flagged for review."""
    groups: list[list[str]] = []
    current: list[str] = []
    for raw in lines:
        line = raw.strip()
        if not line:
            if current:
                groups.append(current)
                current = []
            continue
        line = re.sub(r"^(?:[-•●*]|\d+[.)])\s+", "", line)
        date_heading = bool(DATE.search(line)) and len(line) <= 120 and not line.endswith(".")
        role_delimiter = "|" in line and date_heading
        if current and (role_delimiter or (date_heading and len(current) >= 2)):
            groups.append(current)
            current = []
        current.append(line[:350])
    if current:
        groups.append(current)
    return groups[:25]


def build_preview(filename: str, content: bytes) -> dict[str, Any]:
    fmt, text = extract_text(filename, content)
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        heading = _heading(line)
        if heading:
            current = heading
            sections.setdefault(heading, [])
        elif current:
            sections[current].append(line.rstrip())

    items: list[dict[str, Any]] = []
    for category in ("experience", "education", "project", "skill"):
        lines = sections.get(category, [])
        if category == "experience":
            groups = _split_experiences(lines)
        elif category == "skill":
            groups = [[line] for line in lines if line.strip()][:20]
        else:
            groups = _split_experiences(lines)
        for group in groups:
            if not group:
                continue
            excerpt = "\n".join(group)[:1200]
            title = group[0][:180]
            if len(title) < 2:
                continue
            warnings = []
            if category == "experience" and not DATE.search(excerpt):
                warnings.append("Datas não identificadas; revise cargo, empresa e período")
            if category == "experience" and len(group) > 4:
                warnings.append("Agrupamento heurístico: pode conter mais de uma experiência")
            items.append(
                {
                    "draft_id": str(uuid4()),
                    "category": category,
                    "title": title,
                    "description": "\n".join(group)[:4000],
                    "organization": None,
                    "start_date": None,
                    "end_date": None,
                    "source_excerpt": excerpt,
                    "review_status": "pending",
                    "warnings": warnings,
                }
            )

    found = sorted(sections)
    detected = {"email": bool(MAIL.search(text)), "phone": bool(PHONE.search(text))}
    warnings = [
        "Prévia não salva no banco. Corrija os campos localmente; "
        "confirmação será liberada em D2-E2.D.",
        "Detecção de menções não confirma competências nem garante leitura por ATS de terceiros.",
    ]
    if "experience" not in sections:
        warnings.append("Cabeçalho de experiência não encontrado")
    if not detected["email"]:
        warnings.append("Email não localizado no texto")
    if not detected["phone"]:
        warnings.append("Telefone não localizado no texto")
    return {
        "preview_id": str(uuid4()),
        "format": fmt,
        "character_count": len(text),
        "sections_detected": found,
        "fields_detected": detected,
        "items": items[:40],
        "limitations": warnings,
        "ats_check": {
            "method": "local_text_parser",
            "text_extractable": True,
            "sections_detected": found,
            "unrecognized_fields": [k for k, value in detected.items() if not value],
            "notice": (
                "Compatibilidade documental preliminar, não pontuação ou teste de ATS externo"
            ),
        },
    }
