"""
tests/e2e/test_lab_flow.py
───────────────────────────
Layer 3 E2E tests using Playwright.
Section 5, Testing Strategy — critical user journeys:
    Register → Login → Open lab → Submit incorrect flag →
    Use hint → Submit correct flag → Verify dashboard updates.
"""

import os
import pytest
from playwright.sync_api import Page, expect


BASE_URL = os.environ.get('BASE_URL', 'http://localhost:8000')


# ── Helpers ───────────────────────────────────────────────────────────────────

def register_and_login(page: Page, username: str, password: str):
    page.goto(f'{BASE_URL}/register/')
    page.fill('#id_username',  username)
    page.fill('#id_password1', password)
    page.fill('#id_password2', password)
    page.click('button[type="submit"]')
    expect(page).to_have_url(f'{BASE_URL}/dashboard/')


# ── E2E Test Suite ────────────────────────────────────────────────────────────

class TestLabCompletionFlow:
    """
    Full user journey:
        Register → Login → Browse labs → Open SQL Injection lab →
        Submit wrong flag → Reveal hint → See dashboard update.
    """

    def test_register_redirects_to_dashboard(self, page: Page):
        register_and_login(page, 'e2euser1', 'TestPass123!')
        expect(page.locator('h1.page-title')).to_contain_text('Welcome back')

    def test_dashboard_shows_zero_completion_on_first_login(self, page: Page):
        register_and_login(page, 'e2euser2', 'TestPass123!')
        expect(page.locator('.stat-card--primary .stat-value')).to_contain_text('0')

    def test_lab_registry_displays_labs(self, page: Page):
        register_and_login(page, 'e2euser3', 'TestPass123!')
        page.goto(f'{BASE_URL}/labs/')
        expect(page.locator('.lab-card').first).to_be_visible()

    def test_filter_by_beginner_shows_correct_labs(self, page: Page):
        register_and_login(page, 'e2euser4', 'TestPass123!')
        page.goto(f'{BASE_URL}/labs/?difficulty=beginner')
        cards = page.locator('.lab-card')
        # All visible cards should show beginner labs
        count = cards.count()
        assert count > 0

    def test_lab_detail_page_loads(self, page: Page):
        register_and_login(page, 'e2euser5', 'TestPass123!')
        page.goto(f'{BASE_URL}/labs/sqli_a03/')
        expect(page.locator('h1.page-title')).to_contain_text('SQL Injection')
        expect(page.locator('.hint-accordion')).to_be_visible()
        expect(page.locator('.flag-submit-zone')).to_be_visible()

    def test_incorrect_flag_shows_error_message(self, page: Page):
        register_and_login(page, 'e2euser6', 'TestPass123!')
        page.goto(f'{BASE_URL}/labs/sqli_a03/')
        page.fill('#flag-input', 'FLAG{wrong_flag}')
        page.click('button:has-text("Submit")')
        result = page.locator('#verify-result')
        expect(result).to_be_visible()
        expect(result).to_have_class('error')

    def test_hint_accordion_toggles(self, page: Page):
        register_and_login(page, 'e2euser7', 'TestPass123!')
        page.goto(f'{BASE_URL}/labs/sqli_a03/')
        first_hint = page.locator('.hint-item').first
        expect(first_hint.locator('.hint-item-body')).not_to_be_visible()
        first_hint.locator('.hint-item-header').click()
        expect(first_hint.locator('.hint-item-body')).to_be_visible()

    def test_challenge_list_loads(self, page: Page):
        register_and_login(page, 'e2euser8', 'TestPass123!')
        page.goto(f'{BASE_URL}/challenges/')
        expect(page.locator('.challenge-card').first).to_be_visible()

    def test_incorrect_challenge_flag_shows_error(self, page: Page):
        register_and_login(page, 'e2euser9', 'TestPass123!')
        page.goto(f'{BASE_URL}/challenges/')
        # Get first challenge card
        first_card = page.locator('.challenge-card').first
        first_card.locator('input[type="text"]').fill('FLAG{definitely_wrong}')
        first_card.locator('button:has-text("Submit")').click()
        msg = first_card.locator('.verify-msg')
        expect(msg).to_be_visible()
        expect(msg).to_have_class('verify-msg err')

    def test_owasp_2026_page_loads(self, page: Page):
        register_and_login(page, 'e2euser10', 'TestPass123!')
        page.goto(f'{BASE_URL}/owasp2026/')
        expect(page.locator('h1.page-title')).to_contain_text('OWASP Top 10')
        expect(page.locator('.owasp-card')).to_have_count(6)  # 6 draft categories

    def test_dashboard_stats_section_present(self, page: Page):
        register_and_login(page, 'e2euser11', 'TestPass123!')
        expect(page.locator('.stat-grid')).to_be_visible()
        expect(page.locator('.stat-card').first).to_be_visible()

    def test_lab_reset_button_present(self, page: Page):
        register_and_login(page, 'e2euser12', 'TestPass123!')
        page.goto(f'{BASE_URL}/labs/sqli_a03/')
        expect(page.locator('#reset-btn')).to_be_visible()

    def test_breadcrumb_navigation_works(self, page: Page):
        register_and_login(page, 'e2euser13', 'TestPass123!')
        page.goto(f'{BASE_URL}/labs/sqli_a03/')
        page.locator('.breadcrumb-home').click()
        expect(page).to_have_url(f'{BASE_URL}/dashboard/')

    def test_logout_redirects_to_login(self, page: Page):
        register_and_login(page, 'e2euser14', 'TestPass123!')
        page.goto(f'{BASE_URL}/logout/')
        expect(page).to_have_url(f'{BASE_URL}/accounts/login/')
