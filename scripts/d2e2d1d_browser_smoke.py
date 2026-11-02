"""Chromium UI smoke: synthetic-only HTTP fixtures, no DB or external APIs.

This verifies actual browser interactions and routing. PostgreSQL integration
is exercised by separate backend CI tests; do not call this a database E2E.
"""

import json
from urllib.parse import urlparse

from playwright.sync_api import Route, sync_playwright

APP_URL = "http://127.0.0.1:5173"
TOKEN = "synthetic-browser-session-token-" + "a" * 40
USER = {"id": "synthetic-user", "name": "Pessoa Sintetica", "email": "browser@example.invalid"}
ORIGINAL = [
    {
        "draft_id": "00000000-0000-4000-8000-000000000001",
        "category": "experience",
        "title": "Analista de Dados",
        "description": "Dashboards sinteticos",
        "organization": "Empresa Exemplo",
        "start_date": "2023",
        "end_date": "2024",
        "source_excerpt": "Empresa Exemplo | Analista de Dados",
        "review_status": "pending",
        "warnings": [],
    },
    {
        "draft_id": "00000000-0000-4000-8000-000000000002",
        "category": "skill",
        "title": "Excel",
        "description": "Habilidade sintetica",
        "organization": None,
        "start_date": None,
        "end_date": None,
        "source_excerpt": "Excel",
        "review_status": "pending",
        "warnings": [],
    },
]
PREVIEW = {
    "preview_id": "00000000-0000-4000-8000-000000000010",
    "preview_ticket": "synthetic-ticket-only",
    "format": "txt",
    "character_count": 170,
    "sections_detected": ["experience", "skills"],
    "fields_detected": {"email": True, "phone": False},
    "items": ORIGINAL,
    "limitations": ["Leia os dados antes de confirmar."],
    "ats_check": {
        "method": "local_text_parser",
        "text_extractable": True,
        "sections_detected": ["experience"],
        "unrecognized_fields": [],
        "notice": "Nao ha certificacao ATS externa.",
    },
}


