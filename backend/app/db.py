"""SQLite storage: users, sessions, action logs."""
import hashlib
import hmac
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

DB_PATH = Path(os.environ.get("SPICE_DB", Path(__file__).resolve().parent.parent / "spicescript.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    salt          TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'user',
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    token      TEXT PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS action_logs (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER REFERENCES users(id),
    username       TEXT NOT NULL,
    action         TEXT NOT NULL,   -- login, logout, register, run_stage
    stage          TEXT,            -- lexical, syntax, semantic, icg, run, full
    status         TEXT NOT NULL,   -- success, error
    input_snapshot TEXT,
    detail         TEXT,
    created_at     TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_logs_user ON action_logs(user_id);

CREATE TABLE IF NOT EXISTS login_failures (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    username   TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_failures_user ON login_failures(username);
"""

# ---- security settings --------------------------------------------------------
PBKDF2_ITERATIONS = 600_000      # slows down password guessing if the database ever leaks
SESSION_HOURS = 8                # a session stops working after this long
MAX_FAILED_LOGINS = 5            # wrong passwords allowed ...
LOCKOUT_SECONDS = 15 * 60        # ... within this window before logins are paused


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)


# ---- passwords --------------------------------------------------------------
# Stored as "pbkdf2_sha256$<iterations>$<hex>" so the cost can be raised later without
# breaking old accounts. Older rows (plain hex, 200,000 iterations) still verify.

def _pbkdf2(password: str, salt: str, iterations: int) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), iterations).hex()


def hash_password(password: str, salt: str) -> str:
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${_pbkdf2(password, salt, PBKDF2_ITERATIONS)}"


def verify_password(password: str, salt: str, stored: str) -> bool:
    if stored.startswith("pbkdf2_sha256$"):
        _, iterations, digest = stored.split("$")
        return hmac.compare_digest(_pbkdf2(password, salt, int(iterations)), digest)
    return hmac.compare_digest(_pbkdf2(password, salt, 200_000), stored)   # legacy rows


_DUMMY_SALT = "00" * 16


def burn_time(password: str) -> None:
    """Do the same work as a real check, so an unknown username is not faster to reject."""
    _pbkdf2(password, _DUMMY_SALT, PBKDF2_ITERATIONS)


# ---- users / sessions -------------------------------------------------------

def create_user(username: str, password: str):
    """The very first user becomes admin. Returns the new user row or None if taken."""
    salt = secrets.token_hex(16)
    with connect() as conn:
        is_first = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0
        try:
            cur = conn.execute(
                "INSERT INTO users (username, password_hash, salt, role, created_at) VALUES (?,?,?,?,?)",
                (username, hash_password(password, salt), salt, "admin" if is_first else "user", now()),
            )
        except sqlite3.IntegrityError:
            return None
        return conn.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()


def get_user_by_name(username: str):
    with connect() as conn:
        return conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()


def _token_hash(token: str) -> str:
    """Only a hash of each session token is stored, so a leaked database cannot be used to sign in."""
    return hashlib.sha256(token.encode()).hexdigest()


def _cutoff(seconds: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds)).isoformat(timespec="seconds")


def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    with connect() as conn:
        conn.execute("INSERT INTO sessions (token, user_id, created_at) VALUES (?,?,?)",
                     (_token_hash(token), user_id, now()))
    return token


def get_user_by_token(token: str):
    with connect() as conn:
        return conn.execute(
            "SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id "
            "WHERE s.token = ? AND s.created_at >= ?",
            (_token_hash(token), _cutoff(SESSION_HOURS * 3600)),
        ).fetchone()


def delete_session(token: str) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (_token_hash(token),))


def purge_expired_sessions() -> None:
    with connect() as conn:
        conn.execute("DELETE FROM sessions WHERE created_at < ?", (_cutoff(SESSION_HOURS * 3600),))


# ---- failed-login throttle --------------------------------------------------

def record_login_failure(username: str) -> None:
    with connect() as conn:
        conn.execute("INSERT INTO login_failures (username, created_at) VALUES (?,?)", (username, now()))
        conn.execute("DELETE FROM login_failures WHERE created_at < ?", (_cutoff(LOCKOUT_SECONDS),))


def lockout_seconds(username: str) -> int:
    """Seconds left before this username may try again (0 if it is not locked)."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT created_at FROM login_failures WHERE username = ? AND created_at >= ? ORDER BY id",
            (username, _cutoff(LOCKOUT_SECONDS)),
        ).fetchall()
    if len(rows) < MAX_FAILED_LOGINS:
        return 0
    counted = datetime.fromisoformat(rows[-MAX_FAILED_LOGINS]["created_at"])
    left = counted + timedelta(seconds=LOCKOUT_SECONDS) - datetime.now(timezone.utc)
    return max(0, int(left.total_seconds()) + 1)


def clear_login_failures(username: str) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM login_failures WHERE username = ?", (username,))


# ---- logs -------------------------------------------------------------------

def add_log(user_id, username, action, stage=None, status="success", input_snapshot=None, detail=None) -> None:
    snapshot = input_snapshot[:2000] if input_snapshot else None  # keep rows small
    with connect() as conn:
        conn.execute(
            "INSERT INTO action_logs (user_id, username, action, stage, status, input_snapshot, detail, created_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (user_id, username, action, stage, status, snapshot, detail, now()),
        )


def get_logs(user_id=None, limit=200):
    """user_id=None returns everyone's logs (admin view)."""
    with connect() as conn:
        if user_id is None:
            rows = conn.execute("SELECT * FROM action_logs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM action_logs WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit)
            ).fetchall()
    return [dict(r) for r in rows]
