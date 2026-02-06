const Database = require("better-sqlite3");
const path = require("path");

let db = null;

function init(userDataPath) {
  const dbPath = path.join(userDataPath, "whisprly-history.db");
  db = new Database(dbPath);
  db.pragma("journal_mode = WAL");
  db.exec(`
    CREATE TABLE IF NOT EXISTS history (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      clean_text TEXT NOT NULL,
      raw_text TEXT NOT NULL,
      tone TEXT NOT NULL,
      created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    CREATE INDEX IF NOT EXISTS idx_history_created_at
      ON history(created_at DESC);
  `);
}

function addEntry(cleanText, rawText, tone) {
  if (!db) return;
  db.prepare(
    "INSERT INTO history (clean_text, raw_text, tone) VALUES (?, ?, ?)"
  ).run(cleanText, rawText, tone);
  db.prepare(
    `DELETE FROM history WHERE id NOT IN (
      SELECT id FROM history ORDER BY created_at DESC LIMIT 100
    )`
  ).run();
}

function getEntries(limit = 100) {
  if (!db) return [];
  return db
    .prepare(
      "SELECT id, clean_text, raw_text, tone, created_at FROM history ORDER BY created_at DESC LIMIT ?"
    )
    .all(limit);
}

function deleteEntry(id) {
  if (!db) return;
  db.prepare("DELETE FROM history WHERE id = ?").run(id);
}

function clearAll() {
  if (!db) return;
  db.exec("DELETE FROM history");
}

function close() {
  if (db) db.close();
}

module.exports = { init, addEntry, getEntries, deleteEntry, clearAll, close };
