from io import BytesIO
import pytest
from resume_ingestion import extract_resume, suggested_sections

def test_txt_upload():
    r=extract_resume('resume.txt',b'Experiencia\nProjeto de dados usando Python e SQL na empresa.\n')
    assert r['format']=='txt' and 'Python' in r['text']

def test_docx_upload():
    from docx import Document
    d=Document();d.add_paragraph('Projeto de analise de dados utilizando Python e SQL no trabalho.')
    buf=BytesIO();d.save(buf)
    assert 'Python' in extract_resume('resume.docx',buf.getvalue())['text']

def test_reject_bad_files():
    for name, data in [('resume.pdf',b'not a pdf'*10),('resume.exe',b'x'*100),('resume.txt',b'x'*2000001)]:
        with pytest.raises(ValueError):extract_resume(name,data)

def test_explicit_sections_only():
    sections=suggested_sections('Experiência:\nAnalista de dados\nProjetos:\nAutomação de planilhas')
    assert 'experiencia' in sections and 'projetos' in sections
