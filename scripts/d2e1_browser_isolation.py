"""D2-E1.3 opt-in, disposable-only real browser isolation acceptance.

Requires playwright Python and a separately verified loopback FastAPI bound to
jobagent_react_test. No database schema reset or fixture cleanup.
Creates ten synthetic accounts and one synthetic job for each account.
"""
from __future__ import annotations

import os
import re
import secrets
import sys
from urllib.parse import urlparse
from urllib.request import urlopen

from playwright.sync_api import sync_playwright, expect


def require_isolated_target() -> tuple[str, str]:
    """A string acknowledgement is not proof of DB binding; operator verifies it first."""
    if os.environ.get("D2E1_BROWSER_DISPOSABLE_ACK") != "jobagent_react_test":
        raise RuntimeError("Expected D2E1_BROWSER_DISPOSABLE_ACK=jobagent_react_test")

    web = os.environ.get("D2E1_WEB_URL", "http://127.0.0.1:5173").rstrip("/")
    api = os.environ.get("D2E1_API_URL", "http://127.0.0.1:18081").rstrip("/")
    for url, port in ((web, 5173), (api, 18081)):
        parsed = urlparse(url)
        if (
            parsed.scheme != "http"
            or parsed.hostname not in ("127.0.0.1", "localhost")
            or parsed.port != port
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in ("", "/")
            or parsed.query
            or parsed.fragment
        ):
            raise RuntimeError(f"Refusing non-loopback or unexpected port: {url}")
    with urlopen(api + "/ready", timeout=5) as response:
        if response.status != 200:
            raise RuntimeError("Disposable API not ready")
    return web, api


def register_and_login(page, web: str, email: str, password: str, name: str) -> None:
    page.goto(web + "/register")
    page.get_by_label("Nome").fill(name)
    page.get_by_label("Email").fill(email)
    page.get_by_label("Senha (12 a 128 caracteres)").fill(password)
    page.get_by_role("button", name="Criar conta").click()
    expect(page.get_by_text("Cadastro realizado.", exact=False)).to_be_visible()
    page.get_by_role("link", name="Ir para login").click()
    page.get_by_label("Email").fill(email)
    page.get_by_label("Senha", exact=True).fill(password)
    page.get_by_role("button", name="Entrar", exact=True).click()
    expect(page.get_by_role("heading", name="JOB COMMAND")).to_be_visible()
    expect(page.get_by_text(name, exact=False)).to_be_visible()


def create_job(page, web: str, title: str) -> None:
    page.goto(web + "/jobs")
    expect(page.get_by_role("heading", name="Jobs", exact=True)).to_be_visible()
    page.get_by_role("button", name="Add Job", exact=True).first.click()
    form = page.get_by_role("form", name="Add job")
    form.get_by_label("Title *").fill(title)
    form.get_by_label("Company *").fill("D2E1 Synthetic")
    form.get_by_label("Description *").fill("Synthetic browser isolation data only.")
    form.get_by_role("button", name="Add job", exact=True).click()
    expect(page.get_by_role("heading", name=title, exact=True)).to_be_visible()


def assert_only_owned_job(page, web: str, owned: str, forbidden: list[str]) -> None:
    page.goto(web + "/jobs")
    expect(page.get_by_role("heading", name="Jobs", exact=True)).to_be_visible()
    expect(page.get_by_text(owned, exact=True)).to_be_visible()
    for other in forbidden:
        expect(page.get_by_text(other, exact=True)).to_have_count(0)


def main() -> int:
    web, api = require_isolated_target()
    seed = secrets.token_hex(5)
    password = "D2E1-Only-" + secrets.token_hex(12) + "!Aa9"
    users = [
        (f"d2e1-browser-{seed}-{i}@example.com", f"D2E1 Browser {seed} {i}")
        for i in range(10)
    ]
    titles = [f"D2E1-isolation-{seed}-job-{i}" for i in range(10)]
    print("D2-E1.3: API ready; starting ten synthetic browser accounts")
    print("Web:", web, "| API:", api, "| synthetic run:", seed)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        contexts = []
        try:
            for i, ((email, name), title) in enumerate(zip(users, titles), start=0):
                context = browser.new_context()
                contexts.append(context)
                page = context.new_page()
                register_and_login(page, web, email, password, name)
                create_job(page, web, title)
                # New context per account prevents accidental cookie/storage carry-over.
                print(f"Account {i + 1}/10: register, login, create job PASS")

            for i, context in enumerate(contexts):
                page = context.pages[0]
                assert_only_owned_job(page, web, titles[i], titles[:i] + titles[i + 1:])
                print(f"Account {i + 1}/10: cross-account job list isolation PASS")

            # Explicitly test logout and account switching in the SAME browser context.
            page = contexts[0].pages[0]
            page.get_by_role("button", name="Sair").click()
            expect(page.get_by_role("heading", name="Entrar na sua conta")).to_be_visible()
            page.goto(web + "/jobs")
            expect(page.get_by_role("heading", name="Entrar na sua conta")).to_be_visible()
            page.get_by_label("Email").fill(users[1][0])
            page.get_by_label("Senha", exact=True).fill(password)
            page.get_by_role("button", name="Entrar", exact=True).click()
            expect(page.get_by_role("heading", name="Jobs", exact=True)).to_be_visible()
            assert_only_owned_job(page, web, titles[1], titles[:1] + titles[2:])
            print("Same-context logout / account switch isolation PASS")

            # In-memory bearer is deliberately discarded on full browser reload.
            page.reload()
            expect(page.get_by_role("heading", name="Entrar na sua conta")).to_be_visible()
            print("Refresh requires reauthentication PASS")
        finally:
            for context in contexts:
                context.close()
            browser.close()
    print("D2-E1.3 BROWSER ISOLATION PASS — 10 accounts, 90 foreign-job absences")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"D2-E1.3 BROWSER ISOLATION FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
