"""Política única de transições de ApplicationStatus (máquina de estados V0).

Regras (sem `force`):
- avanço de UM passo no pipeline:
  DISCOVERED → QUALIFIED → PREPARED → READY → APPLIED → RESPONSE → INTERVIEW → TECHNICAL → OFFER
- WITHDRAWN (o usuário desiste): a partir de qualquer estágio do pipeline.
- REJECTED (a empresa recusa): a partir de APPLIED em diante (inclui OFFER, oferta retirada).
- GHOSTED (a empresa some): de APPLIED a TECHNICAL. De GHOSTED é possível voltar a RESPONSE,
  ou encerrar em REJECTED/WITHDRAWN.
- REJECTED e WITHDRAWN são terminais.

Correções administrativas (voltar etapa, pular etapa, reabrir) exigem `force=True`; o service
registra `{"forced": true}` no evento, então nunca passam despercebidas.
"""

from collections.abc import Mapping
from itertools import pairwise
from types import MappingProxyType

from app.domain.enums import ApplicationStatus as S

PIPELINE: tuple[S, ...] = (
    S.DISCOVERED,
    S.QUALIFIED,
    S.PREPARED,
    S.READY,
    S.APPLIED,
    S.RESPONSE,
    S.INTERVIEW,
    S.TECHNICAL,
    S.OFFER,
)
_AFTER_APPLY = frozenset({S.APPLIED, S.RESPONSE, S.INTERVIEW, S.TECHNICAL})


def _build() -> dict[S, frozenset[S]]:
    allowed: dict[S, set[S]] = {status: set() for status in S}
    for current, following in pairwise(PIPELINE):
        allowed[current].add(following)
    for status in PIPELINE:
        allowed[status].add(S.WITHDRAWN)
    for status in _AFTER_APPLY | {S.OFFER}:
        allowed[status].add(S.REJECTED)
    for status in _AFTER_APPLY:
        allowed[status].add(S.GHOSTED)
    allowed[S.GHOSTED] = {S.RESPONSE, S.REJECTED, S.WITHDRAWN}
    return {status: frozenset(targets) for status, targets in allowed.items()}


TRANSITIONS: Mapping[S, frozenset[S]] = MappingProxyType(_build())


class InvalidStatusTransition(Exception):
    def __init__(self, current: S, target: S) -> None:
        self.current = current
        self.target = target
        self.allowed = sorted(status.value for status in TRANSITIONS[current])
        super().__init__(f"{current.value} -> {target.value} is not allowed")


def validate_transition(current: S, target: S, *, force: bool = False) -> None:
    """Levanta InvalidStatusTransition. `current == target` é no-op e deve ser tratado antes."""
    if current == target:
        raise ValueError("current and target are the same status; handle as a no-op")
    if force:
        return
    if target not in TRANSITIONS[current]:
        raise InvalidStatusTransition(current, target)
