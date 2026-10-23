import pytest
from technical_quality import analyze
from contribution_review import summarize
from sandbox_runner import run_python_tests

def test_parseable_code_and_syntax_error():
    r=analyze([{'path':'src/a.py','content':'def f():\n    return 1\n'},{'path':'src/b.py','content':'def bad(:\n pass'}])
    assert r['statistics']['python_parseable']==1
    assert any(x['rule']=='PY_SYNTAX' for x in r['static_findings'])
    assert r['tests_executed'] is False

def test_dynamic_exec_is_not_certified():
    r=analyze([{'path':'app.py','content':'eval("1+1")'}])
    assert any(x['rule']=='DYNAMIC_EXECUTION' for x in r['static_findings'])
    assert r['proficiency_score'] is None

def test_fake_tests_not_executed():
    r=analyze([{'path':'tests/test_fake.py','content':'def test_ok():\n    assert True'}])
    assert r['tests_executed'] is False

def test_contributions_unverified():
    r=summarize([{'sha':'abcdef1234','author':'Someone','files':['src/app.py']}])
    assert r['commits_count']==1 and not r['identity_verified'] and not r['authorship_verified']

def test_duplicate_sha_rejected():
    c={'sha':'abcdef1234','author':'A','files':[]}
    with pytest.raises(ValueError):summarize([c,c])

def test_sandbox_fails_closed():
    with pytest.raises(RuntimeError):run_python_tests([{'path':'tests/test_x.py','content':'pass'}],image_digest='python:3.12.7-slim@sha256:'+'a'*64)
