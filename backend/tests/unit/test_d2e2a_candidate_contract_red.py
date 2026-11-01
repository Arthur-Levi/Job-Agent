"""D2-E2.A contract inventory: expected RED until candidate routes are implemented.

These tests are expressly xfail(strict=True). They never open a database and
do not alter established CI acceptance. Remove xfail incrementally in D2-E2.B+.
"""

import pytest

from app.core.config import Settings
from app.main import create_app

_DB = "postgresql+psycopg://synthetic:synthetic@localhost/jobagent_contract_test"

TARGET_ROUTES = (
    ("POST", "/api/v1/resume-imports/preview"),
    ("POST", "/api/v1/resume-imports/confirm"),
    ("GET", "/api/v1/career/profile"),
    ("GET", "/api/v1/career/facts"),
    ("POST", "/api/v1/career/facts/{fact_id}/corrections"),
    ("GET", "/api/v1/career/facts/contradictions"),
    ("POST", "/api/v1/career/diagnostics"),
    ("POST", "/api/v1/career/resumes/drafts"),
)


def _openapi_paths() -> dict[str, object]:
    app = create_app(
        Settings(_env_file=None, database_url=_DB, app_env="test", log_level="WARNING")
    )
    return app.openapi()["paths"]


@pytest.mark.parametrize(("method", "path"), TARGET_ROUTES)
@pytest.mark.xfail(strict=True, reason="D2-E2.A spec-first: route missing from backend/app")
def test_candidate_journey_route_will_be_present(method: str, path: str) -> None:
    routes = _openapi_paths()
    assert method.lower() in routes[path]


@pytest.mark.xfail(strict=True, reason="D2-E2.A spec-first: multipart upload not wired yet")
def test_resume_preview_will_accept_multipart_and_require_bearer() -> None:
    operation = _openapi_paths()["/api/v1/resume-imports/preview"]["post"]
    assert "multipart/form-data" in operation["requestBody"]["content"]
    assert operation["security"] == [{"HTTPBearer": []}]


def test_d2_e2a_targets_are_not_accidentally_live_yet() -> None:
    """Positive audit baseline; xfail tests above are not disguised passes."""
    paths = _openapi_paths()
    assert all(path not in paths for _, path in TARGET_ROUTES)
    assert "/api/v1/profile" in paths
    assert "/api/v1/jobs" in paths
    assert "/api/v1/applications" in paths
