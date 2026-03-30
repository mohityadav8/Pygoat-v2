"""
challenges/models.py
─────────────────────
Challenge model (flag-based CTF) and attempt tracking.
Extends the existing challenge app with XP reward and category fields.
"""

import hashlib

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models


class Challenge(models.Model):
    """
    Goal 6 — 10 new challenge tasks with automated flag verification.
    """

    CATEGORY_CHOICES = [
        ('sqli',            'SQL Injection'),
        ('xss',             'Cross-Site Scripting'),
        ('csrf',            'CSRF'),
        ('idor',            'IDOR'),
        ('jwt',             'JWT'),
        ('ssti',            'SSTI'),
        ('ssrf',            'SSRF'),
        ('deserialization', 'Insecure Deserialization'),
        ('auth',            'Authentication'),
        ('api',             'API Security'),
    ]

    DIFFICULTY_CHOICES = [
        ('beginner',     'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced',     'Advanced'),
    ]

    name          = models.CharField(max_length=100, unique=True)
    description   = models.TextField()
    category      = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    difficulty    = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default='beginner')
    expected_flag = models.CharField(max_length=128)   # stored as FLAG{sha256_hex}
    xp_reward     = models.IntegerField(default=100)
    order         = models.IntegerField(default=0)     # display order
    is_active     = models.BooleanField(default=True)

    # Optional: hint texts for 3-tier hint system
    hint_cryptic    = models.TextField(blank=True, help_text='Free — abstract clue')
    hint_direct     = models.TextField(blank=True, help_text='Costs 10 XP — direct clue')
    hint_walkthrough = models.TextField(blank=True, help_text='Costs 30 XP — full walkthrough')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Hash the flag on first save if not already hashed
        if self.expected_flag and not self.expected_flag.startswith('FLAG{'):
            raw = self.expected_flag
            hashed = hashlib.sha256(raw.encode()).hexdigest()
            self.expected_flag = f'FLAG{{{hashed}}}'
        super().save(*args, **kwargs)

    def clean(self):
        if self.xp_reward < 0:
            raise ValidationError('xp_reward must be non-negative.')
