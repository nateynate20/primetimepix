import re
from playwright.sync_api import Page, expect

BASE_URL = "http://127.0.0.1:8000"


def test_landing_page_loads(page: Page):
    """Verify the landing page renders correctly."""
    page.goto(BASE_URL)
    expect(page).to_have_title(re.compile(r"PrimeTimePix", re.IGNORECASE))


def test_full_signup_journey(page: Page):
    """Test complete user signup flow."""
    page.goto(f"{BASE_URL}/users/signup/")

    page.fill("#id_username", "e2etestuser")
    page.fill("#id_email", "e2e@testuser.com")
    page.fill("#id_team_name", "E2ETeam")
    page.fill("#id_password1", "testpass123!")
    page.fill("#id_password2", "testpass123!")
    page.click("button[type='submit']")

    # Should redirect to dashboard after signup
    page.wait_for_url(re.compile(r"/users/dashboard"))
    expect(page.locator("body")).to_contain_text("Dashboard")


def test_login_and_navigate(page: Page):
    """Test login and navigation to schedule."""
    # First create a user via signup
    page.goto(f"{BASE_URL}/users/signup/")
    page.fill("#id_username", "e2enav")
    page.fill("#id_email", "e2enav@test.com")
    page.fill("#id_team_name", "NavTeam")
    page.fill("#id_password1", "testpass123!")
    page.fill("#id_password2", "testpass123!")
    page.click("button[type='submit']")
    page.wait_for_url(re.compile(r"/users/dashboard"))

    # Navigate to schedule/picks
    page.goto(f"{BASE_URL}/picks/")
    expect(page).to_have_url(re.compile(r"/picks/"))

    # Navigate to standings
    page.goto(f"{BASE_URL}/picks/general-standings/")
    expect(page).to_have_url(re.compile(r"/picks/general-standings/"))


def test_unauthenticated_redirect(page: Page):
    """Verify unauthenticated users get redirected to login."""
    page.goto(f"{BASE_URL}/users/dashboard/")
    page.wait_for_url(re.compile(r"/login"))
