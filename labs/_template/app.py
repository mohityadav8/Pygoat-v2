"""
labs/_template/app.py
──────────────────────
Scaffold for creating new PyGoat v2 lab microservices.

INSTRUCTIONS:
    1. Copy this directory: cp -r labs/_template labs/<your_lab_id>
    2. Replace LAB_ID, FLAG, and OWASP_CATEGORY below
    3. Implement the three routes: /, /lab, /secure
    4. Add templates to labs/<your_lab_id>/templates/<your_lab_id>/
    5. Add a Dockerfile (copy from this directory)
    6. Register the lab in labs.json
    7. Add to docker-compose.yml

Container API contract (DO NOT CHANGE):
    GET  /health  → {"status": "ok", "lab_id": "<id>"}
    POST /reset   → {"status": "reset", "lab_id": "<id>"}
    POST /verify  → {"flag": "FLAG{...}"} → {"success": bool, "score": int}
"""

import hashlib
import os

from flask import Flask, jsonify, render_template, request, session

app = Flask(__name__)
app.secret_key = os.environ.get('LAB_SECRET', 'template-lab-dev-secret')

# ── Customise these ───────────────────────────────────────────────────────────
LAB_ID         = 'template_lab'                           # Must match labs.json id
OWASP_CATEGORY = 'A00:2021'                               # e.g. A03:2021
DIFFICULTY     = 'beginner'                               # beginner / intermediate / advanced
FLAG           = f'FLAG{{{hashlib.sha256(b"change-this-secret").hexdigest()}}}'


# ── Container API (required — do not modify signatures) ───────────────────────

@app.route('/health')
def health():
    return jsonify({"status": "ok", "lab_id": LAB_ID})


@app.route('/reset', methods=['POST'])
def reset():
    """
    Restore all mutable state to initial vulnerable condition.
    - Re-seed the database
    - Clear any uploaded files
    - Clear server-side session state
    """
    session.clear()
    # TODO: re-seed your database here
    return jsonify({"status": "reset", "lab_id": LAB_ID})


@app.route('/verify', methods=['POST'])
def verify():
    """Accept a flag submission from the core app's LabController."""
    data = request.get_json(silent=True) or {}
    submitted = data.get('flag', '')
    if submitted == FLAG:
        return jsonify({"success": True, "score": 100, "lab_id": LAB_ID})
    return jsonify({"success": False, "score": 0})


# ── Lab Routes (customise these) ──────────────────────────────────────────────

@app.route('/')
def index():
    """
    (a) Concept page.
    Explain:  what the vulnerability is
              how it arises in real codebases
              real-world CVE or breach example
              what impact it has
    """
    return render_template('template_lab/concept.html')


@app.route('/lab', methods=['GET', 'POST'])
def lab():
    """
    (b) Interactive vulnerable environment.
    Place the intentionally vulnerable code here.
    The flag should only be obtainable by successfully exploiting the vulnerability.
    """
    flag = None
    # TODO: implement vulnerable functionality
    # flag = FLAG if <exploit_condition> else None
    return render_template('template_lab/lab.html', flag=flag)


@app.route('/secure', methods=['GET', 'POST'])
def secure():
    """
    (c) Secure implementation demonstration.
    Show the fixed version alongside an explanation of what changed and why.
    """
    return render_template('template_lab/secure.html')


# ── Startup ───────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8099)), debug=False)
