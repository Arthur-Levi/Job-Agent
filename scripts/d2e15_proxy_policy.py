"""D2-E1.5: validate public reverse-proxy settings before launch.

This is intentionally a dry-run policy gate, not an API launcher. Never infer
that a successful dry run means HTTPS, firewall, or proxy are deployed.
"""
from __future__ import annotations

import argparse
import ipaddress
import sys


def validate(*, bind: str, trusted_proxy: str, https_origin: str) -> list[str]:
    bind_ip = ipaddress.ip_address(bind)
    if not bind_ip.is_loopback:
        raise ValueError("FastAPI must bind to loopback behind the reverse proxy")
    if "*" in trusted_proxy:
        raise ValueError("Wildcard trusted proxies are forbidden")
    proxies = [part.strip() for part in trusted_proxy.split(",") if part.strip()]
    if not proxies:
        raise ValueError("An explicit trusted-proxy allowlist is required")
    for item in proxies:
        network = ipaddress.ip_network(item, strict=False)
        if network.prefixlen == 0:
            raise ValueError("Trust-all network is forbidden")
        if network.num_addresses > 256:
            raise ValueError("Overly broad trusted-proxy network")
        if not (network.is_private or network.is_loopback):
            raise ValueError("Public proxy IPs require dedicated security approval")
    if not https_origin.startswith("https://"):
        raise ValueError("Public frontend origin must use HTTPS")
    if any(c in https_origin for c in ("*", " ", ",", "\\", "#", "@")):
        raise ValueError("Invalid public origin")
    if "/" in https_origin.removeprefix("https://"):
        raise ValueError("Frontend origin must contain no path")
    return [
        "uvicorn", "app.main:create_app", "--factory",
        "--host", bind, "--port", "18081",
        "--proxy-headers", "--forwarded-allow-ips", trusted_proxy,
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bind", required=True)
    parser.add_argument("--trusted-proxy", required=True)
    parser.add_argument("--https-origin", required=True)
    args = parser.parse_args()
    try:
        validate(
            bind=args.bind, trusted_proxy=args.trusted_proxy,
            https_origin=args.https_origin,
        )
    except ValueError as exc:
        print(f"PROXY POLICY FAIL: {exc}", file=sys.stderr)
        return 1
    print("D2-E1.5 PROXY POLICY DRY-RUN PASS")
    print("Required separate checks: TLS, ingress rewrite of forwarding headers,")
    print("firewall preventing direct API access, and real multi-IP proxy integration.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
