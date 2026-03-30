"""
core/services/challenge_verifier.py
─────────────────────────────────────
Flag-based verification engine as specified in GSoC 2026 proposal (Section 5).

Each challenge has a unique FLAG{sha256_of_secret} that can only be obtained
by successfully exploiting the vulnerability.

ChallengeVerifier.verify() validates submitted flags, updates UserLabAttempt,
and awards XP via UserProfile.award_xp().
"""

import hashlib
import hmac
import logging

from django.contrib.auth.models import User

logger = logging.getLogger(__name__)


class ChallengeVerifier:
    """
    Stateless verifier.  Instantiate once and call verify() per submission.
    Uses hmac.compare_digest for timing-safe comparison.
    """

    def verify(self, user: User, challenge_id: str, submitted_flag: str) -> dict:
        """
        Validate submitted_flag against the challenge's expected flag.

        Returns:
            {"success": True,  "xp_awarded": int, "message": str}
            {"success": False, "message": str}
        """
        from challenges.models import Challenge
        from core.models import UserLabAttempt

        try:
            challenge = Challenge.objects.get(pk=challenge_id)
        except Challenge.DoesNotExist:
            return {"success": False, "message": "Challenge not found."}

        # Timing-safe comparison
        expected = challenge.expected_flag
        if not hmac.compare_digest(submitted_flag.strip(), expected):
            return {"success": False, "message": "Incorrect flag. Keep trying."}

        # Get or create attempt record
        attempt, _ = UserLabAttempt.objects.get_or_create(
            user=user,
            lab_id=f'challenge_{challenge_id}',
            defaults={'status': 'in_progress', 'score': 100},
        )

        if attempt.status == 'completed':
            return {
                "success": True,
                "xp_awarded": 0,
                "message": "Already solved — no additional XP.",
            }

        # Calculate score based on hints used
        score = self._calculate_score(attempt, challenge)
        attempt.score = score
        attempt.mark_complete()

        # Award XP
        xp = int(challenge.xp_reward * score / 100)
        try:
            user.profile.award_xp(xp)
            self._check_lab_badges(user, challenge)
        except Exception as exc:
            logger.error('XP award failed for user %s: %s', user.username, exc)

        return {
            "success": True,
            "xp_awarded": xp,
            "score": score,
            "message": f"Correct! +{xp} XP awarded.",
        }

    def _calculate_score(self, attempt, challenge) -> int:
        """
        Base score 100.  Deduct per hint tier used:
          cryptic hint  →  -0  XP
          direct hint   →  -10 XP
          walkthrough   →  -30 XP
        """
        score = 100
        if attempt.hint_direct_used:
            score -= 10
        if attempt.hint_walkthrough_used:
            score -= 30
        return max(0, score)

    def _check_lab_badges(self, user: User, challenge) -> None:
        """Award first-solve badges by vulnerability category."""
        category_badges = {
            'sqli':   'first_sqli',
            'xss':    'xss_master',
            'csrf':   'csrf_hunter',
            'idor':   'idor_explorer',
            'ssti':   'ssti_wizard',
        }
        cat = getattr(challenge, 'category', '').lower()
        badge = category_badges.get(cat)
        if badge:
            user.profile.award_badge(badge)
