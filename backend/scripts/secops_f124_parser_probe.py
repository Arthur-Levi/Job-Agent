"""E2.2-F.1.2.4 opt-in host-side parser sandbox probe; synthetic files ONLY.

No customer CVs, APIs, databases or public routes. Requires a development
Docker daemon; do not execute against a production container runtime.
"""

import json
import sys

from app.workers.secops_synthetic_parser_lab import (
    ParserLabRejected,
    run_synthetic_parser_lab,
)


def main() -> int:
    try:
        checks = run_synthetic_parser_lab()
    except (ParserLabRejected, OSError, ValueError) as exc:
        code = str(exc) if isinstance(exc, ParserLabRejected) else "SECOPS_PROBE_FAILED"
        print(json.dumps({"status": "NO-GO", "reason": code}, sort_keys=True))
        return 1
    state = "PASS" if len(checks) == 12 and all(checks.values()) else "NO-GO"
    print(json.dumps({"status": state, "checks": checks}, sort_keys=True))
    return 0 if state == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
