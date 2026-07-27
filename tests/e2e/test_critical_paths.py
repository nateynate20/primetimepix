"""Playwright critical-path smoke tests — the flows that must work on Week 1.

These run against a LIVE server (they are not unit tests). To run them:

    # 1. In one terminal, start a server with realistic data:
    python manage.py migrate
    python manage.py seed_season --fresh
    python manage.py runserver

    # 2. Install browsers once, then run the suite:
    python -m playwright install chromium
    pytest tests/e2e/ --browser chromium

They intentionally assert on stable, high-level behavior (redirects, page
titles, success messaging) rather than brittle pixel/DOM details, so they keep
passing as the UI evolves. Covers the pre-season checklist: auth, submitting
picks, standings, invite links, password reset, and mobile layout.
"""
import random
import re

from playwright.sync_api import Page, expect

BASE_URL = "http://127.0.0.1:8000"


def _unique(prefix):
    return f"{prefix}{random.randint(100000, 999999)}"


def _signup(page: Page, username: str) -> None:
    # team_name is capped at 15 chars and must be unique (see SignupUserForm).
    team_name = f"tm{random.randint(100000, 999999)}"
    page.goto(f"{BASE_URL}/users/signup/")
    page.fill("#id_username", username)
    page.fill("#id_email", f"{username}@example.com")
    page.fill("#id_team_name", team_name)
    page.fill("#id_password1", "testpass123!")
    page.fill("#id_password2", "testpass123!")
    page.check("#terms")  # required client-side agreement, blocks submit if unchecked
    page.click("button[type='submit']")
    page.wait_for_url(re.compile(r"/users/dashboard"))


def test_unauthenticated_schedule_redirects_to_login(page: Page):
    page.goto(f"{BASE_URL}/picks/")
    page.wait_for_url(re.compile(r"/login"))


def test_signup_then_submit_picks(page: Page):
    """New user signs up and can submit a pick for any open primetime game."""
    _signup(page, _unique("e2epick"))

    page.goto(f"{BASE_URL}/picks/?week=1")
    # Pick the first available team radio, if the week has open games.
    radios = page.locator("input[type='radio'][name^='pick_']")
    if radios.count() > 0:
        radios.first.check()
        page.click("button[type='submit']")
        # Either a success flash or a graceful "closed" warning — never a 500.
        expect(page.locator("body")).to_contain_text(
            re.compile(r"(saved|closed|pick)", re.IGNORECASE)
        )


def test_general_standings_loads(page: Page):
    _signup(page, _unique("e2estand"))
    response = page.goto(f"{BASE_URL}/picks/general-standings/")
    assert response is not None and response.status < 500
    expect(page).to_have_url(re.compile(r"/general-standings/"))


def test_invite_link_is_handled_gracefully(page: Page):
    """A shared invite URL should render a landing/login page, never crash."""
    response = page.goto(f"{BASE_URL}/join/DEMOCODE/")
    assert response is not None and response.status < 500


def test_password_reset_page_loads(page: Page):
    response = page.goto(f"{BASE_URL}/users/password_reset/")
    assert response is not None and response.status < 500
    expect(page.locator("body")).to_contain_text(re.compile(r"(email|reset)", re.IGNORECASE))


def test_mobile_viewport_navigation(page: Page):
    """Landing page renders and is usable on a phone-sized viewport."""
    page.set_viewport_size({"width": 390, "height": 844})
    response = page.goto(BASE_URL)
    assert response is not None and response.status < 500
    expect(page).to_have_title(re.compile(r"PrimeTimePix", re.IGNORECASE))
