"""Test-only email transport. Never sends external messages or logs secret links."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MailMessage:
    recipient: str
    subject: str
    link: str


@dataclass
class MemoryMailer:
    messages: list[MailMessage] = field(default_factory=list)

    def send(self, recipient: str, subject: str, link: str) -> None:
        self.messages.append(MailMessage(recipient=recipient, subject=subject, link=link))
