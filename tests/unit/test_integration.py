"""
tests/unit/test_integration.py
───────────────────────────────
Layer 2 integration tests (pytest-django).
Section 5, Testing Strategy:
  - Lab container health check API
  - Flag submission pipeline
  - Dashboard data aggregation queries
  - Lab reset workflow
  - Hint reveal endpoint
"""

import hashlib
import json
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from challenges.models import Challenge
from core.models import UserLabAttempt, UserProfile


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def user(db):
    u = User.objects.create_user('integuser', password='testpass123')
    return u


@pytest.fixture
def client_logged_in(user):
    c = Client()
    c.force_login(user)
    return c


@pytest.fixture
def challenge(db):
    raw    = 'integration-test-flag-secret'
    hashed = f'FLAG{{{hashlib.sha256(raw.encode()).hexdigest()}}}'
    return Challenge.objects.create(
        name='Integration Test Challenge',
        description='Test challenge for integration tests.',
        category='sqli',
        difficulty='beginner',
        expected_flag=hashed,
        xp_reward=100,
        hint_cryptic='Cryptic hint text.',
        hint_direct='Direct hint text — costs 10 XP.',
        hint_walkthrough='Full walkthrough text — costs 30 XP.',
    )


# ── Dashboard view ────────────────────────────────────────────────────────────

class TestDashboardView:

    def test_dashboard_requires_login(self):
        c = Client()
        resp = c.get(reverse('dashboard'))
        assert resp.status_code == 302
        assert '/login' in resp['Location']

    def test_dashboard_loads_for_authenticated_user(self, client_logged_in):
        resp = client_logged_in.get(reverse('dashboard'))
        assert resp.status_code == 200
        assert b'Welcome back' in resp.content

    def test_dashboard_shows_zero_completion_on_new_account(self, client_logged_in, user):
        resp = client_logged_in.get(reverse('dashboard'))
        assert resp.status_code == 200
        assert user.profile.completed_lab_count == 0

    def test_dashboard_completion_count_updates(self, client_logged_in, user):
        UserLabAttempt.objects.create(
            user=user, lab_id='sqli_a03', status='completed', score=100
        )
        assert user.profile.completed_lab_count == 1


# ── Lab Registry view ─────────────────────────────────────────────────────────

class TestLabRegistryView:

    def test_lab_registry_loads(self, client_logged_in):
        resp = client_logged_in.get(reverse('lab_registry'))
        assert resp.status_code == 200

    def test_lab_registry_filter_by_difficulty(self, client_logged_in):
        resp = client_logged_in.get(reverse('lab_registry') + '?difficulty=beginner')
        assert resp.status_code == 200
        # All labs in context should be beginner
        labs = resp.context['labs']
        assert all(l['difficulty'] == 'beginner' for l in labs)

    def test_lab_registry_search(self, client_logged_in):
        resp = client_logged_in.get(reverse('lab_registry') + '?q=injection')
        assert resp.status_code == 200
        labs = resp.context['labs']
        assert len(labs) > 0

    def test_lab_registry_filter_by_language(self, client_logged_in):
        resp = client_logged_in.get(reverse('lab_registry') + '?language=python')
        assert resp.status_code == 200
        labs = resp.context['labs']
        assert all(l['language'] == 'python' for l in labs)


# ── Lab Verify endpoint ───────────────────────────────────────────────────────

