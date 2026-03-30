"""
core/services/lab_controller.py
────────────────────────────────
Manages lab container lifecycle: health check, launch, reset.

Uses Docker SDK when USE_DOCKER_SDK=True (production).
Falls back to subprocess when running without Docker (local dev).

Each lab container must expose:
    GET  /health  → {"status": "ok", "lab_id": "<id>"}
    POST /reset   → restores DB/state to initial vulnerable condition
    POST /verify  → {"flag": "FLAG{...}"} → {"success": bool, "score": int}
"""

import json
import logging
import os
import subprocess
from typing import Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class LabController:
    """
    Abstraction layer between the Django core app and lab Docker containers.
    All public methods return a dict with at least {"success": bool}.
    """

    def __init__(self):
        self._labs = self._load_registry()
        self._host = settings.LAB_HOST
        self._use_sdk = settings.USE_DOCKER_SDK

        if self._use_sdk:
            try:
                import docker
                self._docker = docker.from_env()
            except Exception as exc:
                logger.warning('Docker SDK unavailable, falling back to subprocess: %s', exc)
                self._use_sdk = False

    # ── Registry ─────────────────────────────────────────────────────────────

    def _load_registry(self) -> dict:
        with open(settings.LABS_JSON_PATH) as f:
            data = json.load(f)
        return {lab['id']: lab for lab in data['labs'] if lab.get('enabled', True)}

    def get_lab(self, lab_id: str) -> Optional[dict]:
        return self._labs.get(lab_id)

    def all_labs(self) -> list:
        return list(self._labs.values())

    # ── Container Lifecycle ───────────────────────────────────────────────────

    def health_check(self, lab_id: str) -> dict:
        """GET /health on the lab container."""
        lab = self.get_lab(lab_id)
        if not lab:
            return {"success": False, "error": f"Unknown lab_id: {lab_id}"}
        try:
            url = f'http://{self._host}:{lab["port"]}/health'
            resp = requests.get(url, timeout=3)
            resp.raise_for_status()
            return {"success": True, "data": resp.json()}
        except requests.ConnectionError:
            return {"success": False, "error": "Container not reachable"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def reset_lab(self, lab_id: str) -> dict:
        """POST /reset — restore lab to initial vulnerable state."""
        lab = self.get_lab(lab_id)
        if not lab:
            return {"success": False, "error": f"Unknown lab_id: {lab_id}"}
        try:
            url = f'http://{self._host}:{lab["port"]}/reset'
            resp = requests.post(url, timeout=10)
            resp.raise_for_status()
            return {"success": True}
        except requests.ConnectionError:
            # Fallback: restart via Docker SDK / subprocess
            return self._restart_container(lab)
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def verify_flag(self, lab_id: str, submitted_flag: str) -> dict:
        """POST /verify with the submitted flag. Returns {success, score}."""
        lab = self.get_lab(lab_id)
        if not lab:
            return {"success": False, "error": f"Unknown lab_id: {lab_id}"}
        try:
            url = f'http://{self._host}:{lab["port"]}/verify'
            resp = requests.post(url, json={"flag": submitted_flag}, timeout=5)
            resp.raise_for_status()
            return resp.json()
        except requests.ConnectionError:
            return {"success": False, "error": "Container not reachable"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    # ── Docker Internals ──────────────────────────────────────────────────────

    def _restart_container(self, lab: dict) -> dict:
        """Restart the container for a given lab."""
        image = lab['image']
        port  = lab['port']
        try:
            if self._use_sdk:
                containers = self._docker.containers.list(
                    filters={"ancestor": image}
                )
                for c in containers:
                    c.restart()
                return {"success": True}
            else:
                result = subprocess.run(
                    ['docker', 'restart', image],
                    capture_output=True, text=True, timeout=15
                )
                if result.returncode == 0:
                    return {"success": True}
                return {"success": False, "error": result.stderr}
        except Exception as exc:
            logger.error('Container restart failed for %s: %s', image, exc)
            return {"success": False, "error": str(exc)}

    def container_status(self, lab_id: str) -> str:
        """Return container status string: running | exited | not_found."""
        lab = self.get_lab(lab_id)
        if not lab:
            return 'not_found'
        if self._use_sdk:
            try:
                containers = self._docker.containers.list(
                    all=True, filters={"ancestor": lab['image']}
                )
                if not containers:
                    return 'not_found'
                return containers[0].status
            except Exception:
                return 'unknown'
        # Without SDK, do a quick health check as a proxy for status
        result = self.health_check(lab_id)
        return 'running' if result['success'] else 'stopped'


# ── Module-level singleton ─────────────────────────────────────────────────────
_controller: Optional[LabController] = None


def get_lab_controller() -> LabController:
    global _controller
    if _controller is None:
        _controller = LabController()
    return _controller