def main() -> None:
    stored: list[dict] = []
    versions: list[dict] = []
    calls = {"preview": 0, "confirm": 0, "correction": 0}

    def api(route: Route) -> None:
        request = route.request
        path = urlparse(request.url).path
        method = request.method
        status = 200
        body: dict | list = {}

        if path == "/api/v1/auth/login" and method == "POST":
            body = {"access_token": TOKEN, "token_type": "bearer"}
        elif path == "/api/v1/auth/me" and method == "GET":
            body = USER
        elif path == "/api/v1/resume-imports/preview" and method == "POST":
            calls["preview"] += 1
            body = PREVIEW
        elif path == "/api/v1/resume-imports/confirm" and method == "POST":
            calls["confirm"] += 1
            payload = request.post_data_json
            assert payload["preview_ticket"] == PREVIEW["preview_ticket"]
            assert request.headers.get("idempotency-key")
            accepted = [item for item in payload["items"] if item["review_status"] != "rejected"]
            assert len(accepted) == 1
            assert accepted[0]["description"] == "Relatorios sinteticos corrigidos"
            stored.clear()
            for index, item in enumerate(accepted):
                stored.append({
                    "id": f"fact-{index + 1}",
                    "subject": item["title"],
                    "predicate": item["category"],
                    "value": json.dumps({
                        k: item.get(k)
                        for k in ("title", "description", "organization", "start_date", "end_date")
                    }),
                    "status": "ACTIVE",
                    "verification": "USER_DECLARED",
                    "source_reference": "synthetic-browser-preview",
                    "supersedes_id": None,
                })
            status = 201
            body = {
                "import_id": "synthetic-import-1",
                "created_fact_ids": [fact["id"] for fact in stored],
                "skipped_duplicates": [],
                "verification": "USER_DECLARED",
            }
        elif path == "/api/v1/career/facts" and method == "GET":
            history = "include_history=true" in request.url
            body = {"items": stored + versions if history else stored}
        elif path == "/api/v1/career/profile" and method == "GET":
            body = {"profile_id": "synthetic-profile", "items": [
                {"id": f["id"], "category": f["predicate"], "title": f["subject"],
                 "source_fact_ids": [f["id"]], "verification": f["verification"]}
                for f in stored
            ]}
        elif "/corrections" in path and method == "POST":
            calls["correction"] += 1
            payload = request.post_data_json
            assert payload["value"] == "Descricao corrigida no navegador"
            old = stored.pop(0)
            versions.append({**old, "status": "SUPERSEDED"})
            structured = json.loads(old["value"])
            structured["description"] = payload["value"]
            stored.append({
                **old,
                "id": "synthetic-fact-corrected",
                "value": json.dumps(structured),
                "source_reference": "synthetic-user-correction",
                "supersedes_id": old["id"],
            })
            status = 201
            body = stored[0]
        else:
            status = 404
            body = {"error": {"code": "NOT_FOUND", "message": "Synthetic endpoint not found"}}
        route.fulfill(status=status, content_type="application/json", body=json.dumps(body))

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.route("**/api/v1/**", api)
        try:
            page.goto(APP_URL + "/resume-import")
            page.get_by_role("heading", name="Entrar na sua conta").wait_for(timeout=10000)
            page.get_by_label("Email").fill("browser@example.invalid")
            page.get_by_label("Senha").fill("synthetic-password")
            page.get_by_role("button", name="Entrar").click()
            page.get_by_role("link", name="Importar currículo").wait_for()
            page.get_by_role("link", name="Importar currículo").click()
            page.locator("#resume-file").set_input_files({
                "name": "synthetic.txt",
                "mimeType": "text/plain",
                "buffer": b"Experiencia profissional\\nEmpresa Exemplo | Analista de Dados",
            })
            page.get_by_role("button", name="Verificar leitura do currículo").click()
            page.get_by_text("Itens sugeridos para revisão (2)").wait_for()
            page.get_by_label("Descrição").first.fill("Relatorios sinteticos corrigidos")
            page.get_by_label("Descartar item").nth(1).check()
            page.get_by_label(
                "Revisei as sugestões e entendo que são declarações não verificadas."
            ).check()
            page.get_by_role("button", name="Confirmar e salvar fatos no perfil").click()
            page.get_by_text("Confirmação salva!", exact=False).wait_for()
            assert calls["confirm"] == 1
            page.get_by_role("link", name="Consultar Fact Ledger e Master Profile").click()
            page.get_by_text("Analista de Dados").wait_for()
            page.get_by_role("button", name="Corrigir fato").click()
            editor = page.get_by_label("Descrição corrigida")
            assert editor.input_value() == "Relatorios sinteticos corrigidos"
            editor.fill("Descricao corrigida no navegador")
            page.get_by_label("Motivo da correção").fill("Confirmacao sintetica")
            page.get_by_role("button", name="Salvar nova versão").click()
            page.get_by_text("Descricao corrigida no navegador", exact=False).wait_for()
            page.get_by_label("Mostrar versões substituídas e rejeitadas").check()
            page.get_by_text("SUPERSEDED", exact=False).wait_for()
            assert calls["preview"] == 1 and calls["correction"] == 1

            # Bearer token is intentionally memory-only, so refresh requires login.
            page.reload()
            page.get_by_role("heading", name="Entrar na sua conta").wait_for()
            page.get_by_label("Email").fill("browser@example.invalid")
            page.get_by_label("Senha").fill("synthetic-password")
            page.get_by_role("button", name="Entrar").click()
            page.get_by_role("link", name="Master Profile").wait_for()
            page.get_by_role("link", name="Master Profile").click()
            page.get_by_text("Analista de Dados").wait_for()
            assert len(stored) == 1 and len(versions) == 1
            print("D2-E2.D.1-D Chromium browser journey PASS (mock HTTP)")
        finally:
            browser.close()


if __name__ == "__main__":
    main()
