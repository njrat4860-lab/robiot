import json
import time
from pathlib import Path

import aiosqlite

DEFAULT_WINDOW_SECONDS = 3600
FREE_RATING_TTL_SECONDS = 30 * 24 * 60 * 60
PAID_RATING_TTL_SECONDS = 90 * 24 * 60 * 60
FREE_RATING_HISTORY_LIMIT = 3
PAID_RATING_HISTORY_LIMIT = 5
TOTAL_RATING_HISTORY_LIMIT = FREE_RATING_HISTORY_LIMIT + PAID_RATING_HISTORY_LIMIT

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    gender TEXT,
    created_at INTEGER,
    free_window_start INTEGER,
    free_used INTEGER DEFAULT 0,
    total_ratings INTEGER DEFAULT 0,
    paid_credits INTEGER DEFAULT 0,
    unlimited_until INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    created_at INTEGER,
    mode TEXT,
    gender TEXT,
    psl REAL,
    quality REAL,
    metrics_json TEXT,
    warnings_json TEXT,
    paid INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_ratings_user_paid_id ON ratings (user_id, paid, id DESC);
CREATE INDEX IF NOT EXISTS idx_ratings_created_at ON ratings (created_at);
CREATE TABLE IF NOT EXISTS sponsors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id TEXT,
    title TEXT,
    required INTEGER DEFAULT 1,
    sort_order INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    payload TEXT,
    amount INTEGER,
    status TEXT,
    created_at INTEGER
);
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    text TEXT,
    answer TEXT,
    status TEXT DEFAULT 'open',
    created_at INTEGER,
    answered_at INTEGER
);
CREATE INDEX IF NOT EXISTS idx_tickets_status_id ON tickets (status, id DESC);
CREATE INDEX IF NOT EXISTS idx_tickets_user_id ON tickets (user_id, id DESC);
CREATE TABLE IF NOT EXISTS disabled_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mode TEXT,
    gender TEXT,
    metric_id TEXT,
    UNIQUE(mode, gender, metric_id)
);
CREATE INDEX IF NOT EXISTS idx_disabled_metrics_mode_gender ON disabled_metrics (mode, gender);
"""

DEFAULTS = {
    "price_stars": "50",
    "free_enabled": "1",
    "paid_enabled": "0",
    "free_limit_count": "1",
    "free_limit_hours": "1",
    "queue_size": "5",
    "frontal_male_enabled": "1",
    "frontal_female_enabled": "1",
    "profile_male_enabled": "1",
    "profile_female_enabled": "1",
}
LEGACY_FREE_LIMIT_KEY = "free_limit_per_hour"


class Database:
    def __init__(self, path):
        self.path = path

    async def connect(self):
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = await aiosqlite.connect(self.path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.executescript(SCHEMA)
        await self._migrate()
        for key, value in DEFAULTS.items():
            await self.conn.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value)
            )
        await self.purge_expired_ratings(commit=False)
        await self.conn.commit()

    async def close(self):
        await self.conn.close()

    async def _migrate(self):
        columns = await self._columns("users")
        if "unlimited_until" not in columns:
            await self.conn.execute("ALTER TABLE users ADD COLUMN unlimited_until INTEGER DEFAULT 0")
        await self._migrate_free_limit()

    async def _migrate_free_limit(self):
        cursor = await self.conn.execute("SELECT value FROM settings WHERE key = ?", (LEGACY_FREE_LIMIT_KEY,))
        legacy = await cursor.fetchone()
        if legacy is None:
            return
        await self.conn.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            ("free_limit_count", legacy["value"]),
        )
        await self.conn.execute("DELETE FROM settings WHERE key = ?", (LEGACY_FREE_LIMIT_KEY,))

    async def _columns(self, table):
        cursor = await self.conn.execute(f"PRAGMA table_info({table})")
        rows = await cursor.fetchall()
        return {row["name"] for row in rows}

    async def get_user(self, user_id):
        cursor = await self.conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return await cursor.fetchone()

    async def ensure_user(self, user_id):
        user = await self.get_user(user_id)
        if user is None:
            await self.conn.execute(
                "INSERT OR IGNORE INTO users (user_id, created_at, free_used) VALUES (?, ?, 0)",
                (user_id, int(time.time())),
            )
            await self.conn.commit()
            return await self.get_user(user_id)
        return user

    async def set_gender(self, user_id, gender):
        await self.ensure_user(user_id)
        await self.conn.execute("UPDATE users SET gender = ? WHERE user_id = ?", (gender, user_id))
        await self.conn.commit()

    async def get_setting(self, key):
        cursor = await self.conn.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = await cursor.fetchone()
        return row["value"] if row else DEFAULTS.get(key, "0")

    async def set_setting(self, key, value):
        await self.conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, str(value)),
        )
        await self.conn.commit()

    async def consume_free_rating(self, user_id, limit, window_seconds=DEFAULT_WINDOW_SECONDS):
        await self.ensure_user(user_id)
        now = int(time.time())
        user = await self.get_user(user_id)
        window_start = user["free_window_start"] or 0
        if now - window_start >= window_seconds:
            window_start = now
            used = 0
        else:
            used = user["free_used"]
        if used >= limit:
            return False
        used += 1
        await self.conn.execute(
            "UPDATE users SET free_window_start = ?, free_used = ? WHERE user_id = ?",
            (window_start, used, user_id),
        )
        await self.conn.commit()
        return True

    async def free_remaining(self, user_id, limit, window_seconds=DEFAULT_WINDOW_SECONDS):
        await self.ensure_user(user_id)
        user = await self.get_user(user_id)
        now = int(time.time())
        window_start = user["free_window_start"] or 0
        if now - window_start >= window_seconds:
            return limit
        return max(0, limit - user["free_used"])

    async def free_limit(self):
        count = int(await self.get_setting("free_limit_count"))
        hours = max(1, int(await self.get_setting("free_limit_hours")))
        return count, hours

    async def disabled_metrics(self, mode, gender):
        cursor = await self.conn.execute(
            "SELECT metric_id FROM disabled_metrics WHERE mode = ? AND gender = ?",
            (mode, gender),
        )
        rows = await cursor.fetchall()
        return {row["metric_id"] for row in rows}

    async def set_metric_enabled(self, mode, gender, metric_id, enabled):
        if enabled:
            await self.conn.execute(
                "DELETE FROM disabled_metrics WHERE mode = ? AND gender = ? AND metric_id = ?",
                (mode, gender, metric_id),
            )
        else:
            await self.conn.execute(
                "INSERT OR IGNORE INTO disabled_metrics (mode, gender, metric_id) VALUES (?, ?, ?)",
                (mode, gender, metric_id),
            )
        await self.conn.commit()

    async def disabled_metrics_rows(self, limit=100):
        cursor = await self.conn.execute(
            "SELECT * FROM disabled_metrics ORDER BY mode, gender, metric_id LIMIT ?",
            (limit,),
        )
        return await cursor.fetchall()

    async def add_rating(self, user_id, mode, gender, psl, quality, metrics, warnings, paid):
        await self.ensure_user(user_id)
        await self.conn.execute(
            "INSERT INTO ratings (user_id, created_at, mode, gender, psl, quality, metrics_json, warnings_json, paid) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, int(time.time()), mode, gender, psl, quality,
             json.dumps(metrics, ensure_ascii=False), json.dumps(warnings, ensure_ascii=False), paid),
        )
        await self.conn.execute(
            "UPDATE users SET total_ratings = total_ratings + 1 WHERE user_id = ?", (user_id,)
        )
        await self.purge_expired_ratings(commit=False)
        await self.prune_user_ratings(user_id, commit=False)
        await self.conn.commit()

    async def recent_ratings(self, user_id, limit=TOTAL_RATING_HISTORY_LIMIT):
        await self.purge_expired_ratings(commit=False)
        await self.prune_user_ratings(user_id, commit=False)
        await self.conn.commit()
        cursor = await self.conn.execute(
            "SELECT * FROM ratings WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, min(limit, TOTAL_RATING_HISTORY_LIMIT)),
        )
        return await cursor.fetchall()

    async def delete_rating(self, user_id, rating_id):
        cursor = await self.conn.execute(
            "DELETE FROM ratings WHERE id = ? AND user_id = ?",
            (rating_id, user_id),
        )
        await self.conn.commit()
        return cursor.rowcount > 0

    async def purge_expired_ratings(self, commit=True):
        now = int(time.time())
        free_cutoff = now - FREE_RATING_TTL_SECONDS
        paid_cutoff = now - PAID_RATING_TTL_SECONDS
        await self.conn.execute(
            "DELETE FROM ratings WHERE (paid = 0 AND created_at < ?) OR (paid = 1 AND created_at < ?)",
            (free_cutoff, paid_cutoff),
        )
        if commit:
            await self.conn.commit()

    async def prune_user_ratings(self, user_id, commit=True):
        await self._prune_user_ratings_by_kind(user_id, 0, FREE_RATING_HISTORY_LIMIT)
        await self._prune_user_ratings_by_kind(user_id, 1, PAID_RATING_HISTORY_LIMIT)
        if commit:
            await self.conn.commit()

    async def sponsors(self):
        cursor = await self.conn.execute("SELECT * FROM sponsors ORDER BY sort_order")
        return await cursor.fetchall()

    async def add_sponsor(self, channel_id, title, required):
        cursor = await self.conn.execute(
            "SELECT COALESCE(MAX(sort_order), 0) + 1 FROM sponsors"
        )
        row = await cursor.fetchone()
        order = row[0]
        await self.conn.execute(
            "INSERT INTO sponsors (channel_id, title, required, sort_order) VALUES (?, ?, ?, ?)",
            (channel_id, title, required, order),
        )
        await self.conn.commit()

    async def remove_sponsor(self, sponsor_id):
        await self.conn.execute("DELETE FROM sponsors WHERE id = ?", (sponsor_id,))
        await self.conn.commit()

    async def total_ratings(self):
        cursor = await self.conn.execute("SELECT COUNT(*) FROM ratings")
        return (await cursor.fetchone())[0]

    async def total_users(self):
        cursor = await self.conn.execute("SELECT COUNT(*) FROM users")
        return (await cursor.fetchone())[0]

    async def average_psl(self):
        cursor = await self.conn.execute("SELECT AVG(psl) FROM ratings WHERE psl IS NOT NULL")
        return (await cursor.fetchone())[0]

    async def rating_counts_by_mode(self):
        cursor = await self.conn.execute("SELECT mode, COUNT(*) FROM ratings GROUP BY mode")
        return await cursor.fetchall()

    async def add_credit(self, user_id):
        await self.ensure_user(user_id)
        await self.conn.execute(
            "UPDATE users SET paid_credits = paid_credits + 1 WHERE user_id = ?", (user_id,)
        )
        await self.conn.commit()

    async def paid_credits(self, user_id):
        await self.ensure_user(user_id)
        user = await self.get_user(user_id)
        return user["paid_credits"] or 0

    async def set_unlimited(self, user_id, until):
        await self.ensure_user(user_id)
        await self.conn.execute(
            "UPDATE users SET unlimited_until = ? WHERE user_id = ?",
            (until, user_id),
        )
        await self.conn.commit()

    async def has_unlimited(self, user_id):
        await self.ensure_user(user_id)
        user = await self.get_user(user_id)
        until = user["unlimited_until"] or 0
        return until == -1 or until > int(time.time())

    async def consume_credit(self, user_id):
        await self.ensure_user(user_id)
        user = await self.get_user(user_id)
        if (user["paid_credits"] or 0) <= 0:
            return False
        await self.conn.execute(
            "UPDATE users SET paid_credits = paid_credits - 1 WHERE user_id = ?", (user_id,)
        )
        await self.conn.commit()
        return True

    async def add_payment(self, user_id, payload, amount, status):
        await self.conn.execute(
            "INSERT INTO payments (user_id, payload, amount, status, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, payload, amount, status, int(time.time())),
        )
        await self.conn.commit()

    async def add_ticket(self, user_id, text):
        await self.conn.execute(
            "INSERT INTO tickets (user_id, text, status, created_at) VALUES (?, ?, 'open', ?)",
            (user_id, text, int(time.time())),
        )
        await self.conn.commit()

    async def open_tickets(self, limit=10):
        cursor = await self.conn.execute(
            "SELECT * FROM tickets WHERE status = 'open' ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return await cursor.fetchall()

    async def get_ticket(self, ticket_id):
        cursor = await self.conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
        return await cursor.fetchone()

    async def answer_ticket(self, ticket_id, answer):
        cursor = await self.conn.execute(
            "UPDATE tickets SET answer = ?, status = 'answered', answered_at = ? WHERE id = ? AND status = 'open'",
            (answer, int(time.time()), ticket_id),
        )
        await self.conn.commit()
        return cursor.rowcount > 0

    async def close_ticket(self, ticket_id):
        cursor = await self.conn.execute(
            "UPDATE tickets SET status = 'closed' WHERE id = ? AND status = 'open'",
            (ticket_id,),
        )
        await self.conn.commit()
        return cursor.rowcount > 0

    async def _prune_user_ratings_by_kind(self, user_id, paid, limit):
        await self.conn.execute(
            "DELETE FROM ratings WHERE user_id = ? AND paid = ? AND id NOT IN "
            "(SELECT id FROM ratings WHERE user_id = ? AND paid = ? ORDER BY id DESC LIMIT ?)",
            (user_id, paid, user_id, paid, limit),
        )
