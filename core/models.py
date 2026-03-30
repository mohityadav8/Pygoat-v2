"""
core/models.py
──────────────
Dashboard data models as specified in GSoC 2026 proposal (Section 5).

    UserLabAttempt  — tracks every lab interaction per user
    UserProfile     — XP, streak, badges
"""

from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


class UserLabAttempt(models.Model):
    """
    One row per (user, lab_id) pair.  Updated in-place when the user
    revisits the same lab.  score is reduced proportionally for each
    hint tier consumed (cryptic: -0, direct: -10, walkthrough: -30).
    """

    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed',   'Completed'),
    ]

    user         = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lab_attempts')
    lab_id       = models.CharField(max_length=64)       # references labs.json id field
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started')
    score        = models.IntegerField(default=0)         # 0–100; reduced per hint used
    hints_used   = models.IntegerField(default=0)         # bitmask: 0b001 cryptic, 0b010 direct, 0b100 walkthrough
    started_at   = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'lab_id')
        ordering = ['-started_at']

    def __str__(self):
        return f'{self.user.username} — {self.lab_id} [{self.status}]'

    def mark_complete(self):
        """Mark as completed and record timestamp."""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at', 'score'])

    def mark_in_progress(self):
        if self.status == 'not_started':
            self.status = 'in_progress'
            self.save(update_fields=['status'])

    def use_hint(self, tier: int):
        """
        Register hint usage and deduct XP penalty.
        tier: 1 = cryptic (free), 2 = direct (-10 XP), 3 = walkthrough (-30 XP)
        """
        tier_bit = 1 << (tier - 1)
        if self.hints_used & tier_bit:
            return  # already used this hint tier
        self.hints_used |= tier_bit
        save_fields = ['hints_used']
        if tier == 2:
            self.score = max(0, self.score - 10)
            save_fields.append('score')
        elif tier == 3:
            self.score = max(0, self.score - 30)
            save_fields.append('score')
        self.save(update_fields=save_fields)

    @property
    def hint_cryptic_used(self) -> bool:
        return bool(self.hints_used & 0b001)

    @property
    def hint_direct_used(self) -> bool:
        return bool(self.hints_used & 0b010)

    @property
    def hint_walkthrough_used(self) -> bool:
        return bool(self.hints_used & 0b100)


class UserProfile(models.Model):
    """
    Extended profile linked 1-to-1 with Django's built-in User.
    Created automatically via post_save signal on User.
    """

    BADGE_CHOICES = [
        ('first_sqli',    '💉 First SQLi'),
        ('xss_master',    '🎭 XSS Master'),
        ('csrf_hunter',   '🪝 CSRF Hunter'),
        ('idor_explorer', '🔑 IDOR Explorer'),
        ('ssti_wizard',   '🧩 SSTI Wizard'),
        ('streak_7',      '🔥 7-Day Streak'),
        ('streak_30',     '🔥 30-Day Streak'),
        ('completionist', '👑 Completionist'),
    ]

    user        = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    xp_points   = models.IntegerField(default=0)
    streak_days = models.IntegerField(default=0)
    last_active = models.DateField(null=True, blank=True)
    badges      = models.JSONField(default=list)   # list of badge keys from BADGE_CHOICES

    def __str__(self):
        return f'{self.user.username} — {self.xp_points} XP'

    def award_xp(self, points: int):
        """Add XP and check for badge thresholds."""
        self.xp_points += points
        self._update_streak()
        self._check_badges()
        self.save()

    def _update_streak(self):
        today = timezone.now().date()
        if self.last_active is None:
            self.streak_days = 1
        elif (today - self.last_active).days == 1:
            self.streak_days += 1
        elif (today - self.last_active).days > 1:
            self.streak_days = 1
        # same day: no change
        self.last_active = today

    def _check_badges(self):
        """Award streak badges automatically."""
        if self.streak_days >= 7 and 'streak_7' not in self.badges:
            self.badges.append('streak_7')
        if self.streak_days >= 30 and 'streak_30' not in self.badges:
            self.badges.append('streak_30')

    def award_badge(self, badge_key: str):
        if badge_key not in self.badges:
            self.badges.append(badge_key)
            self.save(update_fields=['badges'])

    @property
    def completed_lab_count(self) -> int:
        return UserLabAttempt.objects.filter(
            user=self.user, status='completed'
        ).count()

    @property
    def completion_percentage(self) -> int:
        from core.services.lab_registry import get_all_labs
        total = len(get_all_labs())
        if total == 0:
            return 0
        return min(100, int(self.completed_lab_count / total * 100))


# ── Signals ───────────────────────────────────────────────────────────────────

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Auto-create UserProfile when a new User is registered."""
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()
