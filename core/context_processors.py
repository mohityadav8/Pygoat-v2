# core/context_processors.py
"""
Injects lab registry data into all templates.
Registered in settings.TEMPLATES context_processors.
"""
from core.services.lab_registry import get_all_labs


def lab_registry(request):
    """Makes all_labs_count available in every template."""
    try:
        count = len(get_all_labs())
    except Exception:
        count = 0
    return {'all_labs_count': count}
