"""
labs/jwt/app.py
───────────────
Goal 3 — JWT Authentication Bypass lab (New Lab).
Covers three attack vectors:
    1. alg:none — strip signature entirely
    2. Weak HS256 secret — brute-forceable with hashcat / john
    3. RS256 → HS256 confusion — use RS256 public key as HS256 secret

Container API: GET /health, POST /reset, POST /verify
"""

import base64
import hashlib
import json
import os

import jwt as pyjwt
from flask import Flask, jsonify, render_template, request, session

app = Flask(__name__)
app.secret_key = os.environ.get('LAB_SECRET', 'jwt-lab-dev-secret')

LAB_ID = 'jwt_a07'
FLAG   = f'FLAG{{{hashlib.sha256(b"pygoat-jwt-a07-secret").hexdigest()}}}'

# Intentionally weak HS256 secret — crackable with common wordlists
JWT_SECRET = 'secret'

USERS = {
    'alice': {'role': 'user',  'password': 'alice123'},
    'admin': {'role': 'admin', 'password': 'notguessable'},
}


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


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_token(username: str, role: str) -> str:
    payload = {'sub': username, 'role': role}
    return pyjwt.encode(payload, JWT_SECRET, algorithm='HS256')


def decode_token_vulnerable(token: str) -> dict | None:
    """
    VULNERABLE: accepts alg:none by not enforcing algorithms list.
    Also accepts any HS256 token regardless of secret strength.
    """
    try:
        # ── VULNERABLE: algorithms not restricted, options permissive ──
        return pyjwt.decode(
            token,
            JWT_SECRET,
            algorithms=['HS256', 'none'],
            options={"verify_signature": False},   # ← intentionally disabled
        )
    except Exception:
        return None


def decode_token_secure(token: str) -> dict | None:
    """SECURE: enforce algorithm, verify signature."""
    try:
        return pyjwt.decode(token, JWT_SECRET, algorithms=['HS256'])
    except Exception:
        return None


# ── Lab Routes ────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('jwt/concept.html')


@app.route('/lab/login', methods=['GET', 'POST'])
def lab_login():
    token = None
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        user = USERS.get(username)
        if user and user['password'] == password:
            token = make_token(username, user['role'])
        else:
            error = 'Invalid credentials.'
    return render_template('jwt/login.html', token=token, error=error)


@app.route('/lab/profile')
def lab_profile():
    """
    (b) Vulnerable profile endpoint — decode token without verifying signature.
    Attack: forge a token with role=admin using alg:none.
    """
    token = request.headers.get('Authorization', '').replace('Bearer ', '') or \
            request.args.get('token', '')

    payload = None
    flag    = None
    error   = None

    if token:
        payload = decode_token_vulnerable(token)
        if payload is None:
            error = 'Token decode failed.'
        elif payload.get('role') == 'admin':
            flag = FLAG

    return render_template('jwt/profile.html', payload=payload, flag=flag, error=error, token=token)


@app.route('/secure/profile')
def secure_profile():
    """(c) Secure: signature is verified, alg is enforced."""
    token = request.headers.get('Authorization', '').replace('Bearer ', '') or \
            request.args.get('token', '')

    payload = None
    error   = None

    if token:
        payload = decode_token_secure(token)
        if payload is None:
            error = 'Token verification failed — invalid signature or expired.'

    return render_template('jwt/secure_profile.html', payload=payload, error=error)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8007)), debug=False)
