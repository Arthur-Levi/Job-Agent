"""Bounded, no-network CV extraction. Never infers competence or persists raw files."""
from io import BytesIO
import re

MAX_BYTES=2_000_000
MAX_CHARS=25000

def extract_resume(filename: str, content: bytes) -> dict:
    if not content or len(content)>MAX_BYTES:
        raise ValueError('Arquivo vazio ou acima de 2 MB')
    suffix=filename.rsplit('.',1)[-1].lower() if '.' in filename else ''
    if suffix=='txt':
        if b'\x00' in content: raise ValueError('TXT binário não permitido')
        try: text=content.decode('utf-8-sig')
        except UnicodeDecodeError: raise ValueError('TXT deve usar UTF-8')
    elif suffix=='pdf':
        if not content.startswith(b'%PDF-'): raise ValueError('Assinatura PDF inválida')
        from pypdf import PdfReader
        reader=PdfReader(BytesIO(content),strict=True)
        if reader.is_encrypted: raise ValueError('PDF protegido por senha não permitido')
        if len(reader.pages)>12: raise ValueError('Limite de 12 páginas')
        text='\n'.join((page.extract_text(extraction_mode='layout') or page.extract_text() or '') for page in reader.pages)
    elif suffix=='docx':
        if not content.startswith(b'PK'):raise ValueError('Assinatura DOCX inválida')
        from docx import Document
        from zipfile import ZipFile
        with ZipFile(BytesIO(content)) as z:
            infos=z.infolist()
            if len(infos)>150 or sum(i.file_size for i in infos)>10_000_000:
                raise ValueError('DOCX excede limites de expansão')
            if any(i.filename.startswith(('word/embeddings/','word/activeX/')) for i in infos):
                raise ValueError('DOCX com conteúdo incorporado não permitido')
        doc=Document(BytesIO(content))
        # Walk DOCX blocks in original order; preserve table rows and cells.
        from docx.oxml.ns import qn
        from docx.text.paragraph import Paragraph
        from docx.table import Table
        blocks=[]
        for child in doc.element.body.iterchildren():
            if child.tag==qn('w:p'):
                blocks.append(Paragraph(child,doc).text)
            elif child.tag==qn('w:tbl'):
                table=Table(child,doc)
                for row in table.rows:
                    cells=[c.text.strip().replace('\n','; ') for c in row.cells]
                    blocks.append(' | '.join(c for c in cells if c))
        text='\n'.join(blocks)
    else: raise ValueError('Formato permitido: PDF, DOCX ou TXT')
    text=text.strip()
    if len(text)<30: raise ValueError('Texto insuficiente; arquivo escaneado pode exigir OCR')
    if len(text)>MAX_CHARS:raise ValueError('Texto extraído acima de 25 mil caracteres')
    return {'text':text,'format':suffix,'characters':len(text)}

def suggested_sections(text: str) -> dict:
    """Find explicit section headings only; never invent dates, employers or skills."""
    headings={'experiencia':r'^(experi[eê]ncia(?:s)?(?: profissional| de trabalho)?|hist[oó]rico profissional)$',
              'educacao':r'^(forma[cç][aã]o(?: acad[eê]mica)?|educa[cç][aã]o)$',
              'projetos':r'^projetos(?: pessoais| profissionais)?$',
              'habilidades':r'^(habilidades|compet[eê]ncias|tecnologias|skills)$'}
    sections={}; active=None
    for line in text.splitlines():
        clean=line.strip().strip(':').strip().lower()
        matched=next((k for k,pat in headings.items() if re.fullmatch(pat,clean)),None)
        if matched:
            active=matched;sections.setdefault(active,[])
        elif active and line.strip() and len(sections[active])<20:
            sections[active].append(line.strip()[:300])
    return {k:'\n'.join(v)[:2000] for k,v in sections.items() if v}
