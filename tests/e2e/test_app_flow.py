"""End-to-end checks on the React app at http://localhost:3000 (Playwright).

Selectors use roles and visible text only (no CSS classes), because the UI
is being redesigned. The app opens in French by default.

Prerequisites: the frontend dev server on :3000 and the backend on :8000.
Chromium: `backend/.venv/bin/python -m playwright install chromium`.
If the app is not reachable, every test is SKIPPED with that reason.
A skip is not a pass.

Run: `backend/.venv/bin/python -m pytest tests/e2e -v`
"""

import re
import urllib.error
import urllib.request

import pytest
from playwright.sync_api import sync_playwright, expect

APP = "http://localhost:3000"

# Visible text this flow depends on (French UI). Re-check against the final
# UI before the final pass; change here only, never in the tests.
LABELS = {
    "compare_button": "Comparer les rotations",
    "see_details": "Voir le détail",
    "tab_climate": "Climat",
    "tab_compare": "Comparer",
    "arabic": "العربية",
    "close": "Fermer",
}


@pytest.fixture(scope="module", autouse=True)
def require_app():
    try:
        urllib.request.urlopen(APP + "/", timeout=10)
    except urllib.error.HTTPError:
        return
    except (urllib.error.URLError, OSError) as exc:
        pytest.skip(f"frontend not reachable at {APP}: {exc}")


@pytest.fixture(scope="module")
def page():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        pg = ctx.new_page()
        pg.goto(APP + "/")
        pg.wait_for_load_state("networkidle")
        yield pg
        browser.close()


def _run_default_comparison(page):
    """Default point, rotation wheat then fallow (already the default rotation
    in the form), move one goal slider, submit."""
    page.get_by_role("slider").first.press("ArrowRight")
    page.get_by_role("button", name=LABELS["compare_button"]).click()
    expect(page.get_by_role("button", name=LABELS["see_details"]).first).to_be_visible(timeout=60000)


def test_default_point_is_pre_filled(page):
    page.goto(APP + "/")
    page.wait_for_load_state("networkidle")
    values = page.locator("input").evaluate_all("els => els.map(e => e.value)")
    assert "33.96" in values and "-5.27" in values, values


def test_submit_returns_at_least_three_strategies(page):
    page.goto(APP + "/")
    page.wait_for_load_state("networkidle")
    _run_default_comparison(page)
    buttons = page.get_by_role("button", name=LABELS["see_details"])
    assert buttons.count() >= 3, buttons.count()


def test_details_show_why_and_risks(page):
    page.goto(APP + "/")
    page.wait_for_load_state("networkidle")
    _run_default_comparison(page)
    page.get_by_role("button", name=LABELS["see_details"]).first.click()
    dialog = page.get_by_role("dialog")
    expect(dialog).to_be_visible()
    # Why and risks sections, in the visible French text of the detail sheet.
    expect(dialog.get_by_text(re.compile(r"pourquoi|raison", re.I)).first).to_be_visible()
    expect(dialog.get_by_text(re.compile(r"risque", re.I)).first).to_be_visible()
    page.get_by_role("button", name=LABELS["close"]).click()


def test_expert_note_is_visible(page):
    page.goto(APP + "/")
    page.wait_for_load_state("networkidle")
    _run_default_comparison(page)
    expect(page.get_by_text(re.compile(r"conseiller agricole", re.I)).first).to_be_visible()


def test_arabic_switch_sets_rtl(page):
    page.goto(APP + "/")
    page.wait_for_load_state("networkidle")
    page.get_by_role("button", name=LABELS["arabic"]).click()
    expect(page.locator("html")).to_have_attribute("dir", "rtl")
    expect(page.locator("html")).to_have_attribute("lang", "ar")
    # restore French for later tests
    page.get_by_role("button", name="Français").click()
    expect(page.locator("html")).to_have_attribute("dir", "ltr")


def test_climate_dashboard_is_reachable(page):
    page.goto(APP + "/")
    page.wait_for_load_state("networkidle")
    _run_default_comparison(page)
    expect(page.get_by_role("tab", name=LABELS["tab_climate"])).to_be_visible()
    page.get_by_role("tab", name=LABELS["tab_climate"]).click()
    expect(page.get_by_text(re.compile(r"Climat de votre champ"))).to_be_visible()


def test_compare_tab_is_reachable(page):
    page.goto(APP + "/")
    page.wait_for_load_state("networkidle")
    _run_default_comparison(page)
    page.get_by_role("tab", name=LABELS["tab_compare"]).click()
    expect(page.get_by_text(re.compile(r"Comparer deux options"))).to_be_visible()
