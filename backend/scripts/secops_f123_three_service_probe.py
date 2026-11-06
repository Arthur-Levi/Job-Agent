"""F.1.2.3: opt-in 3-process, 3-UID signed IPC lab; no parser or user documents.

Run only inside a disposable Linux container with dropped capabilities and no
network, production secrets, DB, parser, or Docker socket.
"""

import argparse
import base64
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
)
from app.workers.broker_transport_wire import read_frame, receive_authenticated, send_frame
from app.workers.gateway_identity import AuthorizedWorkload, GatewayIdentityGate
from app.workers.job_admission import AdmissionService, MemoryAdmissionStore
from app.workers.secops_authenticated_chain import ChainRejected, encode_api_message, relay_one

API_UID, API_GID = 61001, 61010
GATEWAY_UID, GATEWAY_GID = 61002, 61010
BROKER_UID, BROKER_GROUP = 61003, 61020
UNAUTHORIZED_UID, UNAUTHORIZED_GID = 61004, 61004
API_SERVICE = "api-f123-lab"
GATEWAY_SERVICE = "gateway-f123-lab"
# Public fixture secrets: never usable in any real deployment.
API_KEY = b"f123-disposable-api-key-only-" + b"a" * 32
BROKER_KEY = b"f123-disposable-broker-key-only-" + b"b" * 32


def fake_envelope() -> bytes:
    return json.dumps(
        {
            "version": 1,
            "operation": "submit",
            "request_id": str(uuid4()),
            "idempotency_key": secrets.token_hex(16),
            "subject": {"user_id": str(uuid4()), "tenant_id": "synthetic-f123"},
            "payload": {
                "filename": "not-a-real-cv.txt",
                "content_b64": base64.b64encode(b"F123 SYNTHETIC ONLY").decode(),
            },
        },
        separators=(",", ":"),
    ).encode()


def connect_broker(path: str) -> socket.socket:
    sock = socket.socket(socket.AF_UNIX)
    sock.settimeout(2)
    try:
        sock.connect(path)
        return sock
    except OSError:
        sock.close()
        raise


def broker(ingress: str, db_path: str) -> int:
    os.umask(0o077)
    gate = BrokerTransportGate(
        GatewayWorkload(GATEWAY_SERVICE, GATEWAY_UID, GATEWAY_GID, BROKER_KEY),
        SqliteBrokerReplayStore(db_path),
        broker_uid=BROKER_UID,
    )
    with socket.socket(socket.AF_UNIX) as listener:
        listener.bind(ingress)
        os.chmod(ingress, 0o660)
        listener.listen(4)
        listener.settimeout(5)
        print("READY", flush=True)
        try:
            try:
                connection, _ = listener.accept()
            except TimeoutError:
                return 1
            with connection:
                connection.settimeout(3)
                try:
                    result = receive_authenticated(connection, gate)
                    send_frame(connection, ("ACCEPTED:" + result.digest).encode("ascii"))
                except (OSError, BrokerTransportRejected, ValueError):
                    send_frame(connection, b"DENIED")
            return 0
        finally:
            os.unlink(ingress)


def gateway(ingress: str, broker_path: str) -> int:
    gate = GatewayIdentityGate(
        (AuthorizedWorkload(API_SERVICE, API_UID, API_GID),),
        AdmissionService({API_SERVICE: API_KEY}, MemoryAdmissionStore()),
        broker_uid=BROKER_UID,
    )
    with socket.socket(socket.AF_UNIX) as listener:
        listener.bind(ingress)
        os.chmod(ingress, 0o660)
        listener.listen(4)
        listener.settimeout(5)
        print("READY", flush=True)
        try:
            for _ in range(3):
                try:
                    connection, _ = listener.accept()
                except TimeoutError:
                    return 1
                with connection:
                    connection.settimeout(3)
                    try:
                        result = relay_one(
                            connection,
                            broker_connect=lambda: connect_broker(broker_path),
                            api_gate=gate,
                            gateway_service_id=GATEWAY_SERVICE,
                            broker_secret=BROKER_KEY,
                            expected_broker_peer=(BROKER_UID, BROKER_GROUP),
                        )
                        send_frame(
                            connection, b"ACCEPTED" if result.broker_acknowledged else b"DENIED"
                        )
                    except (OSError, ChainRejected, ValueError):
                        send_frame(connection, b"DENIED")
            return 0
        finally:
            os.unlink(ingress)


