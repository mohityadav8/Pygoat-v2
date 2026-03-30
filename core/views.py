"""
core/views.py
──────────────
Dashboard, lab registry, lab detail, verify, reset.
All views require authentication (login_required decorator).
"""

import json
import logging

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from core.models import UserLabAttempt, UserProfile
from core.services.challenge_verifier import ChallengeVerifier
from core.services.lab_controller import get_lab_controller
from core.services.lab_registry import (
    get_all_labs,
    get_lab,
    get_labs_by_difficulty,
    get_owasp_2026_stubs,
)

logger = logging.getLogger(__name__)
verifier = ChallengeVerifier()


# ── Auth ──────────────────────────────────────────────────────────────────────

def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('login')


def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'core/register.html', {'form': form})


# ── Dashboard ─────────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    """
    Goal 4 — Interactive Learner Dashboard.
    Renders progress per OWASP category, XP, streak, badges.
    """
    user = request.user
    profile = user.profile
    all_labs = get_all_labs()

    # Build per-lab status map
    attempts = {
        a.lab_id: a
        for a in UserLabAttempt.objects.filter(user=user)
    }

    # Group labs by OWASP category
    categories: dict[str, dict] = {}
    for lab in all_labs:
        cat = lab['owasp_category']
        if cat not in categories:
            categories[cat] = {
                'title': lab['owasp_title'],
                'labs': [],
                'completed': 0,
                'total': 0,
            }
        attempt = attempts.get(lab['id'])
        lab_data = {
            **lab,
            'attempt': attempt,
            'status': attempt.status if attempt else 'not_started',
        }
        categories[cat]['labs'].append(lab_data)
        categories[cat]['total'] += 1
        if attempt and attempt.status == 'completed':
            categories[cat]['completed'] += 1

    # Recent activity (last 5 completions)
    recent = UserLabAttempt.objects.filter(
        user=user, status='completed'
    ).order_by('-completed_at')[:5]

    # Learning path tiers
    tiers = {
        'beginner':     get_labs_by_difficulty('beginner'),
        'intermediate': get_labs_by_difficulty('intermediate'),
        'advanced':     get_labs_by_difficulty('advanced'),
    }

    ctx = {
        'profile':    profile,
        'categories': categories,
        'all_labs':   all_labs,
        'attempts':   attempts,
        'recent':     recent,
        'tiers':      tiers,
        'total_labs': len(all_labs),
        'completed_count': profile.completed_lab_count,
        'completion_pct':  profile.completion_percentage,
    }
    return render(request, 'core/dashboard.html', ctx)


# ── Lab Registry ──────────────────────────────────────────────────────────────

@login_required
def lab_registry(request):
    """
    Goal 1 / Goal 3 — Lab Registry.
    Displays all labs from labs.json with filter controls.
    """
    labs = get_all_labs()
    difficulty = request.GET.get('difficulty', '')
    category   = request.GET.get('category', '')
    language   = request.GET.get('language', '')
    q          = request.GET.get('q', '')

    if difficulty:
        labs = [l for l in labs if l['difficulty'] == difficulty]
    if category:
        labs = [l for l in labs if l['owasp_category'] == category]
    if language:
        labs = [l for l in labs if l['language'] == language]
    if q:
        q_lower = q.lower()
        labs = [l for l in labs if q_lower in l['title'].lower() or q_lower in l['description'].lower()]

    # Attach attempt status for each lab
    attempts = {
        a.lab_id: a.status
        for a in UserLabAttempt.objects.filter(user=request.user)
    }
    for lab in labs:
        lab['user_status'] = attempts.get(lab['id'], 'not_started')

    ctx = {
        'labs':       labs,
        'difficulty': difficulty,
        'category':   category,
        'language':   language,
        'q':          q,
        'categories': sorted(set(l['owasp_category'] for l in get_all_labs())),
        'languages':  sorted(set(l['language'] for l in get_all_labs())),
    }
    return render(request, 'core/lab_registry.html', ctx)


# ── Lab Detail ────────────────────────────────────────────────────────────────

@login_required
def lab_detail(request, lab_id: str):
    """
    Goal 5 — Standardised lab page layout.
    Left panel: description, hints accordion, remediation.
    Right panel: iframe proxying to the lab container.
    """
    lab = get_lab(lab_id)
    if not lab:
        return render(request, 'core/404.html', status=404)

    attempt, _ = UserLabAttempt.objects.get_or_create(
        user=request.user,
        lab_id=lab_id,
        defaults={'status': 'in_progress', 'score': 100},
    )
    attempt.mark_in_progress()

    controller  = get_lab_controller()
    health      = controller.health_check(lab_id)
    lab_url     = f'http://{controller._host}:{lab["port"]}/'

    ctx = {
        'lab':     lab,
        'attempt': attempt,
        'health':  health,
        'lab_url': lab_url,
    }
    return render(request, 'core/lab_detail.html', ctx)


# ── Lab Reset ─────────────────────────────────────────────────────────────────

@login_required
@require_http_methods(['POST'])
def lab_reset(request, lab_id: str):
    """
    Goal 2.5 — One-click lab reset.
    Calls POST /reset on the lab container and resets UserLabAttempt.
    """
    result = get_lab_controller().reset_lab(lab_id)
    if result['success']:
        UserLabAttempt.objects.filter(
            user=request.user, lab_id=lab_id
        ).update(status='in_progress', score=100, hints_used=0, completed_at=None)
    return JsonResponse(result)


# ── Lab Verify ────────────────────────────────────────────────────────────────

@login_required
@require_http_methods(['POST'])
def lab_verify(request, lab_id: str):
    """
    POST /labs/<lab_id>/verify/
    Body: {"flag": "FLAG{...}"}
    Proxies to lab container's /verify endpoint then awards XP.
    """
    try:
        body = json.loads(request.body)
        flag = body.get('flag', '')
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({"success": False, "message": "Invalid request body."}, status=400)

    controller = get_lab_controller()
    result = controller.verify_flag(lab_id, flag)

    if result.get('success'):
        attempt, _ = UserLabAttempt.objects.get_or_create(
            user=request.user,
            lab_id=lab_id,
            defaults={'score': 100},
        )
        attempt.score = result.get('score', 100)
        attempt.mark_complete()

        lab = get_lab(lab_id)
        xp = int((lab or {}).get('xp_reward', 100) * attempt.score / 100)
        request.user.profile.award_xp(xp)
        result['xp_awarded'] = xp

    return JsonResponse(result)


# ── OWASP 2026 ────────────────────────────────────────────────────────────────

@login_required
def owasp2026(request):
    """
    Goal 8 — OWASP Top 10:2026 Preparation Section.
    Shows draft categories, stub pages, and completed new labs.
    """
    stubs = get_owasp_2026_stubs()
    new_labs = [l for l in get_all_labs() if l.get('owasp_category', '').startswith('A0') and
                l['id'] in ('bola_a01', 'supply_a08')]
    ctx = {
        'stubs':    stubs,
        'new_labs': new_labs,
    }
    return render(request, 'core/owasp2026.html', ctx)


# ── Internal API ──────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(['GET'])
def api_lab_health(request):
    """Quick health ping — used by Docker healthcheck and CI."""
    return JsonResponse({"status": "ok", "service": "pygoat-core"})


@login_required
@require_http_methods(['GET'])
def api_progress(request):
    """
    Goal 4.6 (Stretch) — REST endpoint exposing progress for LMS integration.
    Returns JSON summary of the authenticated user's progress.
    """
    profile = request.user.profile
    attempts = list(
        UserLabAttempt.objects.filter(user=request.user).values(
            'lab_id', 'status', 'score', 'hints_used', 'started_at', 'completed_at'
        )
    )
    return JsonResponse({
        "username":          request.user.username,
        "xp_points":         profile.xp_points,
        "streak_days":       profile.streak_days,
        "badges":            profile.badges,
        "completed_labs":    profile.completed_lab_count,
        "completion_pct":    profile.completion_percentage,
        "attempts":          attempts,
    })


# ── Context Processor helper ──────────────────────────────────────────────────

def context_processors_lab_registry(request):
    """Injected by settings.TEMPLATES context_processors."""
    return {'all_labs_count': len(get_all_labs())}
