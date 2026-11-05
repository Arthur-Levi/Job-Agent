"""F.1.2.4 — opt-in synthetic-only Docker parser acceptance laboratory.

Do not import from public API/production broker paths. The operator explicitly
runs this in a controlled development host with a *prebuilt local* parser image.
No customer documents, DB connection, host files mounted to worker or network.
"""

import base64
import json
import os
import subprocess
from io import BytesIO
from typing import Any

from docx import Document
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from app.services.resume_worker import (
    MAX_WORKER_OUTPUT,
    _cleanup_container,
    _container_command,
    _run_bounded,
)

LAB_ACK = "I_OWN_THIS_SYNTHETIC_PARSER_LAB"
FIXTURE_TEXT = (
    "Professional Experience\n"
    "Fictional Company | Analyst | 2020-2024\n"
    "Education\n"
    "Synthetic University\n"
    "Skills\n"
    "Python\n"
    "Power BI\n"
)


class ParserLabRejected(Exception):
    """Do not include document bytes or Docker diagnostic output in messages."""


def assert_runtime_security_options(options: object) -> None:
    """Refuse runtime if seccomp or mandatory-access-control option is unavailable."""
    if not isinstance(options, list) or not all(isinstance(item, str) for item in options):
        raise ParserLabRejected("SECOPS_RUNTIME_UNVERIFIED")
    normalized = [option.lower() for option in options]
    has_seccomp = any("seccomp" in option and "unconfined" not in option for option in normalized)
    has_lsm = any(
        ("apparmor" in option or "selinux" in option) and "unconfined" not in option
        for option in normalized
    )
    if not has_seccomp or not has_lsm:
        raise ParserLabRejected("SECOPS_RUNTIME_UNVERIFIED")


def _synthetic_pdf() -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    font_ref = writer._add_object(font)
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_ref})}
    )
    # Only constant self-authored synthetic ASCII is embedded.
    commands = [b"BT /F1 12 Tf 40 700 Td"]
    for index, line in enumerate(FIXTURE_TEXT.splitlines()):
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        commands.append(
            (f"0 {-18 if index else 0} Td ({escaped}) Tj").encode("ascii")
        )
    commands.append(b"ET")
    stream = DecodedStreamObject()
    stream.set_data(b" ".join(commands))
    page[NameObject("/Contents")] = writer._add_object(stream)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def _synthetic_docx() -> bytes:
    document = Document()
    for line in FIXTURE_TEXT.splitlines():
        document.add_paragraph(line)
    output = BytesIO()
    document.save(output)
    return output.getvalue()


def synthetic_cases() -> tuple[tuple[str, bytes, str, bool], ...]:
    """Fixtures are generated in RAM; no user inputs and no persistent uploads."""
    return (
        ("fictional.txt", FIXTURE_TEXT.encode("utf-8"), "txt", True),
        ("fictional.pdf", _synthetic_pdf(), "pdf", True),
        ("fictional.docx", _synthetic_docx(), "docx", True),
        ("bad-header.pdf", b"%PDF-not a valid PDF structure", "pdf", False),
        ("bad-archive.docx", b"PK\x03\x04invalid archive", "docx", False),
        ("binary.txt", b"synthetic\x00binary data", "txt", False),
    )


# Read only kernel-provided process facts inside a disposable parser container.
# No document content, environment secrets, host mounts or network calls.
_SANDBOX_STATUS = """
import json, os
status = {}
for line in open('/proc/self/status', encoding='ascii'):
    if line.startswith(('Uid:', 'CapEff:', 'NoNewPrivs:', 'Seccomp:')):
        key, value = line.split(':', 1)
        status[key] = value.strip()
try:
    status['LSM'] = open('/proc/self/attr/current', encoding='utf-8').read().strip()
except OSError:
    status['LSM'] = 'UNVERIFIED'
try:
    status['Interfaces'] = sorted(os.listdir('/sys/class/net'))
except OSError:
    status['Interfaces'] = ['UNVERIFIED']
print(json.dumps(status, sort_keys=True))
"""


def verify_kernel_sandbox_status(data: object) -> dict[str, bool]:
    """Fail closed if kernel status is missing, conflicting or unconfined."""
    if not isinstance(data, dict):
        raise ParserLabRejected("SECOPS_RUNTIME_UNVERIFIED")
    uid_field = data.get("Uid")
    uid_values = uid_field.split() if isinstance(uid_field, str) else []
    lsm = data.get("LSM")
    interfaces = data.get("Interfaces")
    checks = {
        "NON_ROOT_UID": len(uid_values) == 4 and uid_values[0] == "65532",
        "CAPABILITIES_DROPPED": data.get("CapEff") == "0000000000000000",
        "NO_NEW_PRIVILEGES": data.get("NoNewPrivs") == "1",
        "SECCOMP_FILTER": data.get("Seccomp") == "2",
        "LSM_CONFINED": isinstance(lsm, str)
        and bool(lsm)
        and lsm != "UNVERIFIED"
        and "unconfined" not in lsm.lower(),
        "NETWORK_LOOPBACK_ONLY": interfaces == ["lo"],
    }
    if not all(checks.values()):
        raise ParserLabRejected("SECOPS_RUNTIME_UNVERIFIED")
    return checks


