"""End-to-end checks on the React app at http://localhost:3000 (Playwright).

Selectors use roles, accessible names and visible text only (no CSS classes).
Labels come from frontend/src/i18n/{fr,en,ar}.js. Each test starts from a
fresh browser context, so the saved language does not leak between tests.

Prerequisites: frontend dev server on :3000 and backend on :8000 (both must
already be running; these tests do not start or stop them).
Chromium: `backend/.venv/bin/python -m playwright install chromium`.
If the app is not reachable every test is SKIPPED with that reason.
A skip is not a pass.

Run: `backend/.venv/bin/python -m pytest tests/e2e -v`
"""

import json
import re
import urllib.error
import urllib.request
import uuid

import pytest
from playwright.sync_api import expect, sync_playwright

APP = "http://localhost:3000"
TOUR_WAIT_MS = 25000  # the guided tour moves to the next section after a few seconds

# Visible labels per language (copied from the i18n dictionaries).
L = {
    "fr": {
        "analyse": "Analyser mon champ",
        "identifier": "E-mail ou nom d’utilisateur",
        "password": "Mot de passe",
        "login": "Se connecter",
        "next": "Continuer",
        "compare": "Comparer les rotations",
        "lang_button": "Français",
        "tour": "Visite guidée",
        "settings_open": "Ouvrir les réglages",
        "settings_title": "Réglages",
        "dark": "Mode sombre",
        "close": "Fermer",
        "view_optimise": "Optimisation",
        "opt_run": "Voir mon plan",
        "all_fields": "Planifier tous mes champs ensemble (avancé)",
        "optimiser_title": "Optimiser mes parcelles",
        "add_parcel": "Ajouter une parcelle",
        "profile_balanced": "Équilibré",
        "run": "Optimiser",
        "pareto_title": "Revenu et eau : les plans possibles",
        "pareto_pick": "Choisir un plan",
        "brand": "Cycle Sûr",
        "tab_simple": "Conseil",
        "results": "Nos résultats pour votre champ",
        "nav_label": "Sections de la présentation",
    },
    "en": {
        "analyse": "Analyse my field",
        "identifier": "Email or username",
        "password": "Password",
        "login": "Log in",
        "next": "Continue",
        "compare": "Compare rotations",
        "lang_button": "English",
        "tour": "Guided tour",
        "settings_open": "Open settings",
        "settings_title": "Settings",
        "dark": "Dark mode",
        "close": "Close",
        "view_optimise": "Optimisation",
        "opt_run": "Show my plan",
        "all_fields": "Plan all my fields together (advanced)",
        "optimiser_title": "Optimise my parcels",
        "add_parcel": "Add a parcel",
        "profile_balanced": "Balanced",
        "run": "Optimise",
        "pareto_title": "Income and water: the possible plans",
        "pareto_pick": "Choose a plan",
        "brand": "Safe Cycle",
        "tab_simple": "Advice",
        "results": "Our results for your field",
        "nav_label": "Sections of the presentation",
    },
    "ar": {
        "analyse": "حلّل حقلي",
        "identifier": "البريد الإلكتروني أو اسم المستخدم",
        "password": "كلمة المرور",
        "login": "تسجيل الدخول",
        "next": "متابعة",
        "compare": "قارن بين الدورات",
        "lang_button": "العربية",
        "tour": "جولة مرشدة",
        "settings_open": "فتح الإعدادات",
        "settings_title": "الإعدادات",
        "dark": "الوضع الداكن",
        "close": "إغلاق",
        "view_optimise": "التحسين",
        "opt_run": "أرني خطتي",
        "all_fields": "خطط لكل حقولي معا (متقدم)",
        "optimiser_title": "",  # filled below from the dictionary when needed
        "add_parcel": "",
        "profile_balanced": "",
        "run": "حسّن",
        "pareto_title": "الدخل والماء: الخطط الممكنة",
        "pareto_pick": "",
        "brand": "دورة آمنة",
        "tab_simple": "نصيحة",
        "results": "نتائجنا لحقلك",
        "nav_label": "",
    },
}


@pytest.fixture(scope="module", autouse=True)
def require_app():
    try:
        urllib.request.urlopen(APP + "/", timeout=10)
    except urllib.error.HTTPError:
        return
    except (urllib.error.URLError, OSError) as exc:
        pytest.skip(f"frontend not reachable at {APP}: {exc}")


