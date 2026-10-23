from decimal import Decimal
from typing import Annotated, Any

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    HttpUrl,
    StringConstraints,
    TypeAdapter,
)

DEFAULT_LIMIT = 20
MAX_LIMIT = 100
MAX_OFFSET = 1_000_000

_HTTP_URL = TypeAdapter(HttpUrl)
_MAX_URL_LENGTH = 2048


class StrictModel(BaseModel):
    """Entrada: campos desconhecidos viram 422 (typos em PATCH não passam em silêncio)."""

    model_config = ConfigDict(extra="forbid")


class ReadModel(BaseModel):
    """Saída: construído a partir de objetos ORM, que nunca são devolvidos diretamente."""

    model_config = ConfigDict(from_attributes=True)


class Page[T](BaseModel):
    items: list[T]
    total: int
    limit: int
    offset: int


def _blank_to_none(value: Any) -> Any:
    """Campos opcionais: string vazia/em branco equivale a "não informado"."""
    if isinstance(value, str) and not value.strip():
        return None
    return value


def _http_url(value: str) -> str:
    normalized = str(_HTTP_URL.validate_python(value))  # só http/https
    if len(normalized) > _MAX_URL_LENGTH:
        raise ValueError(f"URL must have at most {_MAX_URL_LENGTH} characters")
    return normalized


def _normalize_currency(value: Any) -> Any:
    value = _blank_to_none(value)
    return value.strip().upper() if isinstance(value, str) else value


# Obrigatórios: sem espaços nas pontas, nunca vazios.
RequiredName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]
RequiredText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50_000)
]

# Opcionais: "" vira None. As restrições valem só para o ramo `str` (não para o None).
_Text100 = Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)]
_Text200 = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]
_LongText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=50_000)]
_Url = Annotated[str, StringConstraints(strip_whitespace=True), AfterValidator(_http_url)]
_Currency = Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]

OptionalText100 = Annotated[_Text100 | None, BeforeValidator(_blank_to_none)]
OptionalText200 = Annotated[_Text200 | None, BeforeValidator(_blank_to_none)]
OptionalLongText = Annotated[_LongText | None, BeforeValidator(_blank_to_none)]
OptionalUrl = Annotated[_Url | None, BeforeValidator(_blank_to_none)]
CurrencyCode = Annotated[_Currency | None, BeforeValidator(_normalize_currency)]
# Dinheiro como Decimal (JSON: string, ex. "5000.00"); casa com NUMERIC(12,2).
Money = Annotated[Decimal | None, Field(ge=0, max_digits=12, decimal_places=2)]
