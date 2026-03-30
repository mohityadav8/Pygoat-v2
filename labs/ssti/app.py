"""
labs/ssti/app.py
─────────────────
Goal 3 — Server-Side Template Injection lab (New Lab).
Demonstrates Jinja2 template engine exploitation.

Attack vectors:
    {{ 7*7 }}                         → arithmetic evaluation
    {{ config.items() }}              → config leak
    {{ ''.__class__.__mro__ }}        → MRO traversal
    {{ ''.__class__.__mro__[1].__subclasses__() }}  → subclass enumeration
    → ultimately leads to os.popen RCE chain

Container API: GET /health, POST /reset, POST /verify
"""

import hashlib
import os

from flask import Flask, jsonify, render_template, render_template_string, request, session
from jinja2 import Environment

app = Flask(__name__)
app.secret_key = os.environ.get('LAB_SECRET', 'ssti-lab-dev-secret')

LAB_ID = 'ssti_a03'
FLAG   = f'FLAG{{{hashlib.sha256(b"pygoat-ssti-a03-secret").hexdigest()}}}'

# Embed flag into app config so learners can extract it via config leak
app.config['INTERNAL_FLAG']    = FLAG
app.config['APP_VERSION']      = '1.0.0'
app.config['DATABASE_URL']     = 'sqlite:///app.db'
app.config['ADMIN_EMAIL']      = 'admin@pygoat.local'


# ── Container API ─────────────────────────────────────────────────────────────

@app.route('/health')
def health():
    return jsonify({"status": "ok", "lab_id": LAB_ID})


@app.route('/reset', methods=['POST'])
def reset():
    session.clear()
    return jsonify({"status": "reset", "lab_id": LAB_ID})


@app.route('/verify', methods=['POST'])
def verify():
    data = request.get_json(silent=True) or {}
    submitted = data.get('flag', '')
    if submitted == FLAG:
        return jsonify({"success": True, "score": 100, "lab_id": LAB_ID})
    return jsonify({"success": False, "score": 0})


# ── Lab Routes ────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('ssti/concept.html')


@app.route('/lab', methods=['GET', 'POST'])
def lab():
    """
    (b) Vulnerable blog name renderer.
    The user-supplied 'name' parameter is passed directly to render_template_string —
    classic SSTI via Jinja2.
    """
    output = None
    user_input = ''
    error = None

    if request.method == 'POST':
        user_input = request.form.get('name', '')
        try:
            # ── VULNERABLE: render_template_string with unsanitised input ──
            template_str = f'<p>Hello, {user_input}!</p>'
            output = render_template_string(template_str)
        except Exception as exc:
            error = str(exc)

    return render_template('ssti/lab.html', output=output, user_input=user_input, error=error)


@app.route('/secure', methods=['GET', 'POST'])
def secure():
    """
    (c) Secure implementation — use Markup.escape() or pass as variable,
    never interpolate user data into the template string.
    """
    output = None
    user_input = ''

    if request.method == 'POST':
        user_input = request.form.get('name', '')
        # ── SECURE: pass as template variable, not interpolated ──
        output = render_template_string('<p>Hello, {{ name }}!</p>', name=user_input)

    return render_template('ssti/secure.html', output=output, user_input=user_input)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8005)), debug=False)