class TestLabVerifyEndpoint:

    @patch('core.views.get_lab_controller')
    def test_correct_flag_marks_lab_complete(self, mock_ctrl_fn, client_logged_in, user):
        mock_ctrl = MagicMock()
        mock_ctrl.verify_flag.return_value = {"success": True, "score": 100}
        mock_ctrl_fn.return_value = mock_ctrl

        resp = client_logged_in.post(
            reverse('lab_verify', args=['sqli_a03']),
            data=json.dumps({"flag": "FLAG{correct}"}),
            content_type='application/json',
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['success'] is True
        attempt = UserLabAttempt.objects.get(user=user, lab_id='sqli_a03')
        assert attempt.status == 'completed'

    @patch('core.views.get_lab_controller')
    def test_incorrect_flag_does_not_complete(self, mock_ctrl_fn, client_logged_in, user):
        mock_ctrl = MagicMock()
        mock_ctrl.verify_flag.return_value = {"success": False, "score": 0}
        mock_ctrl_fn.return_value = mock_ctrl

        client_logged_in.post(
            reverse('lab_verify', args=['sqli_a03']),
            data=json.dumps({"flag": "FLAG{wrong}"}),
            content_type='application/json',
        )
        assert not UserLabAttempt.objects.filter(
            user=user, lab_id='sqli_a03', status='completed'
        ).exists()

    @patch('core.views.get_lab_controller')
    def test_xp_awarded_on_correct_flag(self, mock_ctrl_fn, client_logged_in, user):
        mock_ctrl = MagicMock()
        mock_ctrl.verify_flag.return_value = {"success": True, "score": 100}
        mock_ctrl_fn.return_value = mock_ctrl

        initial_xp = user.profile.xp_points
        client_logged_in.post(
            reverse('lab_verify', args=['sqli_a03']),
            data=json.dumps({"flag": "FLAG{correct}"}),
            content_type='application/json',
        )
        user.profile.refresh_from_db()
        assert user.profile.xp_points > initial_xp


# ── Lab Reset endpoint ────────────────────────────────────────────────────────

class TestLabResetEndpoint:

    @patch('core.views.get_lab_controller')
    def test_reset_clears_attempt_status(self, mock_ctrl_fn, client_logged_in, user):
        mock_ctrl = MagicMock()
        mock_ctrl.reset_lab.return_value = {"success": True}
        mock_ctrl_fn.return_value = mock_ctrl

        UserLabAttempt.objects.create(
            user=user, lab_id='sqli_a03', status='completed', score=80, hints_used=3
        )
        client_logged_in.post(reverse('lab_reset', args=['sqli_a03']))

        attempt = UserLabAttempt.objects.get(user=user, lab_id='sqli_a03')
        assert attempt.status == 'in_progress'
        assert attempt.score == 100
        assert attempt.hints_used == 0


# ── Challenge flag submission ─────────────────────────────────────────────────

class TestChallengeFlagSubmission:

    def test_correct_flag_returns_success(self, client_logged_in, challenge):
        resp = client_logged_in.post(
            reverse('challenges:submit', args=[challenge.pk]),
            data=json.dumps({"flag": challenge.expected_flag}),
            content_type='application/json',
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['success'] is True
        assert data['xp_awarded'] > 0

    def test_wrong_flag_returns_failure(self, client_logged_in, challenge):
        resp = client_logged_in.post(
            reverse('challenges:submit', args=[challenge.pk]),
            data=json.dumps({"flag": "FLAG{totallynotright}"}),
            content_type='application/json',
        )
        assert resp.status_code == 200
        assert resp.json()['success'] is False

    def test_empty_flag_returns_400(self, client_logged_in, challenge):
        resp = client_logged_in.post(
            reverse('challenges:submit', args=[challenge.pk]),
            data=json.dumps({"flag": ""}),
            content_type='application/json',
        )
        assert resp.status_code == 400


# ── Hint reveal endpoint ──────────────────────────────────────────────────────

class TestHintReveal:

    def test_tier1_hint_is_free(self, client_logged_in, challenge):
        resp = client_logged_in.post(
            reverse('challenges:hint', args=[challenge.pk]),
            data=json.dumps({"tier": 1}),
            content_type='application/json',
        )
        data = resp.json()
        assert data['success'] is True
        assert data['xp_cost'] == 0
        assert 'cryptic' in data['hint'].lower() or len(data['hint']) > 0

    def test_tier2_hint_costs_10xp(self, client_logged_in, challenge):
        resp = client_logged_in.post(
            reverse('challenges:hint', args=[challenge.pk]),
            data=json.dumps({"tier": 2}),
            content_type='application/json',
        )
        data = resp.json()
        assert data['xp_cost'] == 10

    def test_tier3_hint_costs_30xp(self, client_logged_in, challenge):
        resp = client_logged_in.post(
            reverse('challenges:hint', args=[challenge.pk]),
            data=json.dumps({"tier": 3}),
            content_type='application/json',
        )
        assert resp.json()['xp_cost'] == 30

    def test_invalid_tier_returns_400(self, client_logged_in, challenge):
        resp = client_logged_in.post(
            reverse('challenges:hint', args=[challenge.pk]),
            data=json.dumps({"tier": 99}),
            content_type='application/json',
        )
        assert resp.status_code == 400


# ── Progress API endpoint ─────────────────────────────────────────────────────

class TestProgressAPI:

    def test_api_progress_returns_json(self, client_logged_in, user):
        resp = client_logged_in.get(reverse('api_progress'))
        assert resp.status_code == 200
        data = resp.json()
        assert data['username'] == 'integuser'
        assert 'xp_points' in data
        assert 'streak_days' in data
        assert 'completion_pct' in data
        assert 'attempts' in data

    def test_api_health_returns_ok(self):
        c = Client()
        resp = c.get(reverse('api_lab_health'))
        assert resp.status_code == 200
        assert resp.json()['status'] == 'ok'


# ── OWASP 2026 page ───────────────────────────────────────────────────────────

class TestOWASP2026Page:

    def test_page_loads(self, client_logged_in):
        resp = client_logged_in.get(reverse('owasp2026'))
        assert resp.status_code == 200
        assert b'2026' in resp.content

    def test_stubs_present(self, client_logged_in):
        resp = client_logged_in.get(reverse('owasp2026'))
        assert b'Supply Chain' in resp.content
        assert b'API Security' in resp.content
