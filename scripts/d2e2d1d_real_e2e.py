"""Isolated real-HTTP browser -> API -> PostgreSQL acceptance.

CI ONLY: backend settings must be APP_ENV=test, non-production subprocess parser
must process SYNTHETIC input, and PostgreSQL is an ephemeral GitHub Actions service.
No mocks, customer documents, Codespaces databases, or Docker daemon.
"""

import os
import uuid

from playwright.sync_api import sync_playwright

FRONTEND = "http://127.0.0.1:5173"
BACKEND = "http://127.0.0.1:8000"
CV_TEXT = (
    "Pessoa sintetica de teste\n"
    "Contato: e2e@example.invalid\n"
    "Experiencia profissional\n"
    "Empresa Exemplo | Analista de Dados | 2023-2024\n"
    "Criou dashboards sinteticos de Power BI.\n"
    "Empresa Exemplo | Assistente Administrativo | 2021-2022\n"
    "Atualizou planilhas de teste.\n"
    "Habilidades\n"
    "Excel\n"
).encode()


def login(page: object, email: str, password: str) -> None:
    page.get_by_label("Email").fill(email)
    page.get_by_label("Senha").fill(password)
    page.get_by_role("button", name="Entrar", exact=True).click()
    page.get_by_role("link", name="Importar currículo").wait_for(timeout=15000)


def main() -> None:
    if (
        os.getenv("CI") != "true"
        or os.getenv("E2E_DISPOSABLE_DATABASE") != "1"
        or os.getenv("APP_ENV") != "test"
    ):
        raise SystemExit("Refusing real-HTTP E2E outside ephemeral GitHub CI test environment")

    email = f"browser-e2e-{uuid.uuid4().hex}@example.com"
    password = "Synthetic-Only-Password-2026!"
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.on(
            "response",
            lambda response: print(
                "E2E HTTP",
                response.request.method,
                response.url.split("/api/v1/")[-1],
                response.status,
            )
            if "/api/v1/" in response.url
            else None,
        )
        try:
            page.goto(FRONTEND + "/register")
            page.get_by_label("Nome").fill("Pessoa Sintetica")
            page.get_by_label("Email").fill(email)
            page.get_by_label("Senha (12 a 128 caracteres)").fill(password)
            page.get_by_role("button", name="Criar conta").click()
            try:
                page.get_by_role("link", name="Ir para login").wait_for(timeout=15000)
            except Exception:
                print("E2E registration UI status:", page.locator("main").inner_text()[:600])
                raise
            page.get_by_role("link", name="Ir para login").click()
            login(page, email, password)

            page.get_by_role("link", name="Importar currículo").click()
            page.locator("#resume-file").set_input_files(
                {"name": "synthetic.txt", "mimeType": "text/plain", "buffer": CV_TEXT}
            )
            page.get_by_role("button", name="Verificar leitura do currículo").click()
            page.get_by_text("Itens sugeridos para revisão", exact=False).wait_for(timeout=20000)
            assert page.get_by_text("Item 1 · experience").is_visible()
            assert page.get_by_text("Item 2 · experience").is_visible()

            page.get_by_label("Descrição").first.fill("Descricao sintética revisada")
            page.get_by_label("Revisei as sugestões e entendo que são declarações não verificadas.").check()
            page.get_by_role("button", name="Confirmar e salvar fatos no perfil").click()
            page.get_by_text("Confirmação salva!", exact=False).wait_for(timeout=20000)
            page.get_by_role("link", name="Consultar Fact Ledger e Master Profile").click()
            page.get_by_text("Analista de Dados", exact=True).wait_for(timeout=15000)
            page.get_by_text("Assistente Administrativo", exact=True).wait_for()
            page.get_by_role("button", name="Corrigir fato").first.click()
            page.get_by_label("Descrição corrigida").fill("Corrigida no browser com API real")
            page.get_by_label("Motivo da correção").fill("Revisao sintetica E2E")
            page.get_by_role("button", name="Salvar nova versão").click()
            page.get_by_text("Corrigida no browser com API real", exact=False).wait_for()
            page.get_by_label("Mostrar versões substituídas e rejeitadas").check()
            page.get_by_text("SUPERSEDED", exact=False).wait_for(timeout=15000)

            # Memory-only session intentionally clears on refresh, but DB data remains.
            page.reload()
            page.get_by_role("heading", name="Entrar na sua conta").wait_for(timeout=15000)
            login(page, email, password)
            page.get_by_role("link", name="Master Profile").click()
            page.get_by_text("Corrigida no browser com API real", exact=False).wait_for(
                timeout=15000
            )
            print("D2-E2.D.1-D real browser/API/PostgreSQL PASS (synthetic only)")
        finally:
            browser.close()


if __name__ == "__main__":
    main()
