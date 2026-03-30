"""
playgrounds/views.py
─────────────────────
Goal 6.3 — SSRF Playground: sandboxed proxy environment for SSRF payload experimentation.
Goal 6.4 — Template Injection Playground: sandboxed Jinja2 REPL with payload history.

These playgrounds do NOT expose real internal infrastructure.
SSRF: requests are proxied through a restricted allow-list.
SSTI: Jinja2 is evaluated in a restricted sandbox environment.
"""

import logging
import socket
import urllib.parse
from ipaddress import ip_address, ip_network

import requests
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from jinja2 import Environment, StrictUndefined
from jinja2.sandbox import SandboxedEnvironment

logger = logging.getLogger(__name__)

# ── SSRF Playground — allowed internal ranges for simulation ──────────────────
# In production these would be blocked. The playground simulates responses
# so learners can understand the attack without exposing real infrastructure.

SIMULATED_INTERNAL_RESPONSES = {
    '169.254.169.254': {
        '/latest/meta-data/': 'ami-id\nami-launch-index\nhostname\ninstance-id\nlocal-ipv4\npublic-ipv4\nsecurity-credentials/',
        '/latest/meta-data/instance-id': 'i-0a1b2c3d4e5f67890',
        '/latest/meta-data/local-ipv4':  '10.0.1.42',
        '/latest/meta-data/security-credentials/': 'EC2RoleForPyGoat',
        '/latest/meta-data/security-credentials/EC2RoleForPyGoat':
            '{\n  "AccessKeyId": "ASIA_SIMULATED_KEY",\n  "SecretAccessKey": "SIMULATED_SECRET",\n  "Token": "SIMULATED_TOKEN",\n  "Expiration": "2026-01-01T00:00:00Z"\n}',
    },
    'localhost': {
        '/': '{"status":"ok","service":"internal-api","version":"2.1.0"}',
        '/admin': '{"admin_endpoints":["/admin/reset","/admin/users","/admin/config"]}',
        '/actuator': '{"_links":{"health":{},"env":{},"beans":{}}}',
    },
    '127.0.0.1': {
        '/': '{"status":"ok"}',
    },
    '10.0.0.1': {
        '/': 'Internal service: database admin panel',
    },
}


@login_required
def ssrf_playground(request):
    """Goal 6.3 — SSRF Playground."""
    history = request.session.get('ssrf_history', [])
    ctx = {'history': history}
    return render(request, 'playgrounds/ssrf.html', ctx)


@login_required
@require_http_methods(['POST'])
def ssrf_probe(request):
    """
    POST /playground/ssrf/probe/
    Body: {"url": "http://169.254.169.254/..."}

    Returns simulated response for internal addresses.
    For external addresses: makes real GET request (sandboxed by egress rules).
    """
    import json
    try:
        body = json.loads(request.body)
        target_url = body.get('url', '').strip()
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({"error": "Invalid request."}, status=400)

    if not target_url:
        return JsonResponse({"error": "URL is required."}, status=400)

    parsed = urllib.parse.urlparse(target_url)
    host   = parsed.hostname or ''
    path   = parsed.path or '/'

    # Check if this is a simulated internal target
    sim_host = None
    for known_host in SIMULATED_INTERNAL_RESPONSES:
        if host == known_host or host.startswith(known_host):
            sim_host = known_host
            break

    if sim_host:
        sim_paths = SIMULATED_INTERNAL_RESPONSES[sim_host]
        body_text = sim_paths.get(path, f'[Simulated] No response for {path}')
        result = {
            "url":       target_url,
            "status":    200,
            "headers":   {"Content-Type": "text/plain", "Server": "EC2"},
            "body":      body_text,
            "simulated": True,
            "note":      "SSRF successful — internal resource accessed via server-side request.",
        }
    else:
        # Real external request — blocked in classroom by network policy
        result = {
            "url":       target_url,
            "status":    0,
            "body":      "[Sandbox] External requests are blocked in this environment.",
            "simulated": False,
        }

    # Store in session history (last 10)
    history = request.session.get('ssrf_history', [])
    history.insert(0, {"url": target_url, "status": result["status"]})
    request.session['ssrf_history'] = history[:10]

    return JsonResponse(result)


@login_required
def ssti_playground(request):
    """Goal 6.4 — Jinja2 SSTI REPL Playground."""
    history = request.session.get('ssti_history', [])
    ctx = {'history': history}
    return render(request, 'playgrounds/ssti.html', ctx)


@login_required
@require_http_methods(['POST'])
def ssti_evaluate(request):
    """
    POST /playground/ssti/evaluate/
    Body: {"template": "{{ 7*7 }}"}

    Evaluates the template in a Jinja2 SandboxedEnvironment.
    The sandbox prevents filesystem access and dangerous builtins,
    but exposes enough to demonstrate SSTI concepts.
    """
    import json
    try:
        body = json.loads(request.body)
        template_str = body.get('template', '').strip()
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({"error": "Invalid request."}, status=400)

    if not template_str:
        return JsonResponse({"error": "Template cannot be empty."}, status=400)

    if len(template_str) > 500:
        return JsonResponse({"error": "Template too long (max 500 chars)."}, status=400)

    # Simulated context — reflects what a real app config might expose
    context = {
        'config': {
            'SECRET_KEY':   'dev-secret-exposed-via-ssti',
            'DEBUG':        True,
            'DATABASE_URL': 'sqlite:///app.db',
            'ADMIN_EMAIL':  'admin@pygoat.local',
        },
        'user': {
            'username': request.user.username,
            'role':     'user',
        },
    }

    output = None
    error  = None
    is_dangerous = False

    try:
        # SandboxedEnvironment prevents __import__, open(), os access, etc.
        env = SandboxedEnvironment(undefined=StrictUndefined)
        tmpl = env.from_string(template_str)
        output = tmpl.render(**context)

        # Flag interesting payloads for educational callout
        dangerous_patterns = ['__class__', '__mro__', '__subclasses__', 'config', '_self']
        is_dangerous = any(p in template_str for p in dangerous_patterns)

    except Exception as exc:
        error = str(exc)

    # Session history (last 20 entries)
    history = request.session.get('ssti_history', [])
    history.insert(0, {
        "template": template_str,
        "output":   output,
        "error":    error,
    })
    request.session['ssti_history'] = history[:20]

    return JsonResponse({
        "template":     template_str,
        "output":       output,
        "error":        error,
        "is_dangerous": is_dangerous,
        "note": "Sensitive config data exposed via template context." if is_dangerous else None,
    })
