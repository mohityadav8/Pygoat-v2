<?php
/**
 * labs/ssti_php/index.php
 * ────────────────────────
 * Goal 7 — Deliverable 7.2 (Stretch)
 * PHP SSTI / LFI lab: Twig template injection + include() file traversal.
 * Same A03:2021 vulnerability, PHP/Twig runtime instead of Python/Jinja2.
 *
 * Container API endpoints handled by api.php (included below):
 *   GET  /health  → {"status":"ok","lab_id":"ssti_php"}
 *   POST /reset   → {"status":"reset","lab_id":"ssti_php"}
 *   POST /verify  → {"flag":"FLAG{...}"} → {"success":bool}
 *
 * INTENTIONALLY VULNERABLE — do NOT deploy on public networks.
 */

require_once __DIR__ . '/vendor/autoload.php';

use Twig\Environment;
use Twig\Loader\ArrayLoader;

define('LAB_ID', 'ssti_php');
define('FLAG', 'FLAG{' . hash('sha256', 'pygoat-ssti-php-secret') . '}');

$action = $_GET['action'] ?? 'concept';

// ── Container API ──────────────────────────────────────────────────────────────
if ($_SERVER['REQUEST_METHOD'] === 'GET' && $action === 'health') {
    header('Content-Type: application/json');
    echo json_encode(['status' => 'ok', 'lab_id' => LAB_ID]);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] === 'POST' && $action === 'reset') {
    header('Content-Type: application/json');
    session_unset();
    echo json_encode(['status' => 'reset', 'lab_id' => LAB_ID]);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] === 'POST' && $action === 'verify') {
    header('Content-Type: application/json');
    $data = json_decode(file_get_contents('php://input'), true);
    $submitted = trim($data['flag'] ?? '');
    echo json_encode([
        'success' => hash_equals(FLAG, $submitted),
        'score'   => hash_equals(FLAG, $submitted) ? 100 : 0,
    ]);
    exit;
}

// ── (a) Concept page ──────────────────────────────────────────────────────────
if ($action === 'concept') {
    include __DIR__ . '/templates/concept.php';
    exit;
}

// ── (b) SSTI — Vulnerable Twig rendering ──────────────────────────────────────
if ($action === 'ssti_lab') {
    $name   = $_POST['name'] ?? '';
    $output = null;
    $error  = null;

    if ($_SERVER['REQUEST_METHOD'] === 'POST' && $name !== '') {
        try {
            /**
             * VULNERABLE: user input is interpolated directly into the template
             * string before it reaches the Twig engine.
             * A learner can inject: {{_self.env.getExtension('Twig\\Extension\\DebugExtension')}}
             * or traverse to system() via filter chains.
             */
            $templateStr = "Hello, {$name}! Your order is ready.";

            $loader = new ArrayLoader(['greeting' => $templateStr]);
            $twig   = new Environment($loader, ['debug' => true]);

            // Store FLAG in Twig globals so it can be extracted via SSTI
            $twig->addGlobal('app_flag', FLAG);
            $twig->addGlobal('db_password', 'lab-db-secret-9a8b7c');

            $output = $twig->render('greeting', []);
        } catch (\Throwable $e) {
            $error = $e->getMessage();
        }
    }
    include __DIR__ . '/templates/ssti_lab.php';
    exit;
}

// ── (c) LFI — Vulnerable include() ───────────────────────────────────────────
if ($action === 'lfi_lab') {
    $page   = $_GET['page'] ?? 'home';
    $output = null;
    $error  = null;

    /**
     * VULNERABLE: user-controlled $page goes directly into include().
     * Attack: ?page=../../etc/passwd or ?page=php://filter/convert.base64-encode/resource=index
     * No path sanitisation, no whitelist.
     */
    $file = __DIR__ . "/pages/{$page}.php";

    ob_start();
    try {
        // ── VULNERABLE: unsanitised path traversal ──
        include $file;
    } catch (\Throwable $e) {
        $error = "Error including file: " . $e->getMessage();
    }
    $output = ob_get_clean();

    include __DIR__ . '/templates/lfi_lab.php';
    exit;
}

// ── (d) Secure SSTI ───────────────────────────────────────────────────────────
if ($action === 'ssti_secure') {
    $name   = $_POST['name'] ?? '';
    $output = null;

    if ($_SERVER['REQUEST_METHOD'] === 'POST' && $name !== '') {
        /**
         * SECURE: pass user input as a template variable, never interpolated
         * into the template string itself.
         */
        $loader = new ArrayLoader(['greeting' => 'Hello, {{ name }}! Your order is ready.']);
        $twig   = new Environment($loader, ['debug' => false]);
        $output = $twig->render('greeting', ['name' => $name]);
    }
    include __DIR__ . '/templates/ssti_secure.php';
    exit;
}

// ── (e) Secure LFI ───────────────────────────────────────────────────────────
if ($action === 'lfi_secure') {
    $page = $_GET['page'] ?? 'home';

    // ── SECURE: strict whitelist, no path construction from user input ──
    $allowed = ['home', 'about', 'contact'];
    if (!in_array($page, $allowed, true)) {
        http_response_code(400);
        echo 'Invalid page.';
        exit;
    }
    include __DIR__ . "/pages/{$page}.php";
    exit;
}

// Default — redirect to concept
header('Location: ?action=concept');
