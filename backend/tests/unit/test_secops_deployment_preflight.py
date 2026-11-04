"""E2.2-F configuration-policy checks; no CVs, Docker, filesystem or network."""

from dataclasses import replace

import pytest

from app.workers.secops_deployment_preflight import (
    DeploymentPreflightError,
    IsolatedWorkerDeployment,
    check_deployment,
)


def compliant_example() -> IsolatedWorkerDeployment:
    """Desired staging configuration; NOT a claim that it is deployed."""
    return IsolatedWorkerDeployment(
        api_parser_mode="broker",
        api_has_docker_socket=False,
        api_runs_as_root=False,
        broker_runs_as_root=False,
        broker_has_separate_identity=True,
        broker_socket_path="/run/jobagent-private/broker.sock",
        broker_socket_directory_mode=0o700,
        broker_socket_mode=0o600,
        broker_has_network_listener=False,
        parser_network_disabled=True,
        parser_readonly_rootfs=True,
        parser_non_root=True,
        parser_drops_all_capabilities=True,
        parser_no_new_privileges=True,
        parser_seccomp_enforced=True,
        parser_apparmor_or_selinux_enforced=True,
        parser_pid_limit=32,
        parser_memory_limit_mb=1024,
        parser_cpu_limit_millicores=1000,
        audit_logs_exclude_document_content=True,
    )


def test_compliant_configuration_contract() -> None:
    check_deployment(compliant_example())


@pytest.mark.parametrize(
    ("field", "unsafe"),
    [
        ("api_parser_mode", "subprocess"),
        ("api_parser_mode", "container"),
        ("api_has_docker_socket", True),
        ("api_runs_as_root", True),
        ("broker_runs_as_root", True),
        ("broker_has_separate_identity", False),
        ("broker_socket_path", "relative.sock"),
        ("broker_socket_path", "/run/../tmp/socket"),
        ("broker_socket_directory_mode", 0o755),
        ("broker_socket_mode", 0o666),
        ("broker_has_network_listener", True),
        ("parser_network_disabled", False),
        ("parser_readonly_rootfs", False),
        ("parser_non_root", False),
        ("parser_drops_all_capabilities", False),
        ("parser_no_new_privileges", False),
        ("parser_seccomp_enforced", False),
        ("parser_apparmor_or_selinux_enforced", False),
        ("parser_pid_limit", 33),
        ("parser_memory_limit_mb", 2048),
        ("parser_cpu_limit_millicores", 2000),
        ("audit_logs_exclude_document_content", False),
    ],
)
def test_unsafe_deployment_is_rejected(field: str, unsafe: object) -> None:
    config = replace(compliant_example(), **{field: unsafe})
    with pytest.raises(DeploymentPreflightError, match="preflight denied"):
        check_deployment(config)


def test_multiple_violations_are_reported_without_secrets() -> None:
    config = replace(
        compliant_example(),
        api_parser_mode="subprocess",
        api_has_docker_socket=True,
        parser_network_disabled=False,
    )
    with pytest.raises(DeploymentPreflightError) as error:
        check_deployment(config)
    message = str(error.value)
    assert "API_MUST_USE_BROKER" in message
    assert "API_RUNTIME_PRIVILEGE" in message
    assert "PARSER_NETWORK" in message
    assert "broker.sock" not in message
