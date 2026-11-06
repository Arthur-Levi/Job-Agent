"""E2.2-F: pure, fail-closed checklist for isolated broker deployment.

This is configuration validation, NOT proof of host/container isolation.
Never invoke Docker, connect to the socket, run parsers, or inspect CVs.
"""

from dataclasses import dataclass
from pathlib import PurePosixPath


class DeploymentPreflightError(ValueError):
    """Deployment not eligible for an operational acceptance run."""


@dataclass(frozen=True)
class IsolatedWorkerDeployment:
    api_parser_mode: str
    api_has_docker_socket: bool
    api_runs_as_root: bool
    broker_runs_as_root: bool
    broker_has_separate_identity: bool
    broker_socket_path: str
    broker_socket_directory_mode: int
    broker_socket_mode: int
    broker_has_network_listener: bool
    parser_network_disabled: bool
    parser_readonly_rootfs: bool
    parser_non_root: bool
    parser_drops_all_capabilities: bool
    parser_no_new_privileges: bool
    parser_seccomp_enforced: bool
    parser_apparmor_or_selinux_enforced: bool
    parser_pid_limit: int
    parser_memory_limit_mb: int
    parser_cpu_limit_millicores: int
    audit_logs_exclude_document_content: bool


def check_deployment(config: IsolatedWorkerDeployment) -> None:
    """Reject missing safety properties; deployment evidence is still required."""
    violations: list[str] = []
    if config.api_parser_mode != "broker":
        violations.append("API_MUST_USE_BROKER")
    if config.api_has_docker_socket or config.api_runs_as_root:
        violations.append("API_RUNTIME_PRIVILEGE")
    if config.broker_runs_as_root or not config.broker_has_separate_identity:
        violations.append("BROKER_IDENTITY")
    socket_path = PurePosixPath(config.broker_socket_path)
    if (
        not config.broker_socket_path.startswith("/")
        or ".." in socket_path.parts
        or len(config.broker_socket_path) > 100
        or str(socket_path) in {"/", "."}
    ):
        violations.append("SOCKET_PATH")
    if config.broker_socket_directory_mode != 0o700 or config.broker_socket_mode != 0o600:
        violations.append("SOCKET_PERMISSIONS")
    if config.broker_has_network_listener:
        violations.append("BROKER_NETWORK_LISTENER")
    if not config.parser_network_disabled:
        violations.append("PARSER_NETWORK")
    if not config.parser_readonly_rootfs:
        violations.append("PARSER_ROOTFS")
    if not config.parser_non_root:
        violations.append("PARSER_IDENTITY")
    if not config.parser_drops_all_capabilities:
        violations.append("PARSER_CAPABILITIES")
    if not config.parser_no_new_privileges:
        violations.append("PARSER_PRIVILEGE_ESCALATION")
    if not config.parser_seccomp_enforced:
        violations.append("PARSER_SECCOMP")
    if not config.parser_apparmor_or_selinux_enforced:
        violations.append("PARSER_LSM")
    if not 1 <= config.parser_pid_limit <= 32:
        violations.append("PARSER_PIDS")
    if not 64 <= config.parser_memory_limit_mb <= 1024:
        violations.append("PARSER_MEMORY")
    if not 100 <= config.parser_cpu_limit_millicores <= 1000:
        violations.append("PARSER_CPU")
    if not config.audit_logs_exclude_document_content:
        violations.append("LOG_PRIVACY")
    if violations:
        raise DeploymentPreflightError("isolation preflight denied: " + ",".join(violations))