def client(gateway_path: str, mode: str, hex_raw: str, nonce: str) -> int:
    raw = bytes.fromhex(hex_raw)
    signed = encode_api_message(
        raw,
        api_service_id=API_SERVICE,
        api_secret=API_KEY,
        timestamp=int(os.environ["SECOPS_F123_TIME"]),
        nonce=nonce,
    )
    if mode == "tampered":
        message = json.loads(signed)
        message["payload_hex"] += "20"
        signed = json.dumps(message, separators=(",", ":")).encode("ascii")
    with socket.socket(socket.AF_UNIX) as connection:
        connection.settimeout(4)
        connection.connect(gateway_path)
        send_frame(connection, signed)
        response = read_frame(connection, max_bytes=256)
        print(response.decode("ascii"))
        return 0 if response == (b"ACCEPTED" if mode == "authorized" else b"DENIED") else 1


def denied_path(path: str) -> int:
    try:
        os.stat(path)
    except PermissionError:
        print("PERMISSION_DENIED")
        return 0
    except OSError:
        return 1
    return 1


def launch(
    role: str, args: list[str], uid: int, gid: int, extra: list[int]
) -> subprocess.Popen[str]:
    return subprocess.Popen(
        [sys.executable, __file__, "--role", role, *args],
        user=uid,
        group=gid,
        extra_groups=extra,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def ready(proc: subprocess.Popen[str]) -> None:
    assert proc.stdout is not None
    if proc.stdout.readline().strip() != "READY":
        raise RuntimeError("synthetic service failed to start")


def run_client(gateway_path: str, mode: str, raw: bytes, nonce: str, stamp: int) -> bool:
    child = subprocess.run(
        [
            sys.executable,
            __file__,
            "--role",
            "client",
            gateway_path,
            mode,
            raw.hex(),
            nonce,
        ],
        user=API_UID,
        group=API_GID,
        extra_groups=[],
        env={**os.environ, "SECOPS_F123_TIME": str(stamp)},
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    expected = "ACCEPTED" if mode == "authorized" else "DENIED"
    return child.returncode == 0 and child.stdout.strip() == expected


def main() -> int:
    if sys.platform != "linux" or os.geteuid() != 0:
        raise SystemExit("REFUSED: disposable Linux root required")
    if os.getenv("SECOPS_DISPOSABLE_ACK") != "I_OWN_THIS_DISPOSABLE_SANDBOX":
        raise SystemExit("REFUSED: disposable sandbox acknowledgment required")
    for uid in (API_UID, GATEWAY_UID, BROKER_UID, UNAUTHORIZED_UID):
        try:
            pwd.getpwuid(uid)
        except KeyError:
            pass
        else:
            raise SystemExit("REFUSED: collision with existing test UID")

    with tempfile.TemporaryDirectory(prefix="secops-f123-") as tmp:
        root = Path(tmp)
        root.chmod(0o711)
        api_dir = root / "gateway"
        broker_dir = root / "broker-ingress"
        private_dir = root / "broker-private"
        for directory in (api_dir, broker_dir, private_dir):
            directory.mkdir()
        api_dir.chmod(0o770)
        os.chown(api_dir, GATEWAY_UID, GATEWAY_GID)
        broker_dir.chmod(0o710)
        os.chown(broker_dir, BROKER_UID, BROKER_GROUP)
        private_dir.chmod(0o700)
        os.chown(private_dir, BROKER_UID, BROKER_UID)

        gateway_path = str(api_dir / "gateway.sock")
        broker_path = str(broker_dir / "ingress.sock")
        db_path = str(private_dir / "nonces.sqlite3")
        workers: list[subprocess.Popen[str]] = []
        results: dict[str, bool] = {}
        try:
            bp = launch("broker", [broker_path, db_path], BROKER_UID, BROKER_GROUP, [])
            workers.append(bp)
            ready(bp)
            gp = launch(
                "gateway",
                [gateway_path, broker_path],
                GATEWAY_UID,
                GATEWAY_GID,
                [BROKER_GROUP],
            )
            workers.append(gp)
            ready(gp)
            # Prove filesystem denials while BOTH listeners are still alive.
            for name, uid, gid, path in (
                ("API_DIRECT_BROKER_DENIED", API_UID, API_GID, broker_path),
                ("UNKNOWN_GATEWAY_DENIED", UNAUTHORIZED_UID, UNAUTHORIZED_GID, gateway_path),
            ):
                attempt = subprocess.run(
                    [sys.executable, __file__, "--role", "denied", path],
                    user=uid,
                    group=gid,
                    extra_groups=[],
                    capture_output=True,
                    text=True,
                    timeout=4,
                    check=False,
                )
                results[name] = (
                    attempt.returncode == 0 and attempt.stdout.strip() == "PERMISSION_DENIED"
                )
            raw = fake_envelope()
            nonce = secrets.token_hex(16)
            stamp = int(time.time())
            results["AUTHORIZED_3_UID_HOPS"] = run_client(
                gateway_path, "authorized", raw, nonce, stamp
            )
            results["API_HMAC_TAMPERING_DENIED"] = run_client(
                gateway_path, "tampered", raw, secrets.token_hex(16), stamp
            )
            results["API_NONCE_REPLAY_DENIED"] = run_client(
                gateway_path, "replay", raw, nonce, stamp
            )

            for process in workers:
                process.wait(timeout=8)
            results["SERVICES_EXIT_ZERO"] = all(p.returncode == 0 for p in workers)
            os.chown(api_dir, 0, 0)
            os.chown(broker_dir, 0, 0)
            os.chown(private_dir, 0, 0)
            results["GATEWAY_DIRECTORY_0770"] = stat.S_IMODE(api_dir.stat().st_mode) == 0o770
            results["BROKER_INGRESS_0710"] = stat.S_IMODE(broker_dir.stat().st_mode) == 0o710
            results["BROKER_PRIVATE_0700"] = stat.S_IMODE(private_dir.stat().st_mode) == 0o700
            results["REPLAY_DB_0600"] = stat.S_IMODE(Path(db_path).stat().st_mode) == 0o600
            results["SEPARATE_UIDS"] = len({API_UID, GATEWAY_UID, BROKER_UID}) == 3
            print(
                json.dumps(
                    {"status": "PASS" if all(results.values()) else "FAIL", "checks": results},
                    sort_keys=True,
                )
            )
            return 0 if all(results.values()) else 1
        finally:
            # No CAP_KILL: services exit naturally after bounded accepts and timeouts.
            os.chown(api_dir, 0, 0)
            os.chown(broker_dir, 0, 0)
            os.chown(private_dir, 0, 0)
            for process in workers:
                try:
                    process.wait(timeout=8)
                except subprocess.TimeoutExpired as exc:
                    raise RuntimeError("synthetic service did not stop") from exc


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", choices=["broker", "gateway", "client", "denied"])
    parser.add_argument("args", nargs="*")
    opts = parser.parse_args()
    if opts.role == "broker":
        sys.exit(broker(*opts.args))
    if opts.role == "gateway":
        sys.exit(gateway(*opts.args))
    if opts.role == "client":
        sys.exit(client(*opts.args))
    if opts.role == "denied":
        sys.exit(denied_path(*opts.args))
    sys.exit(main())
