"""CI-only integrity and render acceptance of synthetic candidate-approved documents.

Must be run only with disposable CI postgresql; no customer files allowed.
LibreOffice renderer is a *separate* check of DOCX actual page count.
"""

import hashlib
import io
import os
import subprocess
import tempfile
from pathlib import Path

from docx import Document
from pypdf import PdfReader

EXPECTED = (
    "Pessoa Sintetica",
    "Analista de Dados",
    "Assistente Administrativo",
    "Empresa Exemplo",
)
FORBIDDEN = ("Cargo secreto", "Emprego antigo", "999% de sucesso")


def _pdf_text(data: bytes) -> tuple[int, str]:
    reader = PdfReader(io.BytesIO(data))
    return len(reader.pages), "\n".join(page.extract_text() or "" for page in reader.pages)


def main() -> None:
    if any(os.getenv(key) != value for key, value in (
        ("CI", "true"), ("APP_ENV", "test"), ("E2E_DISPOSABLE_DATABASE", "1"),
    )):
        raise SystemExit("Only ephemeral CI synthetic-document verification is permitted")
    directory = Path(os.environ["E2E_ACCEPTANCE_ARTIFACT_DIR"])
    pdf_file = directory / "synthetic-resume.pdf"
    docx_file = directory / "synthetic-resume.docx"
    assert pdf_file.is_file() and docx_file.is_file(), "Missing real-browser downloads"
    pdf_data, docx_data = pdf_file.read_bytes(), docx_file.read_bytes()
    assert pdf_data.startswith(b"%PDF-") and docx_data.startswith(b"PK")
    assert 0 < len(pdf_data) <= 500_000 and 0 < len(docx_data) <= 500_000

    document = Document(io.BytesIO(docx_data))
    docx_text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    pdf_pages, pdf_text = _pdf_text(pdf_data)
    assert pdf_pages == 1, f"Backend PDF exceeds single page: {pdf_pages}"
    for label in EXPECTED:
        assert label in pdf_text, f"Missing synthetic content in PDF: {label}"
        assert label in docx_text, f"Missing synthetic content in DOCX: {label}"
    for value in FORBIDDEN:
        assert value not in pdf_text and value not in docx_text
    assert "\n".join(document.paragraphs[i].text for i in range(len(document.paragraphs))).strip()
    assert len(document.tables) == 0, "ATS layout must not include DOCX tables"
    assert len(document.inline_shapes) == 0, "ATS layout must not include images"

    with tempfile.TemporaryDirectory(prefix="jobagent-docx-qa-") as output_dir:
        cmd = [
            "libreoffice", "-env:UserInstallation=file:///tmp/jobagent-lo-f5",
            "--headless", "--convert-to", "pdf", "--outdir", output_dir,
            str(docx_file.resolve()),
        ]
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=90)
        rendered_pdf = Path(output_dir) / "synthetic-resume.pdf"
        assert rendered_pdf.is_file(), "DOCX did not render to PDF"
        docx_pages, rendered_text = _pdf_text(rendered_pdf.read_bytes())
        assert docx_pages == 1, (
            f"DOCX renderer produced {docx_pages} pages: requires manual layout revision"
        )
        for label in EXPECTED:
            assert label in rendered_text, f"Rendered DOCX lost synthetic content: {label}"
        # Keep preview PNGs for reviewer inspection; only synthetic personal data.
        subprocess.run(
            ["pdftoppm", "-f", "1", "-l", "1", "-singlefile", "-png",
             "-scale-to", "1100", str(pdf_file), str(directory / "pdf-preview")],
            check=True, capture_output=True, timeout=45,
        )
        subprocess.run(
            ["pdftoppm", "-f", "1", "-l", "1", "-singlefile", "-png",
             "-scale-to", "1100", str(rendered_pdf), str(directory / "docx-preview")],
            check=True, capture_output=True, timeout=45,
        )
        assert (directory / "pdf-preview.png").stat().st_size > 5000
        assert (directory / "docx-preview.png").stat().st_size > 5000

    print(
        "D2-E2.F.5 document integrity PASS",
        "pdf_pages=1", "libreoffice_docx_pages=1",
        "pdf_sha256=" + hashlib.sha256(pdf_data).hexdigest()[:16],
        "docx_sha256=" + hashlib.sha256(docx_data).hexdigest()[:16],
    )


if __name__ == "__main__":
    main()
