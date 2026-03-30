r if you want to just overwrite the remote (since it only has a blank README):

powershell
git push -u origin main --force
The --force is safe here because the remote only has your empty README — nothing important will be lost.

1774859570722_image.png
2:03 PM

Identified merge editor state and required action
Identified merge editor state and required action
Git opened a merge commit message editor and is waiting for you to close it. You can see "Waiting for editor to close the file..." at the bottom.

Look at your VS Code tabs at the top — there should be a tab that says "MERGE_MSG" or "Git Commit Message".

Just close that tab (click the X on it), and the push will continue automatically.

If you don't see it, press Ctrl+Shift+G (Source Control panel) in VS Code — the merge commit file should be open there. Close it and the terminal will unblock and finish the push.

1774859696056_image.png
2:04 PM

Thought for 0s
Thought for 0s
I can see it clearly. Just click the "Continue" button (the blue button on the left panel) and it will complete the merge and finish the push automatically.

1774859784811_image.png
2:06 PM

Thought for 1s
Thought for 1s
The merge commit is done (I can see it in the git graph on the left). Now close the MERGE_MSG tab by clicking the X on it at the top, then run this in the terminal:

powershell
git push -u origin main
That's the final step — your code will be on GitHub.

give readme for this

2:08 PM

Architected comprehensive README documentation for PyGoat v2
Architected comprehensive README documentation for PyGoat v2
Now push this to GitHub. Copy the README content and paste it into your repo, or run these commands in your VS Code terminal:

powershell
# Copy the downloaded README.md into your project folder, then:
git add README.md
git commit -m "docs: add comprehensive README for GSoC 2026 prototype"
git push
The README includes everything a maintainer needs to see — badges, project structure, quick start, all 11 lab microservices in a table, all 10 CTF challenges, deliverables mapping to proposal sections, your PyGoat PRs, and the disclaimer. It's structured to impress mentors reviewing your GSoC proposal.

Readme
Document · MD 

You are out of free messages until 6:30 PM
Upgrade



Claude is AI and can make mistakes. Please double-check responses.
Readme · MD
Copy

# 🐐 PyGoat v2 — Modernised Security Training Platform
 
