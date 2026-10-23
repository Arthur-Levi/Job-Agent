import pytest
from artifact_review import review

def test_artifact_inventory_not_verification():
    result=review([{'path':'src/main.py','content':'print(123)'},{'path':'tests/test_main.py','content':'def test_main(): assert True'},{'path':'README.md','content':'Example'},{'path':'requirements.txt','content':'pytest'}])
    assert result['checks']['test_files_present']
    assert result['checks']['source_present']
    assert not result['authorship_verified']
    assert not result['technical_correctness_verified']
    assert not result['tests_executed']
    assert result['proficiency_score'] is None

def test_adversarial_fake_tests_not_certified():
    r=review([{'path':'tests/test_fake.py','content':'# I promise all tests pass'}])
    assert r['checks']['test_files_present']
    assert r['tests_executed'] is False

def test_rejects_secrets_traversal_and_duplicate():
    for files in ([{'path':'../secrets.txt','content':'abc'}],
                  [{'path':'a.py','content':'abc'},{'path':'a.py','content':'def'}],
                  [{'path':'config.py','content':'api_key = "12345678901234567890"'}]):
        with pytest.raises(ValueError):review(files)

def test_order_independent_digest():
    a={'path':'a.py','content':'a'};b={'path':'b.py','content':'b'}
    assert review([a,b])['inventory_sha256']==review([b,a])['inventory_sha256']

def test_rejects_oversize():
    with pytest.raises(ValueError):review([{'path':'a.py','content':'x'*120001}])
