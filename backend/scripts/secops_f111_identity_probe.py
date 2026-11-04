"""E2.2-F.1.1: disposable Linux multi-UID Unix socket probe; no CV, DB or Docker."""
import argparse
import json
import os
import pwd
import socket
import stat
import subprocess
import sys
import tempfile
from pathlib import Path


def client(path: str, outcome: str) -> int:
    sock = socket.socket(socket.AF_UNIX)
    try:
        sock.settimeout(2)
        sock.connect(path)
        reply = sock.recv(100).decode()
        ok = reply == outcome
    except (PermissionError, FileNotFoundError, ConnectionRefusedError, socket.timeout, OSError):
        ok = outcome == "DENIED"
    finally:
        sock.close()
    return 0 if ok else 1


def server(role: str, path: str) -> int:
    listener = socket.socket(socket.AF_UNIX)
    try:
        listener.bind(path)
        os.chmod(path, 0o600 if role == "broker" else 0o660)
        listener.listen(8)
        print("READY", flush=True)
        for _ in range(3):
            listener.settimeout(5)
            try:
                conn, _ = listener.accept()
            except socket.timeout:
                break
            with conn:
                if role == "gateway":
                    import struct

                    raw = conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12)
                    _pid, uid, gid = struct.unpack("3i", raw)
                    conn.sendall(b"ALLOWED" if (uid, gid) == (61001, 61010) else b"DENIED")
                else:
                    conn.sendall(b"BROKER")
        return 0
    finally:
        listener.close()


def main() -> int:
    if sys.platform != "linux" or os.geteuid() != 0:
        raise SystemExit("SKIP: requires root inside an owned disposable Linux sandbox")
    if os.getenv("SECOPS_DISPOSABLE_ACK") != "I_OWN_THIS_DISPOSABLE_SANDBOX":
        raise SystemExit("REFUSED: explicit disposable sandbox acknowledgement required")
    for uid in (61001, 61002, 61003, 61004):
        try:
            pwd.getpwuid(uid)
        except KeyError:
            pass
        else:
            raise SystemExit(f"REFUSED: reserved test UID {uid} exists")
    with tempfile.TemporaryDirectory(prefix="secops-f111-") as tmp:
        root = Path(tmp)
        root.chmod(0o711)
        gateway_dir = root / "gateway"
        broker_dir = root / "broker"
        gateway_dir.mkdir()
        broker_dir.mkdir()
        os.chown(gateway_dir, 61002, 61010)
        os.chmod(gateway_dir, 0o770)
        os.chown(broker_dir, 61003, 61003)
        os.chmod(broker_dir, 0o700)
        gw_sock = str(gateway_dir / "gateway.sock")
        br_sock = str(broker_dir / "broker.sock")
        workers = []
        try:
            for role, path, uid, gid in [
                ("gateway", gw_sock, 61002, 61010),
                ("broker", br_sock, 61003, 61003),
            ]:
                proc = subprocess.Popen(
                    [sys.executable, __file__, "--server", role, path],
                    user=uid,
                    group=gid,
                    extra_groups=[],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                workers.append(proc)
                assert proc.stdout is not None
                ready = proc.stdout.readline().strip()
                if ready != "READY":
                    raise RuntimeError(f"{role} did not initialize: {ready}")
            cases = [
                ("API_TO_GATEWAY", 61001, 61010, gw_sock, "ALLOWED"),
                ("API_TO_BROKER_DENIED", 61001, 61010, br_sock, "DENIED"),
                ("GATEWAY_TO_BROKER_DENIED", 61002, 61010, br_sock, "DENIED"),
                ("UNAUTHORIZED_TO_GATEWAY_DENIED", 61004, 61004, gw_sock, "DENIED"),
            ]
            results = {}
            for name, uid, gid, path, expectation in cases:
                outcome = subprocess.run(
                    [sys.executable, __file__, "--client", path, expectation],
                    user=uid,
                    group=gid,
                    extra_groups=[],
                    capture_output=True,
                    text=True,
                    timeout=4,
                    check=False,
                )
                results[name] = outcome.returncode == 0
            results["GATEWAY_SOCKET_MODE"] = stat.S_IMODE(os.stat(gw_sock).st_mode) == 0o660
            results["BROKER_SOCKET_MODE"] = stat.S_IMODE(os.stat(br_sock).st_mode) == 0o600
            results["BROKER_DIRECTORY_MODE"] = stat.S_IMODE(os.stat(broker_dir).st_mode) == 0o700
            results["DISTINCT_SERVICE_UIDS"] = len({61001, 61002, 61003}) == 3
            print(json.dumps({
                "status": "PASS" if all(results.values()) else "FAIL",
                "checks": results,
            }, sort_keys=True))
            return 0 if all(results.values()) else 1
        finally:
            for proc in workers:
                proc.terminate()
            for proc in workers:
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--client", nargs=2)
    parser.add_argument("--server", nargs=2)
    args = parser.parse_args()
    if args.client:
        sys.exit(client(*args.client))
    if args.server:
        sys.exit(server(*args.server))
    sys.exit(main())
