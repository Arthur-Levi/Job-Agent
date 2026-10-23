import pytest

from app.domain.application_status import (
    PIPELINE,
    TRANSITIONS,
    InvalidStatusTransition,
    validate_transition,
)
from app.domain.enums import ApplicationStatus as S


def test_every_status_has_an_entry() -> None:
    assert set(TRANSITIONS) == set(S)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (S.DISCOVERED, S.QUALIFIED),
        (S.QUALIFIED, S.PREPARED),
        (S.PREPARED, S.READY),
        (S.READY, S.APPLIED),
        (S.APPLIED, S.RESPONSE),
        (S.RESPONSE, S.INTERVIEW),
        (S.INTERVIEW, S.TECHNICAL),
        (S.TECHNICAL, S.OFFER),
        (S.DISCOVERED, S.WITHDRAWN),
        (S.OFFER, S.WITHDRAWN),
        (S.APPLIED, S.REJECTED),
        (S.OFFER, S.REJECTED),
        (S.APPLIED, S.GHOSTED),
        (S.TECHNICAL, S.GHOSTED),
        (S.GHOSTED, S.RESPONSE),
        (S.GHOSTED, S.REJECTED),
    ],
)
def test_allowed_transitions(current: S, target: S) -> None:
    validate_transition(current, target)  # não levanta


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (S.DISCOVERED, S.OFFER),  # pular etapas
        (S.DISCOVERED, S.APPLIED),
        (S.READY, S.PREPARED),  # voltar
        (S.DISCOVERED, S.REJECTED),  # empresa só recusa depois de candidatura
        (S.READY, S.GHOSTED),
        (S.OFFER, S.GHOSTED),
        (S.REJECTED, S.RESPONSE),  # terminais
        (S.WITHDRAWN, S.DISCOVERED),
    ],
)
def test_disallowed_transitions(current: S, target: S) -> None:
    with pytest.raises(InvalidStatusTransition) as info:
        validate_transition(current, target)
    assert info.value.current is current
    assert info.value.target is target
    assert info.value.allowed == sorted(s.value for s in TRANSITIONS[current])


def test_terminal_statuses_have_no_exits() -> None:
    assert TRANSITIONS[S.REJECTED] == frozenset()
    assert TRANSITIONS[S.WITHDRAWN] == frozenset()


def test_force_bypasses_the_policy() -> None:
    validate_transition(S.DISCOVERED, S.OFFER, force=True)
    validate_transition(S.REJECTED, S.DISCOVERED, force=True)


def test_same_status_is_a_caller_bug() -> None:
    with pytest.raises(ValueError):
        validate_transition(S.READY, S.READY)


def test_pipeline_covers_the_main_chain_once() -> None:
    assert len(PIPELINE) == len(set(PIPELINE)) == 9
