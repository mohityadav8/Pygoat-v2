// labs/sqli_nodejs/app.js
// Goal 7 — Deliverable 7.1 (Stretch)
// Node.js/Express SQLi lab demonstrating mysql2 query concatenation vs
// parameterised queries — same A03:2021 vulnerability, different runtime.
//
// Container API:
//   GET  /health  → {"status":"ok","lab_id":"sqli_nodejs"}
//   POST /reset   → truncates and reseeds the database
//   POST /verify  → {"flag":"FLAG{...}"} → {"success":bool}

'use strict';

const express  = require('express');
const mysql2   = require('mysql2/promise');
const crypto   = require('crypto');
const path     = require('path');

const app    = express();
const PORT   = parseInt(process.env.PORT || '8010', 10);
const LAB_ID = 'sqli_nodejs';
const FLAG   = `FLAG{${crypto.createHash('sha256').update('pygoat-sqli-nodejs-secret').digest('hex')}}`;

app.use(express.urlencoded({ extended: true }));
app.use(express.json());
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));

// ── Database pool ──────────────────────────────────────────────────────────────
const pool = mysql2.createPool({
  host:     process.env.DB_HOST     || 'localhost',
  user:     process.env.DB_USER     || 'root',
  password: process.env.DB_PASSWORD || 'labpassword',
  database: process.env.DB_NAME     || 'sqli_lab',
  waitForConnections: true,
  connectionLimit: 5,
});

async function initDb() {
  const conn = await pool.getConnection();
  await conn.query(`
    CREATE TABLE IF NOT EXISTS users (
      id       INT AUTO_INCREMENT PRIMARY KEY,
      username VARCHAR(100) NOT NULL,
      password VARCHAR(100) NOT NULL,
      role     VARCHAR(20)  DEFAULT 'user'
    )
  `);
  await conn.query('DELETE FROM users');
  await conn.query(`
    INSERT INTO users (username, password, role) VALUES
      ('admin', 'supersecretpassword', 'admin'),
      ('alice', 'alice123',            'user'),
      ('bob',   'bob456',              'user')
  `);
  conn.release();
}

// ── Container API ──────────────────────────────────────────────────────────────

app.get('/health', (_req, res) => {
  res.json({ status: 'ok', lab_id: LAB_ID });
});

app.post('/reset', async (_req, res) => {
  try {
    await initDb();
    res.json({ status: 'reset', lab_id: LAB_ID });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/verify', (req, res) => {
  const submitted = (req.body.flag || '').trim();
  res.json({ success: submitted === FLAG, score: submitted === FLAG ? 100 : 0 });
});

// ── Lab Routes ──────────────────────────────────────────────────────────────────

// (a) Concept page
app.get('/', (_req, res) => {
  res.render('concept', { lab_id: LAB_ID });
});

// (b) Vulnerable login — string concatenation into mysql2 query
app.get('/lab', (_req, res) => {
  res.render('lab', { result: null, query: null, error: null, flag: null });
});

app.post('/lab', async (req, res) => {
  const { username = '', password = '' } = req.body;

  // ── VULNERABLE: raw string interpolation ──
  const query = `SELECT * FROM users WHERE username='${username}' AND password='${password}'`;

  let result = null;
  let error  = null;
  let flag   = null;

  try {
    const [rows] = await pool.query(query);     // ← no parameterisation
    result = rows;
    if (rows.some(r => r.role === 'admin')) {
      flag = FLAG;
    }
  } catch (err) {
    error = `DB error: ${err.sqlMessage || err.message}`;
  }

  res.render('lab', { result, query, error, flag });
});

// (c) Secure — parameterised query with mysql2 placeholders
app.get('/secure', (_req, res) => {
  res.render('secure', { result: null, query: null });
});

app.post('/secure', async (req, res) => {
  const { username = '', password = '' } = req.body;

  // ── SECURE: parameterised query — mysql2 placeholder syntax ──
  const query  = 'SELECT * FROM users WHERE username=? AND password=?';
  const [rows] = await pool.query(query, [username, password]);

  res.render('secure', {
    result: rows.length > 0 ? rows[0] : null,
    query,
  });
});

// ── Startup ────────────────────────────────────────────────────────────────────
initDb()
  .then(() => {
    app.listen(PORT, '0.0.0.0', () => {
      console.log(`[sqli-nodejs] Lab running on port ${PORT}`);
    });
  })
  .catch(err => {
    console.error('DB init failed:', err.message);
    process.exit(1);
  });
