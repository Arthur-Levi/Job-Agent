"""D2-E2.F.2 synthetic-only saved job integration; no production data or CVs."""

from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest

from app.core.errors import NotFoundError, UnprocessableError
from app.domain.enums import RequirementImportance
from app.services import saved_job_matching as subject


def _requirement(
    *,
    category: str | None = "skill",
    name: str = "Python",
    normalized_name: str | None = None,
    importance: RequirementImportance = RequirementImportance.MUST_HAVE,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        category=category,
        name=name,
        normalized_name=normalized_name,
        importance=importance,
    )


def _fixture(
    rows: list[SimpleNamespace] | None = None,
) -> tuple[Mock, UUID, UUID]:
    user_id, job_id = uuid4(), uuid4()
    db = Mock()
    db.scalar.return_value = SimpleNamespace(id=job_id, title="Synthetic Analyst")
    db.scalars.return_value = [_requirement()] if rows is None else rows
    return db, user_id, job_id


def test_owner_scoped_job_query_and_existing_matching_reused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db, user_id, job_id = _fixture(
        [
            _requirement(name="Python", normalized_name="python"),
            _requirement(
                category="education",
                name="Computing",
                importance=RequirementImportance.IMPORTANT,
            ),
        ]
    )
    matcher = Mock(
        return_value={
            "status": "preliminary_candidate_review",
            "summary": {"documented_match": 0},
            "limitations": ["Missing facts are not missing skills."],
        }
    )
    monkeypatch.setattr(subject, "vacancy_match", matcher)
    result = subject.explain_saved_job(db, user_id, job_id)
    sql = db.scalar.call_args.args[0]
    assert user_id in sql.compile().params.values()
    assert job_id in sql.compile().params.values()
    request = matcher.call_args.args[2]
    assert request.vacancy_title == "Synthetic Analyst"
    assert [item.name for item in request.requirements] == ["Computing", "python"]
    assert request.requirements[0].importance == "preferred"
    assert request.requirements[1].importance == "required"
    assert result["saved_job_id"] == str(job_id)
    assert result["vacancy_source"] == "owned_saved_job_requirements_unverified"
    assert result["summary"] == {"documented_match": 0}


def test_other_user_job_hidden_as_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    db, user_id, job_id = _fixture()
    db.scalar.return_value = None
    matcher = Mock()
    monkeypatch.setattr(subject, "vacancy_match", matcher)
    with pytest.raises(NotFoundError):
        subject.explain_saved_job(db, user_id, job_id)
    db.scalars.assert_not_called()
    matcher.assert_not_called()


@pytest.mark.parametrize(
    "rows",
    [
        [],
        [_requirement(category=None)],
        [_requirement(importance=RequirementImportance.UNKNOWN)],
        [_requirement(category="work_mode", name="hybrid")],
        [_requirement(category="work_mode", name="remote")],
        [_requirement(name="Python"), _requirement(name=" python ")],
        [_requirement(name="P")],
        [_requirement() for _ in range(21)],
    ],
)
def test_invalid_or_ambiguous_requirements_never_run_matcher(
    rows: list[SimpleNamespace], monkeypatch: pytest.MonkeyPatch
) -> None:
    db, user_id, job_id = _fixture(rows)
    matcher = Mock()
    monkeypatch.setattr(subject, "vacancy_match", matcher)
    with pytest.raises(UnprocessableError):
        subject.explain_saved_job(db, user_id, job_id)
    matcher.assert_not_called()


def test_read_only_does_not_insert_or_commit(monkeypatch: pytest.MonkeyPatch) -> None:
    db, user_id, job_id = _fixture()
    monkeypatch.setattr(
        subject,
        "vacancy_match",
        Mock(return_value={"status": "preliminary_candidate_review", "limitations": []}),
    )
    subject.explain_saved_job(db, user_id, job_id)
    db.add.assert_not_called()
    db.commit.assert_not_called()
    db.flush.assert_not_called()
