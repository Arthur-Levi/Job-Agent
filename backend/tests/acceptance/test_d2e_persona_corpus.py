"""D2-E synthetic persona corpus contract — no DB, network or personal records.

Run: backend/.venv/bin/python -m pytest backend/tests/acceptance/test_d2e_persona_corpus.py -q
from the repository root, or .venv/bin/python -m pytest tests/acceptance -q from backend/.
This validates fixture quality only; it does NOT claim multi-user authentication is implemented.
"""
import json
from pathlib import Path

DATA = Path(__file__).with_name("d2e_personas.json")


def personas():
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    return payload["personas"]


def test_exactly_ten_distinct_synthetic_identities():
    rows = personas()
    assert len(rows) == 10
    assert {p["id"] for p in rows} == {f"P{i:02d}" for i in range(1, 11)}
    assert len({p["email"].lower() for p in rows}) == 10
    assert len({p["name"] for p in rows}) == 10
    assert all(p["email"].endswith("@example.test") for p in rows)


def test_every_persona_has_a_different_career_case():
    rows = personas()
    assert len({p["segment"] for p in rows}) == 10
    assert all(p["target_role"] and p["job"]["title"] for p in rows)
    assert all(p["resume"]["sections"] for p in rows)
    assert {p["resume"]["format"] for p in rows} == {"pdf", "docx", "txt"}


def test_every_expected_gap_is_grounded_in_job_requirements():
    for p in personas():
        req = set(p["job"]["requirements"])
        known = set(p["expected"]["supported_mentions"])
        gaps = set(p["expected"]["gaps_to_investigate"])
        assert known and gaps
        assert known <= req
        assert gaps <= req
        assert not (known & gaps)
        assert p["expected"]["requires_human_review"] is True
        assert "experiência inventada" in p["expected"]["forbidden_claims"]


def test_adversarial_cases_are_present():
    by_id = {p["id"]: p for p in personas()}
    roles = by_id["P03"]["resume"]["sections"]
    assert len(roles) == 3
    assert len({x["role"] for x in roles}) == 3
    assert len({x["employer"] for x in roles}) == 1
    assert [x["role"] for x in roles] == ["Auxiliar de Estoque", "Conferente", "Supervisor de Operações"]
    assert [x["start"] for x in roles] == ["2014-01", "2018-01", "2021-01"]
    assert [x["end"] for x in roles] == ["2017-12", "2020-12", "2026-10"]
    assert by_id["P01"]["resume"]["sections"][0]["role"] == "Aprendiz Administrativo"
    assert len(by_id["P09"]["resume"]["conflicting_claims"][0]["values"]) == 2
    assert by_id["P10"]["resume"]["language"] == "pt-BR/en-US"
    assert by_id["P05"]["resume"]["sections"][0]["kind"] == "project"


def test_all_source_dates_and_labels_are_bounded():
    for p in personas():
        for section in p["resume"]["sections"]:
            assert section["role"].strip()
            assert section["description"].strip()
            assert set(("kind", "employer", "role", "start", "end", "description")) <= set(section)
            assert section["employer"].strip()
            import re
            start = section["start"]
            assert re.fullmatch(r"(19|20)\d{2}-(0[1-9]|1[0-2])", start)
            if section["end"]:
                assert re.fullmatch(r"(19|20)\d{2}-(0[1-9]|1[0-2])", section["end"])
                assert section["end"] >= start
