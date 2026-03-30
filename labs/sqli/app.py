"""
labs/sqli/app.py
─────────────────
Goal 1 / Goal 2 — SQL Injection lab extracted into standalone Flask microservice.
Goal 3 — Follows three-stage pedagogical model:
    (a) concept page  (b) interactive vulnerable env  (c) secure demo

Intentionally vulnerable — do NOT deploy on public networks.

Lab Container API (Deliverable 2.3):
    GET  /health  → {"status": "ok", "lab_id": "sqli_a03"}
    POST /reset   → restore DB to initial state
    POST /verify  → {"flag": "FLAG{...}"} → {"success": bool, "score": int}
"""

import hashlib
import os
import sqlite3

from flask import Flask, g, jsonify, redirect, render_template, request, session, url_for

app = Flask(__name__)
app.secret_key = os.environ.get('LAB_SECRET', 'sqli-lab-dev-secret')

LAB_ID   = 'sqli_a03'
FLAG     = f'FLAG{{{hashlib.sha256(b"pygoat-sqli-a03-secret").hexdigest()}}}'
DB_PATH  = '/tmp/sqli_lab.db'


# ── Database helpers ──────────────────────────────────────────────────────────

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop('db', None)
    if db:
        db.close()


def init_db():
    """Populate the database with initial data (called on /reset)."""
    db = sqlite3.connect(DB_PATH)
    db.execute('DROP TABLE IF EXISTS users')
    db.execute('''
        CREATE TABLE users (
            id       INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            role     TEXT DEFAULT "user"
        )
    ''')
    db.execute('DROP TABLE IF EXISTS secrets')
    db.execute('''
        CREATE TABLE secrets (
            id    INTEGER PRIMARY KEY,
            value TEXT NOT NULL
        )
    ''')
    db.executemany(
        'INSERT INTO users (username, password, role) VALUES (?, ?, ?)',
        [
            ('admin',  'supersecretpassword',  'admin'),
            ('alice',  'alice123',             'user'),
            ('bob',    'bob456',               'user'),
        ],
    )
    db.execute('INSERT INTO secrets (value) VALUES (?)', (FLAG,))
    db.commit()
    db.close()


# ── Lab Container API ─────────────────────────────────────────────────────────

@app.route('/health')
def health():
    return jsonify({"status": "ok", "lab_id": LAB_ID})


@app.route('/reset', methods=['POST'])
def reset():
    init_db()
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
    """(a) Concept page — explains SQL Injection with real-world context."""
    return render_template('sqli/concept.html', lab_id=LAB_ID)


@app.route('/lab', methods=['GET', 'POST'])
def lab():
    """(b) Interactive vulnerable login form."""
    result = None
    query  = None
    error  = None

    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')

        db = get_db()
        # ── VULNERABLE: raw string concatenation ──
        query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
        try:
            cur = db.execute(query)
            rows = cur.fetchall()
            if rows:
                result = [dict(r) for r in rows]
                if any(r['role'] == 'admin' for r in result):
                    session['flag'] = FLAG
            else:
                error = 'Invalid credentials.'
        except sqlite3.OperationalError as exc:
            error = f'DB error: {exc}'

    flag = session.get('flag') if result else None
    return render_template('sqli/lab.html', result=result, query=query, error=error, flag=flag)


@app.route('/secure')
def secure():
    """(c) Secure implementation — parameterised query demo."""
    return render_template('sqli/secure.html')


@app.route('/secure/login', methods=['POST'])
def secure_login():
    username = request.form.get('username', '')
    password = request.form.get('password', '')
    db = get_db()
    # ── SECURE: parameterised query ──
    query = 'SELECT * FROM users WHERE username=? AND password=?'
    cur = db.execute(query, (username, password))
    row = cur.fetchone()
    result = dict(row) if row else None
    return render_template('sqli/secure.html', result=result, query=query)


# ── Startup ───────────────────────────────────────────────────────────────────

with app.app_context():
    init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8001)), debug=False)
