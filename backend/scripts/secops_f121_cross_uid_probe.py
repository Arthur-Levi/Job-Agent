"""F.1.2.1 opt-in disposable cross-UID authenticated broker ingress lab.

No resume parser, Docker invocation, API listener, real credentials or CVs.
Run ONLY as root inside an owned disposable container without docker.sock.
"""

import argparse
import json
import os
import pwd
import secrets
import socket
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from uuid import uuid4

from app.workers.broker_replay_sqlite import SqliteBrokerReplayStore
from app.workers.broker_transport_auth import (
    BrokerTransportGate,
    BrokerTransportRejected,
    GatewayWorkload,
    encode_signed_transport,
)
from app.workers.broker_transport_wire import read_frame, receive_authenticated, send_frame

API_UID = 61001
API_GID = 61010
GATEWAY_UID = 61002
GATEWAY_GID = 61010
BROKER_UID = 61003
BROKER_GROUP = 61020
UNKNOWN_UID = 61004
UNKNOWN_GID = 61004

# Lab fixture only. Never use any key from this file for a real deployment.
LAB_KEY = b"jobagent-disposable-lab-only-transport-key-2026"
LAB_SERVICE = "gateway-lab"


def payload() -> bytes:
    # status with generated fake UUIDs; no resumes/documents are ever transferred.
    return json.dumps(
        {
            "version": 1,
            "operation": "status",
            "request_id": str(uuid4()),
            "subject": {"user_id": str(uuid4()), "tenant_id": "test-only"},
            "job_id": str(uuid4()),
        },
        separators=(",", ":"),
    ).encode()


def server(ingress: str, db_path: str) -> int:
    os.umask(0o077)
    replay = SqliteBrokerReplayStore(db_path)
    gate = BrokerTransportGate(
        GatewayWorkload(LAB_SERVICE, GATEWAY_UID, GATEWAY_GID, LAB_KEY),
        replay,
        broker_uid=BROKER_UID,
    )
    with socket.socket(socket.AF_UNIX) as listener:
        listener.bind(ingress)
        os.chmod(ingress, 0o660)
        listener.listen(4)
        listener.settimeout(2.0)
        print("READY", flush=True)
        try:
            try:
                conn, _ = listener.accept()
            except TimeoutError:
                return 0
            with conn:
                conn.settimeout(2)
                try:
                    received = receive_authenticated(conn, gate)
                    assert received.operation == "status"
                    reply = "ACCEPTED"
                except (BrokerTransportRejected, OSError, ValueError) as exc:
                    reply = (
                        "REJECTED:" + exc.code
                        if isinstance(exc, BrokerTransportRejected)
                        else "REJECTED:BROKER_INVALID"
                    )
                send_frame(conn, reply.encode("ascii"))
            return 0
        finally:
            os.unlink(ingress)


def client(ingress: str, mode: str, raw_hex: str, nonce: str, timestamp: str) -> int:
    raw = bytes.fromhex(raw_hex)
    stamp = int(timestamp)
    service_id = LAB_SERVICE if mode != "forged-service" else "unknown-gateway"
    frame = encode_signed_transport(
        raw,
        service_id=service_id,
        timestamp=stamp,
        nonce=nonce,
        key=LAB_KEY,
    )
    if mode == "tampered":
        message = json.loads(frame)
        message["payload_hex"] += "20"
        frame = json.dumps(message, separators=(",", ":")).encode("ascii")
    with socket.socket(socket.AF_UNIX) as conn:
        conn.settimeout(3)
        try:
            conn.connect(ingress)
        except PermissionError:
            if mode == "denied":
                print("SOCKET_ACCESS_DENIED")
                return 0
            return 1
        except OSError:
            # Missing socket/connection refusal is never positive evidence.
            return 1
        if mode == "denied":
            return 1
        send_frame(conn, frame)
        response = read_frame(conn, max_bytes=1024).decode("ascii")
        expected = {
            "authorized": "ACCEPTED",
            "replay": "REJECTED:BROKER_REPLAY",
            "tampered": "REJECTED:BROKER_UNAUTHORIZED",
            "forged-service": "REJECTED:BROKER_UNAUTHORIZED",
        }.get(mode)
        print(response)
        return 0 if response == expected else 1


def check_private(path: str) -> int:
    try:
        os.stat(path)
    except PermissionError:
        print("PRIVATE_DIRECTORY_DENIED")
        return 0
    except OSError:
        return 1
    return 1


