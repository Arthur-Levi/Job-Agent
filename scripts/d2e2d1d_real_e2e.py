"""Isolated real-HTTP browser -> API -> PostgreSQL acceptance.

CI ONLY: backend settings must be APP_ENV=test, non-production subprocess parser
must process SYNTHETIC input, and PostgreSQL is an ephemeral GitHub Actions service.
No mocks, customer documents, Codespaces databases, or Docker daemon.
"""

import os
import uuid
from pathlib import Path

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
            page.get_by_role("link", name="Diagnóstico", exact=True).click()
            page.get_by_role("heading", name="Diagnóstico de carreira").wait_for(timeout=15000)
            page.get_by_role("heading", name="Experiências profissionais").wait_for()
            page.get_by_role("heading", name="Formação").wait_for()
            page.get_by_text("Analista de Dados", exact=True).wait_for()
            page.get_by_text("Assistente Administrativo", exact=True).wait_for()
            page.get_by_text("Declaração do candidato (sem verificação externa)").first.wait_for()
            page.get_by_text("Sem registros documentados nesta categoria").first.wait_for()
            assert page.get_by_text("Nenhum fato foi criado ou alterado por esta análise.").is_visible()
            with page.expect_response("**/api/v1/career/resume-export/preview") as preview_info:
                page.get_by_role("link", name="Exportar currículo", exact=True).click()
            approved_digest = preview_info.value.json()["approval_sha256"]
            page.get_by_role("heading", name="Revisar e exportar currículo").wait_for()
            page.get_by_text("Pessoa Sintetica", exact=True).wait_for()
            assert page.get_by_role("button", name="Baixar PDF").is_disabled()
            page.get_by_role("checkbox").check()
            with page.expect_download(timeout=15000) as download_info:
                page.get_by_role("button", name="Baixar PDF").click()
            assert download_info.value.suggested_filename == "job-agent-resume.pdf"
            artifacts = os.getenv("E2E_ACCEPTANCE_ARTIFACT_DIR")
            if artifacts:
                directory = Path(artifacts)
                directory.mkdir(parents=True, exist_ok=True)
                download_info.value.save_as(directory / "synthetic-resume.pdf")
            with page.expect_download(timeout=15000) as download_info:
                page.get_by_role("button", name="Baixar DOCX").click()
            assert download_info.value.suggested_filename == "job-agent-resume.docx"
            if artifacts:
                download_info.value.save_as(directory / "synthetic-resume.docx")
            print("D2-E2.F.4 real browser PDF/DOCX approval PASS (synthetic only)")

            page.get_by_role("link", name="Matching de vagas", exact=True).click()
            page.get_by_role("heading", name="Matching explicável").wait_for()
            page.get_by_label("Título da vaga").fill("Analista de Dados")
            page.get_by_placeholder("Escreva exatamente como no fato").fill("Kubernetes")
            assert page.get_by_role("button", name="Comparar com meu Fact Ledger").is_disabled()
            page.get_by_role("checkbox").check()
            page.get_by_role("button", name="Comparar com meu Fact Ledger").click()
            page.get_by_text("Não documentado", exact=True).wait_for(timeout=15000)
            page.get_by_text("Isso não comprova ausência da competência", exact=False).wait_for()
            print("D2-E2.F.4 real browser vacancy uncertainty PASS (synthetic only)")

            # A completely independent account must not access the prior user's
            # facts, diagnosis, document or inferred vacancy evidence.
            other_email = f"browser-isolation-{uuid.uuid4().hex}@example.com"
            registration = page.request.post(
                BACKEND + "/api/v1/auth/register",
                data={"name": "Outro Candidato Sintetico", "email": other_email,
                      "password": password},
            )
            assert registration.status == 201
            other_login = page.request.post(
                BACKEND + "/api/v1/auth/login",
                data={"email": other_email, "password": password},
            )
            assert other_login.status == 200
            other_token = other_login.json()["access_token"]
            other_headers = {"Authorization": "Bearer " + other_token}
            other_profile = page.request.get(
                BACKEND + "/api/v1/career/profile", headers=other_headers
            )
            assert other_profile.status == 200
            assert other_profile.json()["items"] == []
            other_ledger = page.request.get(
                BACKEND + "/api/v1/career/facts", headers=other_headers
            )
            assert other_ledger.status == 200
            assert other_ledger.json()["items"] == []
            other_diagnostic = page.request.get(
                BACKEND + "/api/v1/career/diagnostic", headers=other_headers
            )
            assert other_diagnostic.status == 200
            assert other_diagnostic.json()["total_active_facts"] == 0
            other_match = page.request.post(
                BACKEND + "/api/v1/career/vacancy-match", headers=other_headers,
                data={"vacancy_title": "Analista de Dados",
                      "requirements": [{"category": "experience",
                                        "name": "Analista de Dados",
                                        "importance": "required"}]},
            )
            assert other_match.status == 200
            assert other_match.json()["requirements"][0]["classification"] == "not_documented"
            cross_export = page.request.post(
                BACKEND + "/api/v1/career/resume-export/pdf",
                headers=other_headers,
                data={"approved": True, "approval_sha256": approved_digest},
            )
            assert cross_export.status == 409
            unauth = page.request.get(BACKEND + "/api/v1/career/resume-export/preview")
            assert unauth.status == 401
            logout = page.request.post(
                BACKEND + "/api/v1/auth/logout", headers=other_headers
            )
            assert logout.status == 204
            revoked = page.request.get(
                BACKEND + "/api/v1/career/diagnostic", headers=other_headers
            )
            assert revoked.status == 401
            print("D2-E2.F.5 cross-account and revoked-session isolation PASS")

            # Basic keyboard and accessible-name smoke (NOT a WCAG audit).
            review_link = page.get_by_role("link", name="Exportar currículo", exact=True)
            review_link.focus()
            page.keyboard.press("Enter")
            page.get_by_role("heading", name="Revisar e exportar currículo").wait_for()
            approval_box = page.get_by_role("checkbox")
            approval_box.focus()
            page.keyboard.press("Space")
            assert approval_box.is_checked()
            assert page.get_by_role("button", name="Baixar PDF").is_enabled()
            assert page.locator("main input").evaluate_all(
                "(fields) => fields.every(field => field.labels && field.labels.length > 0)"
            )
            matching_link = page.get_by_role("link", name="Matching de vagas", exact=True)
            matching_link.focus()
            page.keyboard.press("Enter")
            page.get_by_role("heading", name="Matching explicável").wait_for()
            assert page.get_by_label("Título da vaga").is_visible()
            print("D2-E2.F.5 keyboard navigation and form label smoke PASS")


            print("D2-E2.E.2 diagnostic React/API/PostgreSQL PASS (synthetic only)")
            print("D2-E2.D.1-D real browser/API/PostgreSQL PASS (synthetic only)")
        finally:
            browser.close()


if __name__ == "__main__":
    main()