def _post(path, body, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(APP + path, data=json.dumps(body).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=10) as res:
        return json.loads(res.read())


def _new_user():
    creds = {"username": f"e2e-{uuid.uuid4().hex[:8]}", "password": "correct-horse-9"}
    _post("/api/register/", creds)
    return creds


@pytest.fixture(scope="module")
def account():
    """A fresh user who has already set up a farm, created through the API (via the dev server proxy)."""
    creds = _new_user()
    token = _post("/api/token/", creds)["access"]
    _post("/api/farms/", {
        "name": "E2E farm", "latitude": 33.96, "longitude": -5.27, "soil_type": "unknown",
        "crops": ["wheat"], "parcels": [{"name": "Field 1", "area_ha": 1}],
    }, token)
    return creds


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        yield b
        b.close()


@pytest.fixture
def page(browser):
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    pg = ctx.new_page()
    pg.goto(APP + "/")
    pg.wait_for_load_state("load")
    yield pg
    ctx.close()


def _switch_language(page, lang_code):
    """Use the language switch on the page, by its visible name."""
    names = {"fr": "Français", "en": "English", "ar": "العربية"}
    page.get_by_role("button", name=names[lang_code], exact=True).first.click()
    expect(page.locator("html")).to_have_attribute("lang", lang_code)


def _run_wizard(page, lang, account):
    """Landing -> analyse -> log in -> My farm -> Optimisation tab -> Show my plan -> results."""
    t = L[lang]
    page.get_by_role("button", name=t["analyse"]).first.click()
    _log_in(page, t, account)
    page.get_by_role("tab", name=t["view_optimise"]).click()
    page.get_by_role("button", name=t["opt_run"]).click()
    expect(page.get_by_role("heading", name=t["results"])).to_be_visible(timeout=60000)


# ---------------------------------------------------------------------------
# Landing page
# ---------------------------------------------------------------------------

def test_landing_stats_show_numbers(page):
    stat_label = page.get_by_text(re.compile(r"mois par an de champ nu")).first
    expect(stat_label).to_be_visible()
    # the number sits in the same block as its label
    block_text = stat_label.locator("xpath=..").inner_text()
    assert re.search(r"\d", block_text), block_text


def test_guided_tour_advances(page):
    nav = page.get_by_role("navigation", name=L["fr"]["nav_label"])
    current = nav.locator("[aria-current='true']")
    expect(current).to_have_count(1)
    before = current.get_attribute("aria-label")
    page.get_by_role("button", name=L["fr"]["tour"]).click()
    expect(nav.locator("[aria-current='true']")).not_to_have_attribute(
        "aria-label", before, timeout=TOUR_WAIT_MS
    )


# ---------------------------------------------------------------------------
# Wizard to simple results, in each language
# ---------------------------------------------------------------------------

def test_wizard_runs_to_simple_results_in_french(page, account):
    _run_wizard(page, "fr", account)
    expect(page.get_by_text(re.compile(r"conseiller agricole", re.I)).first).to_be_visible()


def test_wizard_runs_to_simple_results_in_english(page, account):
    _switch_language(page, "en")
    _run_wizard(page, "en", account)
    expect(page.get_by_text(re.compile(r"local (agricultural )?(advisor|expert)", re.I)).first).to_be_visible()
    # New results screen: three tabs, the field picture, three verdicts, compare strips.
    expect(page.get_by_role("tab")).to_have_count(5)  # My farm, Optimisation + My plan, Compare, Details
    expect(page.get_by_role("img", name=re.compile("Life of your field"))).to_be_visible()
    expect(page.locator(".verdict")).to_have_count(3)
    page.get_by_role("tab", name="Compare").click()
    assert page.locator(".cmp-row").count() >= 3


def test_wizard_runs_to_simple_results_in_arabic_with_rtl(page, account):
    _switch_language(page, "ar")
    expect(page.locator("html")).to_have_attribute("dir", "rtl")
    _run_wizard(page, "ar", account)
    expect(page.locator("html")).to_have_attribute("dir", "rtl")


def test_brand_name_follows_language(page):
    expect(page.get_by_text(L["fr"]["brand"]).first).to_be_visible()
    _switch_language(page, "en")
    expect(page.get_by_text(L["en"]["brand"]).first).to_be_visible()
    _switch_language(page, "ar")
    expect(page.get_by_text(L["ar"]["brand"]).first).to_be_visible()


# ---------------------------------------------------------------------------
# Settings panel
# ---------------------------------------------------------------------------

def test_settings_toggle_dark_mode(page):
    t = L["fr"]
    page.get_by_role("button", name=t["settings_open"]).click()
    dialog = page.get_by_role("dialog", name=t["settings_title"])
    expect(dialog).to_be_visible()

    dark = dialog.get_by_role("switch", name=t["dark"])
    before = dark.get_attribute("aria-checked")
    dark.click()
    expect(dark).not_to_have_attribute("aria-checked", before)

    dialog.get_by_role("button", name=t["close"]).click()


# ---------------------------------------------------------------------------
# Optimiser (several parcels) with Pareto chart
# ---------------------------------------------------------------------------

def _log_in(page, t, account):
    page.get_by_label(t["identifier"]).fill(account["username"])
    page.get_by_label(t["password"]).fill(account["password"])
    page.get_by_role("button", name=t["login"], exact=True).last.click()


def test_optimiser_returns_plans_and_pareto_chart(page, account):
    t = L["fr"]
    page.get_by_role("button", name=t["analyse"]).first.click()
    _log_in(page, t, account)
    page.get_by_role("tab", name=t["view_optimise"]).click()
    page.get_by_role("button", name=t["all_fields"]).click()
    expect(page.get_by_role("heading", name=t["optimiser_title"])).to_be_visible()

    # the first parcel is open by default: set its area first
    area_first = page.get_by_label("Surface (hectares)").first
    expect(area_first).to_be_visible()
    area_first.fill("3")
    page.get_by_role("button", name=t["add_parcel"]).click()
    # the second parcel is a closed <details>: open it, then set its area
    page.locator("details").filter(has_text="Parcelle 2").locator("summary").first.click()
    page.get_by_label("Surface (hectares)").nth(1).fill("2")

    page.get_by_role("button", name=t["profile_balanced"]).click()
    page.get_by_role("button", name=t["run"], exact=True).click()

    chart = page.get_by_role("img", name=t["pareto_title"])
    expect(chart).to_be_visible(timeout=90000)
    picker = page.get_by_role("group", name=t["pareto_pick"])
    assert picker.get_by_role("button").count() >= 2


# ---------------------------------------------------------------------------
# Farm setup wizard (first time after sign-up)
# ---------------------------------------------------------------------------

def test_farm_setup_wizard_with_gps(browser):
    ctx = browser.new_context(
        viewport={"width": 390, "height": 844},
        geolocation={"latitude": 33.93, "longitude": -5.22, "accuracy": 20},
        permissions=["geolocation"],
    )
    page = ctx.new_page()
    page.goto(APP + "/")
    _switch_language(page, "en")
    t = L["en"]
    page.get_by_role("button", name=t["analyse"]).first.click()
    _log_in(page, t, _new_user())

    expect(page.get_by_role("heading", name="What is the name of your farm?")).to_be_visible()
    page.get_by_label("Farm name").fill("Ferme Ait Ali")
    page.get_by_role("button", name=t["next"]).click()
    page.get_by_role("button", name="One field more").click()
    page.get_by_label("Field 1: size").fill("2,5")
    page.get_by_label("Field 2: size").fill("1")
    page.get_by_role("button", name=t["next"]).click()
    page.get_by_role("radio", name="Red soil (Hamri)").click()
    page.get_by_role("button", name=t["next"]).click()
    # Place: the map comes first; saving without placing the farm is refused.
    page.get_by_role("button", name="Save my farm").click()
    expect(page.get_by_role("alert")).to_contain_text("Tap the map")
    page.get_by_role("button", name="Use my location").click()  # secondary option
    expect(page.get_by_text("Position found")).to_be_visible()
    page.get_by_role("button", name="Save my farm").click()
    # Then the "My farm" dashboard.
    expect(page.get_by_role("heading", name="Ferme Ait Ali")).to_be_visible(timeout=15000)
    expect(page.get_by_text("33.93").first).to_be_visible()
    ctx.close()