[![GSoC 2026](https://img.shields.io/badge/GSoC-2026-orange?logo=google&logoColor=white)](https://summerofcode.withgoogle.com)
[![OWASP](https://img.shields.io/badge/OWASP-PyGoat-blue?logo=owasp)](https://owasp.org/www-project-pygoat/)
[![Python](https://img.shields.io/badge/Python-3.10%20|%203.11%20|%203.12-blue?logo=python)](https://python.org)
[![Django](https://img.shields.io/badge/Django-4.2-green?logo=django)](https://djangoproject.com)
[![Flask](https://img.shields.io/badge/Flask-3.0-black?logo=flask)](https://flask.palletsprojects.com)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE.md)
 
> **GSoC 2026 Proposal Prototype** — Modernising PyGoat: Microservice Architecture, Interactive Dashboards & OWASP Top 10:2026 Lab Expansion
>
> Contributor: **Mohit Yadav** | Mentors: Ardiansyah, Rupak Biswas, Garvita Kataria
 
---
 
## 📖 What is PyGoat v2?
 
PyGoat is OWASP's intentionally vulnerable Python/Django web application that teaches developers and security practitioners how common vulnerabilities arise and how to mitigate them.
 
This repository is a **working prototype** for my GSoC 2026 proposal to modernise PyGoat across 8 interconnected goals:
 
| Goal | Description | Status |
|------|-------------|--------|
| 1 | Refactor monolithic app — decouple vulnerable labs from core | ✅ Prototype |
| 2 | Microservice architecture — each lab in its own Docker container | ✅ Prototype |
| 3 | New vulnerability labs — SSTI, JWT, BOLA, Supply Chain, XXE, IDOR | ✅ Prototype |
| 4 | Interactive learner progress dashboard with XP, streaks, badges | ✅ Prototype |
| 5 | UI consistency — CSS design token system, WCAG AA compliance | ✅ Prototype |
| 6 | Expanded challenges (10 CTF tasks) + SSRF/SSTI playgrounds | ✅ Prototype |
| 7 | Multi-language labs — Node.js SQLi, PHP SSTI/LFI | ✅ Prototype |
| 8 | OWASP Top 10:2026 preparation section with stub pages | ✅ Prototype |
 
---
 
## 🗂️ Project Structure
 
```
pygoat_v2/
├── core/                          # Core Django app — dashboard, lab registry, progress
│   ├── models.py                  # UserLabAttempt, UserProfile (XP, streak, badges)
│   ├── views.py                   # dashboard, lab_registry, lab_detail, verify, reset
│   ├── context_processors.py      # Injects lab count into all templates
│   └── services/
│       ├── lab_controller.py      # Docker SDK — health/reset/verify container lifecycle
│       ├── lab_registry.py        # Reads labs.json registry
│       └── challenge_verifier.py  # HMAC flag verification + XP award engine
│
├── challenges/                    # CTF challenge app
│   ├── models.py                  # Challenge model with 3-tier hint system
│   ├── views.py                   # Flag submission, hint reveal endpoints
│   └── fixtures/challenges.json   # 10 pre-loaded CTF challenges
│
├── playgrounds/                   # Sandboxed experimentation environments
│   └── views.py                   # SSRF proxy + Jinja2 SandboxedEnvironment REPL
│
├── labs/                          # Lab microservices (each runs in its own container)
│   ├── _template/                 # Scaffold for new labs (copy to add a lab in minutes)
│   ├── sqli/app.py                # SQL Injection — Flask, raw vs parameterised queries
│   ├── ssti/app.py                # SSTI — Flask, Jinja2 render_template_string
│   ├── jwt/app.py                 # JWT — alg:none, weak secret, RS256→HS256 confusion
│   ├── bola/app.py                # BOLA — Django REST Framework, missing object-level auth
│   ├── sqli_nodejs/app.js         # SQLi — Node.js/Express + mysql2 (Goal 7)
│   └── ssti_php/index.php         # SSTI/LFI — PHP/Twig template injection (Goal 7)
│
├── static/css/
│   ├── tokens.css                 # Design token system — all colour/spacing/typography
│   └── base.css                   # Layout + components (uses tokens only, no hardcoding)
│
├── templates/
│   ├── base.html                  # Shared nav/topbar/footer — extended by all pages
│   ├── core/dashboard.html        # Learner progress dashboard
│   ├── core/lab_registry.html     # Lab browser with filters
│   ├── core/lab_detail.html       # Two-panel lab layout (description + live environment)
│   ├── core/owasp2026.html        # OWASP Top 10:2026 preparation section
│   ├── challenges/list.html       # CTF challenge arena
│   └── playgrounds/               # SSRF + SSTI playground UIs
│
├── tests/
│   ├── unit/
│   │   ├── test_challenge_verifier.py   # ChallengeVerifier, XP logic, hint bitmask
│   │   └── test_integration.py          # All API endpoints, flag pipeline, dashboard
│   └── e2e/
│       └── test_lab_flow.py             # Playwright — register→lab→flag full journey
│
├── labs.json                      # Central lab registry (id, port, OWASP category, XP)
├── docker-compose.yml             # All services — core + 9 lab containers
├── Dockerfile                     # Core app container
└── .github/workflows/ci.yml       # CI — Python 3.10/3.11/3.12, pytest, mypy, Playwright
```
 
---
 
## ⚡ Quick Start
 
### Option 1 — Docker Compose (recommended)
 
```bash
git clone https://github.com/mohityadav8/Pygoat-v2.git
cd Pygoat-v2
 
# Start everything (core app + all lab containers)
docker compose up --build
 
# Open in browser
open http://localhost:8000
```
 
### Option 2 — Local development (without Docker)
 
```bash
git clone https://github.com/mohityadav8/Pygoat-v2.git
cd Pygoat-v2
 
# Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
 
# Install dependencies
pip install -r requirements.txt
 
# Run migrations
python manage.py migrate
 
# Load challenge fixtures
python manage.py loaddata challenges/fixtures/challenges.json
 
# Start the server
python manage.py runserver
```
 
> **Note:** Without Docker, lab environments (the iframe panels) will show as offline. The dashboard, challenges, and playgrounds work fully without Docker.
 
---
 
## 🧪 Lab Microservice Architecture
 
Each lab runs as an independent Docker container exposing a minimal HTTP API:
 
```
GET  /health  →  {"status": "ok", "lab_id": "<id>"}
POST /reset   →  Restores DB/state to initial vulnerable condition
POST /verify  →  {"flag": "FLAG{...}"} → {"success": bool, "score": int}
```
 
The core Django app's `LabController` service communicates with lab containers over an internal Docker network (`pygoat_net`) — lab code is completely isolated from the authentication system and learner data.
 
### Available Labs
 
| Lab | OWASP | Language | Port | Difficulty |
|-----|-------|----------|------|------------|
| SQL Injection | A03:2021 | Python/Flask | 8001 | Beginner |
| Cross-Site Scripting | A03:2021 | Python/Flask | 8002 | Beginner |
| CSRF | A01:2021 | Python/Flask | 8003 | Beginner |
| IDOR | A01:2021 | Python/Flask | 8004 | Beginner |
| Server-Side Template Injection | A03:2021 | Python/Flask | 8005 | Intermediate |
| XML External Entity (XXE) | A05:2021 | Python/Flask | 8006 | Intermediate |
| JWT Authentication Bypass | A07:2021 | Python/Flask | 8007 | Intermediate |
| API Security — BOLA | A01:2021 | Python/DRF | 8008 | Advanced |
| Supply Chain Attack | A08:2021 | Python/Flask | 8009 | Advanced |
| SQLi (Node.js) | A03:2021 | Node.js/Express | 8010 | Intermediate |
| SSTI/LFI (PHP) | A03:2021 | PHP/Twig | 8011 | Advanced |
 
---
 
## 📊 Dashboard Features (Goal 4)
 
- **XP Points** — awarded on lab/challenge completion, reduced per hint used
- **Day Streak** — consecutive daily activity tracking
- **Badges** — First SQLi, XSS Master, CSRF Hunter, 7-Day Streak, Completionist, etc.
- **Per-OWASP-category progress** — completion percentage with animated bars
- **Learning path tiers** — Beginner → Intermediate → Advanced with recommended sequence
- **Recent activity feed** — last 5 completed labs with scores
- **LMS integration API** — `GET /api/progress/` returns JSON for external systems
 
---
 
## 🚩 Challenge Arena (Goal 6)
 
10 CTF-style challenges with automated flag verification:
 
| # | Title | Category | XP |
|---|-------|----------|----|
| C01 | Login Bypass Classic | SQLi | 100 |
| C02 | Cookie Monster | Auth | 120 |
| C03 | Reflected Glory | XSS | 100 |
| C04 | Other People's Orders | IDOR | 140 |
| C05 | None of Your Algorithm | JWT | 150 |
| C06 | Template Troubles | SSTI | 160 |
| C07 | Blind Date | SQLi (Blind) | 200 |
| C08 | Cross-Site Forgery Art | CSRF | 130 |
| C09 | Metadata Madness | SSRF | 180 |
| C10 | Pickle Rick | Deserialization | 200 |
 
**3-tier hint system** per challenge:
- 💡 Cryptic hint — free
- 🔦 Direct hint — costs 10 XP from score
- 📖 Full walkthrough — costs 30 XP from score
 
---
 
## 🔬 Playgrounds (Goal 6)
 
| Playground | Description |
|------------|-------------|
| SSRF | Sandboxed server-side HTTP client — probe simulated AWS metadata, internal APIs |
| Jinja2 SSTI REPL | SandboxedEnvironment template evaluator with payload history and annotation |
 
---
 
## 🛡️ OWASP Top 10:2026 (Goal 8)
 
A forward-looking section covering draft categories anticipated for the 2026 update:
 
- **API Security Failures** — BOLA, broken function-level auth, excessive data exposure
- **AI/ML Security Risks** — prompt injection, model inversion, training data poisoning
- **Supply Chain Attacks** — dependency confusion, typosquatting, compromised CI/CD
- **Injection (Expanded)** — SSTI, LDAP injection now first-class members
- **Software & Data Integrity** — CI/CD pipeline integrity, microservice deserialisation
 
---
 
## 🧪 Running Tests
 
```bash
# Install dev dependencies
pip install -r requirements.txt  # includes pytest, playwright, mypy
 
# Layer 1 — Unit tests
pytest tests/unit/test_challenge_verifier.py -v
 
# Layer 2 — Integration tests
pytest tests/unit/test_integration.py -v
 
# Layer 3 — E2E tests (requires running server)
python manage.py runserver &
pytest tests/e2e/ -v
 
# With coverage
pytest tests/ --cov=core --cov=challenges --cov=playgrounds --cov-report=term-missing
```
 
---
 
## 🏗️ Adding a New Lab
 
```bash
# 1. Copy the scaffold
cp -r labs/_template labs/your_lab_name
 
# 2. Edit labs/your_lab_name/app.py
#    - Set LAB_ID, FLAG, OWASP_CATEGORY
#    - Implement /, /lab, /secure routes
 
# 3. Register in labs.json
#    Add entry with id, port, difficulty, xp_reward, etc.
 
# 4. Add to docker-compose.yml
#    Copy an existing lab service block, change name/port
 
# 5. Add templates in labs/your_lab_name/templates/
```
 
The `_template/app.py` scaffold documents every step. A new lab can be added in under 2 hours once the microservice foundation is in place.
 
---
 
## 🔧 CI/CD Pipeline
 
GitHub Actions runs on every push and PR:
 
```
lint     →  flake8 + ruff + mypy (Python 3.12)
hadolint →  All Dockerfiles checked
test     →  pytest matrix: Python 3.10 / 3.11 / 3.12
coverage →  Uploaded to Codecov
e2e      →  Playwright browser tests (main branch only)
lab-test →  Individual lab microservice unit tests
```
 
---
 
## 📋 GSoC 2026 Deliverables Mapping
 
| Proposal Deliverable | File(s) |
|----------------------|---------|
| 1.3 Lab extraction scaffold | `labs/_template/app.py`, `labs/sqli/app.py` |
| 2.2 Master docker-compose | `docker-compose.yml` |
| 2.3 Lab registry config | `labs.json` |
| 2.4 Internal REST API | `core/services/lab_controller.py` |
| 3.x New vulnerability labs | `labs/ssti/`, `labs/jwt/`, `labs/bola/` |
| 4.1 Dashboard models | `core/models.py` — `UserLabAttempt`, `UserProfile` |
| 4.2 Dashboard view | `core/views.py::dashboard`, `templates/core/dashboard.html` |
| 4.3 Learning path tiers | `templates/core/dashboard.html` |
| 4.6 LMS REST API | `core/views.py::api_progress` |
| 5.1 Design token system | `static/css/tokens.css` |
| 5.2 Base template | `templates/base.html` |
| 5.3 Standardised lab layout | `templates/core/lab_detail.html` |
| 6.1 10 challenge tasks | `challenges/fixtures/challenges.json` |
| 6.2 3-tier hint system | `challenges/views.py::reveal_hint`, `core/models.py::use_hint` |
| 6.3 SSRF playground | `playgrounds/views.py::ssrf_playground` |
| 6.4 SSTI playground | `playgrounds/views.py::ssti_evaluate` |
| 7.1 Node.js SQLi lab | `labs/sqli_nodejs/app.js` |
| 7.2 PHP SSTI/LFI lab | `labs/ssti_php/index.php` |
| 8.2 OWASP 2026 stubs | `templates/core/owasp2026.html` |
| 8.3 API Security lab | `labs/bola/app.py` |
| Testing Layer 1 | `tests/unit/test_challenge_verifier.py` |
| Testing Layer 2 | `tests/unit/test_integration.py` |
| Testing Layer 3 | `tests/e2e/test_lab_flow.py` |
| CI/CD pipeline | `.github/workflows/ci.yml` |
 
---
 
## 👤 About the Contributor
 
**Mohit Yadav** — B.Tech CSE (Full-Stack Dev), Chandigarh University
 
- GitHub: [@mohityadav8](https://github.com/mohityadav8)
- LinkedIn: [mohit-yadav-6b2319305](https://linkedin.com/in/mohit-yadav-6b2319305)
- Email: ymohit799057@gmail.com
 
**PyGoat Contributions:**
- PR [#420](https://github.com/adeyosemanputra/pygoat/pull/420) — Fix SQLi via Django ORM
- PR [#422](https://github.com/adeyosemanputra/pygoat/pull/422) — Add SECURITY.md policy
- PR [#425](https://github.com/adeyosemanputra/pygoat/pull/425) — Fix error() view returning None
- PR [#448](https://github.com/adeyosemanputra/pygoat/pull/448) — Fix SSTI in filter_blog
- PR [#459](https://github.com/adeyosemanputra/pygoat/pull/459) — Fix broken authentication
 
---
 
## ⚠️ Disclaimer
 
> **This application is intentionally vulnerable.** It is designed for security education only.
> Never deploy PyGoat on a public-facing server or any network accessible to untrusted users.
> Always run it in an isolated local or classroom environment.
 
---
 
## 📄 License
 
MIT License — see [LICENSE.md](LICENSE.md)
 
PyGoat is an [OWASP](https://owasp.org) project. Original repository: [adeyosemanputra/pygoat](https://github.com/adeyosemanputra/pygoat)
 
