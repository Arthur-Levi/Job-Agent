from enum import StrEnum

from sqlalchemy import CheckConstraint, Enum


def enum_column(enum_cls: type[StrEnum], name: str) -> Enum:
    """VARCHAR(32) + CHECK nomeada. `name` deve ser único por tabela (use o nome da coluna).

    length=32 fixo: valores novos (até 32 chars) não exigem ALTER COLUMN, só recriar a CHECK.
    """
    return Enum(
        enum_cls,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=32,
        validate_strings=True,
        values_callable=lambda members: [member.value for member in members],
    )


def nonblank(column: str) -> CheckConstraint:
    """Defesa em profundidade: o Pydantic já rejeita vazio; o banco rejeita ''/'   '."""
    return CheckConstraint(f"char_length(btrim({column})) > 0", name=f"nonblank_{column}")
