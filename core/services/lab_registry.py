"""
core/services/lab_registry.py
──────────────────────────────
Thin helper that reads labs.json and returns structured data.
Used by views and the template context processor.
"""

import json
from functools import lru_cache
from django.conf import settings


@lru_cache(maxsize=1)
def get_all_labs() -> list:
    with open(settings.LABS_JSON_PATH) as f:
        data = json.load(f)
    return [lab for lab in data['labs'] if lab.get('enabled', True)]


def get_lab(lab_id: str) -> dict | None:
    for lab in get_all_labs():
        if lab['id'] == lab_id:
            return lab
    return None


def get_labs_by_category(owasp_category: str) -> list:
    return [lab for lab in get_all_labs() if lab['owasp_category'] == owasp_category]


def get_labs_by_difficulty(difficulty: str) -> list:
    return [lab for lab in get_all_labs() if lab['difficulty'] == difficulty]


def get_owasp_2026_stubs() -> list:
    with open(settings.LABS_JSON_PATH) as f:
        data = json.load(f)
    return data.get('owasp_2026_stubs', [])
