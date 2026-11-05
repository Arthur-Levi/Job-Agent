"""F.1.2.4 parser fixture and sandbox-policy tests. No Docker is started."""

import base64
import json
import subprocess
from unittest.mock import Mock

import pytest
from pypdf import PdfReader

from app.services.resume_preview import build_preview
from app.workers import secops_synthetic_parser_lab as lab


def test_generated_pdf_docx_txt_are_readable_synthetic_cv_fixtures() -> None:
    cases = lab.synthetic_cases()
    assert len(cases) == 6
    for filename, content, expected, should_pass in cases:
        assert "fictional" in filename or not should_pass
        assert len(content) <= 2_000_000
        if should_pass:
            preview = build_preview(filename, content)
            assert preview["format"] == expected
            assert "experience" in preview["sections_detected"]
            assert preview["items"]
        else:
            from app.core.errors import UnprocessableError

            with pytest.raises(UnprocessableError):
                build_preview(filename, content)


def test_pdf_has_only_fictional_data() -> None:
    from io import BytesIO

    pdf_bytes = lab._synthetic_pdf()
    pdf = PdfReader(BytesIO(pdf_bytes), strict=True)
    extracted = pdf.pages[0].extract_text()
    assert "Fictional Company" in extracted
    assert "Synthetic University" in extracted


@pytest.mark.parametrize(
    "options",
    [
        [],
        ["name=seccomp,profile=builtin"],
        ["name=apparmor"],
        ["name=seccomp,profile=unconfined", "name=apparmor"],
        ["name=seccomp,profile=builtin", "name=apparmor,profile=unconfined"],
        None,
        "seccomp,apparmor",
    ],
)
def test_security_config_missing_controls_fails_closed(options: object) -> None:
    with pytest.raises(lab.ParserLabRejected, match="SECOPS_RUNTIME_UNVERIFIED"):
        lab.assert_runtime_security_options(options)


def test_seccomp_and_lsm_present_only_satisfies_preflight() -> None:
    lab.assert_runtime_security_options(
        ["name=seccomp,profile=builtin", "name=apparmor"]
    )


def test_requires_explicit_operator_opt_in(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SECOPS_F124_ACK", raising=False)
    with pytest.raises(lab.ParserLabRejected, match="ACK_REQUIRED"):
        lab.run_synthetic_parser_lab()


def test_docker_info_without_security_options_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SECOPS_F124_ACK", lab.LAB_ACK)
    monkeypatch.setattr(
        lab.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            ["docker"], 0, b"[]"
        ),
    )
    with pytest.raises(lab.ParserLabRejected, match="UNVERIFIED"):
        lab.run_synthetic_parser_lab()


def test_synthetic_lab_does_not_need_real_docker_for_contract_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SECOPS_F124_ACK", lab.LAB_ACK)
    monkeypatch.setattr(
        lab.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            ["docker"], 0, b'["name=seccomp,profile=builtin","name=apparmor"]'
        ),
    )

    monkeypatch.setattr(
        lab,
        "inspect_parser_runtime",
        lambda: {
            "NON_ROOT_UID": True,
            "CAPABILITIES_DROPPED": True,
            "NO_NEW_PRIVILEGES": True,
            "SECCOMP_FILTER": True,
            "LSM_CONFINED": True,
            "NETWORK_LOOPBACK_ONLY": True,
        },
    )
    names: list[str] = []

    def synthetic_runner(
        command: list[str], request: bytes, env: dict[str, str]
    ) -> subprocess.CompletedProcess[bytes]:
        assert "--network=none" in command
        assert "--read-only" in command
        assert "--cap-drop=ALL" in command
        assert not any("/var/run/docker.sock" in part for part in command)
        assert "DATABASE_URL" not in env
        name = command[command.index("--name") + 1]
        names.append(name)
        obj = json.loads(request)
        payload = base64.b64decode(obj["content"], validate=True)
        try:
            preview = build_preview(obj["filename"], payload)
            output = {"ok": True, "preview": preview}
        except Exception:
            output = {"ok": False, "error": "CV_PARSE"}
        return subprocess.CompletedProcess(
            command, 0, json.dumps(output).encode("utf-8")
        )

    cleanup = Mock()
    monkeypatch.setattr(lab, "_run_bounded", synthetic_runner)
    monkeypatch.setattr(lab, "_cleanup_container", cleanup)
    result = lab.run_synthetic_parser_lab()
    assert len(result) == 12
    assert all(result.values())
    assert len(names) == 6
    assert cleanup.call_count == 6


def test_parser_failure_always_attempts_cleanup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECOPS_F124_ACK", lab.LAB_ACK)
    monkeypatch.setattr(
        lab.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            ["docker"], 0, b'["name=seccomp,profile=builtin","name=apparmor"]'
        ),
    )
    monkeypatch.setattr(lab, "inspect_parser_runtime", lambda: {"NON_ROOT_UID": True})

    def fail(*args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        raise subprocess.TimeoutExpired(["docker"], 10)

    cleanup = Mock()
    monkeypatch.setattr(lab, "_run_bounded", fail)
    monkeypatch.setattr(lab, "_cleanup_container", cleanup)
    with pytest.raises(lab.ParserLabRejected, match="UNAVAILABLE"):
        lab.run_synthetic_parser_lab()
    cleanup.assert_called_once()


def test_kernel_attestation_requires_real_isolated_process() -> None:
    good = {
        "Uid": "65532 65532 65532 65532",
        "CapEff": "0000000000000000",
        "NoNewPrivs": "1",
        "Seccomp": "2",
        "LSM": "docker-default (enforce)",
        "Interfaces": ["lo"],
    }
    assert all(lab.verify_kernel_sandbox_status(good).values())
    for key, unsafe in (
        ("Uid", "0 0 0 0"),
        ("CapEff", "0000000000002000"),
        ("NoNewPrivs", "0"),
        ("Seccomp", "0"),
        ("LSM", "unconfined"),
        ("Interfaces", ["lo", "eth0"]),
    ):
        with pytest.raises(lab.ParserLabRejected, match="UNVERIFIED"):
            lab.verify_kernel_sandbox_status({**good, key: unsafe})
