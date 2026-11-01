"""Transactional identity email delivery. No secret URLs, tokens or keys in logs.

Resend's POST /emails supports Idempotency-Key for safe bounded retries.
Transport is synchronous intentionally; a durable outbox is a later release gate.
"""

import hashlib
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


class _RejectRedirect(urllib.request.HTTPRedirectHandler):
    """Never forward the provider authorization header to a redirected host."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


class EmailDeliveryUnavailable(Exception):
    """Generic failure: deliberately never contains response bodies or credentials."""


@runtime_checkable
class Mailer(Protocol):
    def send(self, recipient: str, subject: str, link: str) -> None: ...


@dataclass(frozen=True)
class MailMessage:
    recipient: str
    subject: str
    link: str


@dataclass
class MemoryMailer:
    """Synthetic-only outbox. Never send to an external network."""

    messages: list[MailMessage] = field(default_factory=list)

    def send(self, recipient: str, subject: str, link: str) -> None:
        self.messages.append(MailMessage(recipient=recipient, subject=subject, link=link))


@dataclass(frozen=True)
class ResendMailer:
    api_key: str
    from_address: str
    timeout_seconds: float = 5.0
    # This endpoint is fixed: callers cannot redirect bearer credentials to a host.
    endpoint: str = "https://api.resend.com/emails"

    def send(self, recipient: str, subject: str, link: str) -> None:
        if not self.api_key or not self.from_address:
            raise EmailDeliveryUnavailable("Email service not configured")
        # The action link is intentionally only in the HTTPS request body.
        payload = json.dumps(
            {
                "from": self.from_address,
                "to": [recipient],
                "subject": subject,
                "text": (
                    "Esta mensagem foi solicitada para sua conta Job Agent.\n"
                    "Abra o link abaixo para continuar:\n"
                    f"{link}\n\n"
                    "Se voce nao solicitou esta acao, ignore esta mensagem."
                ),
            },
            ensure_ascii=False,
        ).encode("utf-8")
        # Same payload and token => same key within Resend's idempotency window.
        key = "jobagent-" + hashlib.sha256(payload).hexdigest()
        opener = urllib.request.build_opener(_RejectRedirect())
        for attempt in range(3):
            request = urllib.request.Request(
                self.endpoint,
                data=payload,
                method="POST",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "Idempotency-Key": key,
                    "User-Agent": "JobAgent-Transactional/1",
                },
            )
            try:
                with opener.open(request, timeout=self.timeout_seconds) as response:
                    if response.status != 200:
                        raise EmailDeliveryUnavailable("Email provider rejected request")
                    result = json.loads(response.read(16_384))
                    if not isinstance(result, dict) or not isinstance(result.get("id"), str):
                        raise EmailDeliveryUnavailable("Email provider response invalid")
                    return
            except urllib.error.HTTPError as exc:
                # Never read or log response body: may contain sensitive provider details.
                if exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                    raise EmailDeliveryUnavailable("Email provider request failed") from None
            except (urllib.error.URLError, TimeoutError, OSError):
                if attempt == 2:
                    raise EmailDeliveryUnavailable("Email provider unavailable") from None
            except (ValueError, UnicodeError):
                raise EmailDeliveryUnavailable("Email provider response invalid") from None
            # Bounded retry with the SAME Idempotency-Key; max 2 waits.
            time.sleep(0.25 * (2**attempt))
        raise EmailDeliveryUnavailable("Email provider unavailable")