def inspect_parser_runtime() -> dict[str, bool]:
    """Inspect actual process state with the same restricted flags as the parser."""
    name = "jobagent-f124-attestation-" + os.urandom(8).hex()
    command = _container_command(name)[:-2] + ["-c", _SANDBOX_STATUS]
    try:
        output = _run_bounded(command, b"", {"PATH": "/usr/bin:/bin", "HOME": "/nonexistent"})
    except (OSError, subprocess.TimeoutExpired):
        raise ParserLabRejected("SECOPS_RUNTIME_UNVERIFIED") from None
    finally:
        _cleanup_container(name)
    if output.returncode != 0 or len(output.stdout) > 8192:
        raise ParserLabRejected("SECOPS_RUNTIME_UNVERIFIED")
    try:
        data: Any = json.loads(output.stdout)
    except (ValueError, UnicodeError):
        raise ParserLabRejected("SECOPS_RUNTIME_UNVERIFIED") from None
    return verify_kernel_sandbox_status(data)


def parser_request(filename: str, data: bytes) -> bytes:
    return json.dumps(
        {"filename": filename, "content": base64.b64encode(data).decode("ascii")},
        separators=(",", ":"),
    ).encode("utf-8")


def run_synthetic_parser_lab() -> dict[str, bool]:
    """Execute *only generated test fixtures* using existing restricted Docker flags.

    This is not a parser release/production deployment attestation. Actual LSM,
    seccomp/cgroup state still requires operator Docker inspect + OS evidence.
    """
    if os.getenv("SECOPS_F124_ACK") != LAB_ACK:
        raise ParserLabRejected("SECOPS_DISPOSABLE_ACK_REQUIRED")

    info = subprocess.run(
        ["docker", "info", "--format", "{{json .SecurityOptions}}"],
        capture_output=True,
        check=False,
        timeout=8,
    )
    if info.returncode != 0 or len(info.stdout) > 8192:
        raise ParserLabRejected("SECOPS_RUNTIME_UNVERIFIED")
    try:
        assert_runtime_security_options(json.loads(info.stdout))
    except (ValueError, UnicodeError):
        raise ParserLabRejected("SECOPS_RUNTIME_UNVERIFIED") from None

    results = inspect_parser_runtime()
    for filename, content, expected_format, should_pass in synthetic_cases():
        request = parser_request(filename, content)
        if len(request) > 3_000_000:
            raise ParserLabRejected("SECOPS_FIXTURE_OVERSIZED")
        # Use the actual app parser image: no host mount, network, API DB or secrets.
        name = "jobagent-f124-synthetic-" + os.urandom(8).hex()
        command = _container_command(name)
        if not all(
            item in command
            for item in (
                "--network=none",
                "--read-only",
                "--cap-drop=ALL",
                "--security-opt=no-new-privileges",
                "--user=65532:65532",
            )
        ):
            raise ParserLabRejected("SECOPS_SANDBOX_FLAGS_MISSING")
        try:
            output = _run_bounded(
                command,
                request,
                {"PATH": "/usr/bin:/bin", "HOME": "/nonexistent"},
            )
        except (OSError, subprocess.TimeoutExpired):
            raise ParserLabRejected("SECOPS_PARSER_UNAVAILABLE") from None
        finally:
            # Docker CLI process termination alone does not guarantee worker
            # removal; force cleanup on timeout, crash, or malformed output.
            _cleanup_container(name)
        if output.returncode or len(output.stdout) > MAX_WORKER_OUTPUT:
            raise ParserLabRejected("SECOPS_PARSER_UNAVAILABLE")
        try:
            body: Any = json.loads(output.stdout)
        except (UnicodeError, ValueError):
            raise ParserLabRejected("SECOPS_PARSER_INVALID_OUTPUT") from None
        if not isinstance(body, dict) or type(body.get("ok")) is not bool:
            raise ParserLabRejected("SECOPS_PARSER_INVALID_OUTPUT")
        if should_pass:
            preview = body.get("preview")
            passed = (
                body["ok"] is True
                and isinstance(preview, dict)
                and preview.get("format") == expected_format
                and "experience" in preview.get("sections_detected", [])
                and preview.get("items") is not None
            )
        else:
            passed = body["ok"] is False and body.get("error") in {
                "CV_PARSE",
                "CV_FORMAT",
                "CV_SIZE",
                "CV_TEXT",
            }
        results[filename] = bool(passed)
    return results
