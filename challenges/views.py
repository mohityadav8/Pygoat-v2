"""
challenges/views.py
────────────────────
Goal 6 — Challenge section with flag-based verification and 3-tier hints.
"""

import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from challenges.models import Challenge
from core.models import UserLabAttempt
from core.services.challenge_verifier import ChallengeVerifier

logger = logging.getLogger(__name__)
verifier = ChallengeVerifier()


@login_required
def challenge_list(request):
    """Display all active challenges grouped by category."""
    challenges = Challenge.objects.filter(is_active=True).order_by('order', 'difficulty')

    # Attach per-user attempt status
    solved_ids = set(
        UserLabAttempt.objects.filter(
            user=request.user,
            lab_id__startswith='challenge_',
            status='completed',
        ).values_list('lab_id', flat=True)
    )

    challenge_data = []
    for c in challenges:
        challenge_data.append({
            'challenge': c,
            'is_solved': f'challenge_{c.pk}' in solved_ids,
        })

    ctx = {
        'challenge_data': challenge_data,
        'solved_count': len(solved_ids),
        'total_count': challenges.count(),
    }
    return render(request, 'challenges/list.html', ctx)


@login_required
def challenge_detail(request, challenge_id: int):
    """Individual challenge page."""
    challenge = get_object_or_404(Challenge, pk=challenge_id, is_active=True)
    attempt = UserLabAttempt.objects.filter(
        user=request.user, lab_id=f'challenge_{challenge_id}'
    ).first()
    ctx = {
        'challenge': challenge,
        'attempt':   attempt,
        'is_solved': attempt and attempt.status == 'completed',
    }
    return render(request, 'challenges/detail.html', ctx)


@login_required
@require_http_methods(['POST'])
def submit_flag(request, challenge_id: int):
    """
    POST /challenges/<id>/submit/
    Body: {"flag": "FLAG{...}"}
    Returns: {"success": bool, "message": str, "xp_awarded": int}
    """
    try:
        body = json.loads(request.body)
        flag = body.get('flag', '').strip()
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({"success": False, "message": "Invalid request."}, status=400)

    if not flag:
        return JsonResponse({"success": False, "message": "Flag cannot be empty."}, status=400)

    result = verifier.verify(request.user, challenge_id, flag)
    return JsonResponse(result)


@login_required
@require_http_methods(['POST'])
def reveal_hint(request, challenge_id: int):
    """
    POST /challenges/<id>/hint/
    Body: {"tier": 1|2|3}

    Goal 6.2 — Three-tier hint system:
        tier 1: cryptic hint  (costs 0 XP)
        tier 2: direct hint   (costs 10 XP)
        tier 3: full walkthrough (costs 30 XP)
    """
    try:
        tier = int(json.loads(request.body).get('tier', 1))
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"success": False, "message": "Invalid tier."}, status=400)

    if tier not in (1, 2, 3):
        return JsonResponse({"success": False, "message": "Tier must be 1, 2, or 3."}, status=400)

    challenge = get_object_or_404(Challenge, pk=challenge_id, is_active=True)

    # Get or create attempt
    attempt, _ = UserLabAttempt.objects.get_or_create(
        user=request.user,
        lab_id=f'challenge_{challenge_id}',
        defaults={'status': 'in_progress', 'score': 100},
    )
    attempt.use_hint(tier)

    hint_map = {
        1: challenge.hint_cryptic,
        2: challenge.hint_direct,
        3: challenge.hint_walkthrough,
    }
    xp_cost = {1: 0, 2: 10, 3: 30}

    return JsonResponse({
        "success": True,
        "hint":     hint_map[tier],
        "xp_cost":  xp_cost[tier],
        "message":  f"Hint revealed (tier {tier}) — {xp_cost[tier]} XP deducted from score.",
    })
