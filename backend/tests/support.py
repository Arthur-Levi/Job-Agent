import os

from sqlalchemy.engine import make_url


def safe_test_database_url() -> str | None:
    """Devolve TEST_DATABASE_URL se definida e segura; None se não definida.

    Falha ALTO (RuntimeError) se o nome do banco não terminar em "_test": é o que
    impede os testes de rodarem por acidente contra o banco de desenvolvimento.
    """
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        return None
    database = make_url(url).database or ""
    if not database.endswith("_test"):
        raise RuntimeError("TEST_DATABASE_URL must point to a database whose name ends in '_test'")
    return url