def launch(
    role: str, args: list[str], uid: int, gid: int, groups: list[int]
) -> subprocess.Popen[str]:
    return subprocess.Popen(
        [sys.executable, __file__, "--role", role, *args],
        user=uid,
        group=gid,
        extra_groups=groups,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def run_case(
    ingress: str,
    db: str,
    case: str,
    raw_hex: str,
    nonce: str,
    stamp: str,
) -> bool:
    broker = launch("server", [ingress, db], BROKER_UID, BROKER_GROUP, [])
    assert broker.stdout is not None
    ready = broker.stdout.readline().strip()
    if ready != "READY":
        stderr = broker.stderr.read() if broker.stderr is not None else ""
        raise RuntimeError(f"broker did not initialize: {ready} {stderr[:160]}")
    if case in {"api-blocked", "unknown-blocked"}:
        uid, gid = (API_UID, API_GID) if case == "api-blocked" else (UNKNOWN_UID, UNKNOWN_GID)
        args = ["--role", "check-private", ingress]
        result = subprocess.run(
            [sys.executable, __file__, *args],
            user=uid,
            group=gid,
            extra_groups=[],
            capture_output=True,
            text=True,
            timeout=4,
            check=False,
        )
        passed = result.returncode == 0 and "PRIVATE_DIRECTORY_DENIED" in result.stdout
    else:
        result = subprocess.run(
            [sys.executable, __file__, "--role", "client", ingress, case, raw_hex, nonce, stamp],
            user=GATEWAY_UID,
            group=GATEWAY_GID,
            extra_groups=[BROKER_GROUP],
            capture_output=True,
            text=True,
            timeout=4,
            check=False,
        )
        passed = result.returncode == 0
    try:
        broker.wait(timeout=6)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("broker failed to stop naturally; do not add CAP_KILL") from exc
    return passed and broker.returncode == 0


def main() -> int:
    if sys.platform != "linux" or os.geteuid() != 0:
        raise SystemExit("REFUSED: requires root inside a disposable Linux sandbox")
    if os.getenv("SECOPS_DISPOSABLE_ACK") != "I_OWN_THIS_DISPOSABLE_SANDBOX":
        raise SystemExit("REFUSED: explicit disposable sandbox acknowledgment required")
    for uid in (API_UID, GATEWAY_UID, BROKER_UID, UNKNOWN_UID):
        try:
            pwd.getpwuid(uid)
        except KeyError:
            continue
        raise SystemExit(f"REFUSED: test UID {uid} already registered")
    with tempfile.TemporaryDirectory(prefix="secops-f121-") as tmp:
        root = Path(tmp)
        root.chmod(0o711)
        ingress_dir = root / "ingress"
        private_dir = root / "broker-private"
        ingress_dir.mkdir()
        private_dir.mkdir()
        ingress_dir.chmod(0o710)
        os.chown(ingress_dir, BROKER_UID, BROKER_GROUP)
        private_dir.chmod(0o700)
        os.chown(private_dir, BROKER_UID, BROKER_UID)
        ingress = str(ingress_dir / "gateway.sock")
        db = str(private_dir / "nonces.sqlite3")
        raw_hex = payload().hex()
        nonce = secrets.token_hex(16)
        stamp = str(int(time.time()))
        results: dict[str, bool] = {}
        try:
            for case in [
                "authorized",
                "replay",
                "tampered",
                "forged-service",
                "api-blocked",
                "unknown-blocked",
            ]:
                results[case.upper().replace("-", "_")] = run_case(
                    ingress, db, case, raw_hex, nonce, stamp
                )
            # Permissions measured only after reclaiming directories; no DAC override.
            os.chown(ingress_dir, 0, 0)
            os.chown(private_dir, 0, 0)
            results["INGRESS_DIRECTORY_0710"] = stat.S_IMODE(ingress_dir.stat().st_mode) == 0o710
            results["BROKER_DIRECTORY_0700"] = stat.S_IMODE(private_dir.stat().st_mode) == 0o700
            results["REPLAY_DB_0600"] = stat.S_IMODE(Path(db).stat().st_mode) == 0o600
            results["DISTINCT_UIDS"] = len({API_UID, GATEWAY_UID, BROKER_UID}) == 3
            print(
                json.dumps(
                    {"status": "PASS" if all(results.values()) else "FAIL", "checks": results},
                    sort_keys=True,
                )
            )
            return 0 if all(results.values()) else 1
        finally:
            os.chown(ingress_dir, 0, 0)
            os.chown(private_dir, 0, 0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", choices=["server", "client", "check-private"])
    parser.add_argument("args", nargs="*")
    opts = parser.parse_args()
    if opts.role == "server":
        sys.exit(server(*opts.args))
    if opts.role == "client":
        sys.exit(client(*opts.args))
    if opts.role == "check-private":
        sys.exit(check_private(*opts.args))
    sys.exit(main())
