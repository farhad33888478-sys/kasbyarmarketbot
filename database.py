# -*- coding: utf-8 -*-
"""
لایه‌ی دیتابیس ربات kasbyarmarket (SQLite)
جدول‌ها:
  users      : کاربران ربات
  businesses : کسب‌وکارهای ثبت‌شده
  payments   : درخواست‌های پرداخت/تمدید
"""

import sqlite3
import datetime
import threading

import config

_lock = threading.Lock()


def get_conn():
    conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _lock, get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER PRIMARY KEY,
                first_name  TEXT,
                username    TEXT,
                phone       TEXT,
                created_at  TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS businesses (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id            INTEGER,
                name               TEXT,
                category           TEXT,
                description        TEXT,
                phone              TEXT,
                address            TEXT,
                photo_file_id      TEXT,
                status             TEXT DEFAULT 'pending',  -- pending/approved/rejected/expired
                created_at         TEXT,
                trial_end          TEXT,
                paid_until         TEXT,
                channel_message_id INTEGER,
                reject_reason      TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS posters (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id            INTEGER,
                caption            TEXT,
                photo_file_id      TEXT,
                status             TEXT DEFAULT 'pending',  -- pending/approved/rejected
                created_at         TEXT,
                channel_message_id INTEGER,
                reject_reason      TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                business_id    INTEGER,
                user_id        INTEGER,
                plan_id        TEXT,
                plan_title     TEXT,
                amount         INTEGER,
                receipt_file_id TEXT,
                status         TEXT DEFAULT 'pending',  -- pending/confirmed/rejected
                created_at     TEXT
            )
        """)
        conn.commit()

        # افزودن ستون platform (برای تشخیص اینکه ثبت از تلگرام بوده یا بله) - افزایشی و امن
        for table in ("users", "businesses", "posters"):
            try:
                c.execute(f"ALTER TABLE {table} ADD COLUMN platform TEXT DEFAULT 'telegram'")
                conn.commit()
            except sqlite3.OperationalError:
                pass  # ستون از قبل وجود دارد


def now_iso():
    return datetime.datetime.utcnow().isoformat()


# ---------------------------------------------------------------------
# کاربران
# ---------------------------------------------------------------------
def upsert_user(user_id, first_name, username, phone=None, platform="telegram"):
    with _lock, get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
        if c.fetchone():
            if phone:
                c.execute("UPDATE users SET first_name=?, username=?, phone=?, platform=? WHERE user_id=?",
                          (first_name, username, phone, platform, user_id))
            else:
                c.execute("UPDATE users SET first_name=?, username=?, platform=? WHERE user_id=?",
                          (first_name, username, platform, user_id))
        else:
            c.execute("INSERT INTO users (user_id, first_name, username, phone, created_at, platform) VALUES (?,?,?,?,?,?)",
                      (user_id, first_name, username, phone, now_iso(), platform))
        conn.commit()


# ---------------------------------------------------------------------
# کسب‌وکارها
# ---------------------------------------------------------------------
def create_business(user_id, name, category, description, phone, address, photo_file_id, platform="telegram"):
    with _lock, get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            INSERT INTO businesses
                (user_id, name, category, description, phone, address, photo_file_id, status, created_at, platform)
            VALUES (?,?,?,?,?,?,?, 'pending', ?, ?)
        """, (user_id, name, category, description, phone, address, photo_file_id, now_iso(), platform))
        conn.commit()
        return c.lastrowid


def get_business(biz_id):
    with _lock, get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM businesses WHERE id=?", (biz_id,))
        row = c.fetchone()
        return dict(row) if row else None


def list_businesses_by_user(user_id):
    with _lock, get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM businesses WHERE user_id=? ORDER BY id DESC", (user_id,))
        return [dict(r) for r in c.fetchall()]


def approve_business(biz_id, channel_message_id):
    trial_end = (datetime.datetime.utcnow() + datetime.timedelta(days=config.FREE_TRIAL_DAYS)).isoformat()
    with _lock, get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            UPDATE businesses
            SET status='approved', trial_end=?, paid_until=?, channel_message_id=?
            WHERE id=?
        """, (trial_end, trial_end, channel_message_id, biz_id))
        conn.commit()
    return trial_end


def reject_business(biz_id, reason=""):
    with _lock, get_conn() as conn:
        c = conn.cursor()
        c.execute("UPDATE businesses SET status='rejected', reject_reason=? WHERE id=?", (reason, biz_id))
        conn.commit()


def set_business_expired(biz_id):
    with _lock, get_conn() as conn:
        c = conn.cursor()
        c.execute("UPDATE businesses SET status='expired' WHERE id=?", (biz_id,))
        conn.commit()


def extend_business(biz_id, days):
    biz = get_business(biz_id)
    base = datetime.datetime.utcnow()
    if biz.get("paid_until"):
        try:
            current_end = datetime.datetime.fromisoformat(biz["paid_until"])
            if current_end > base:
                base = current_end
        except ValueError:
            pass
    new_end = base + datetime.timedelta(days=days)
    with _lock, get_conn() as conn:
        c = conn.cursor()
        c.execute("UPDATE businesses SET paid_until=?, status='approved' WHERE id=?",
                  (new_end.isoformat(), biz_id))
        conn.commit()
    return new_end.isoformat()


def list_pending_businesses():
    with _lock, get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM businesses WHERE status='pending' ORDER BY id ASC")
        return [dict(r) for r in c.fetchall()]


def list_approved_businesses():
    with _lock, get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM businesses WHERE status='approved'")
        return [dict(r) for r in c.fetchall()]


def set_channel_message_id(biz_id, message_id):
    with _lock, get_conn() as conn:
        c = conn.cursor()
        c.execute("UPDATE businesses SET channel_message_id=? WHERE id=?", (message_id, biz_id))
        conn.commit()


# ---------------------------------------------------------------------
# پرداخت‌ها
# ---------------------------------------------------------------------
def create_payment(business_id, user_id, plan_id, plan_title, amount):
    with _lock, get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            INSERT INTO payments (business_id, user_id, plan_id, plan_title, amount, status, created_at)
            VALUES (?,?,?,?,?, 'pending', ?)
        """, (business_id, user_id, plan_id, plan_title, amount, now_iso()))
        conn.commit()
        return c.lastrowid


def attach_receipt(payment_id, file_id):
    with _lock, get_conn() as conn:
        c = conn.cursor()
        c.execute("UPDATE payments SET receipt_file_id=? WHERE id=?", (file_id, payment_id))
        conn.commit()


def get_payment(payment_id):
    with _lock, get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM payments WHERE id=?", (payment_id,))
        row = c.fetchone()
        return dict(row) if row else None


def confirm_payment(payment_id):
    with _lock, get_conn() as conn:
        c = conn.cursor()
        c.execute("UPDATE payments SET status='confirmed' WHERE id=?", (payment_id,))
        conn.commit()


def reject_payment(payment_id):
    with _lock, get_conn() as conn:
        c = conn.cursor()
        c.execute("UPDATE payments SET status='rejected' WHERE id=?", (payment_id,))
        conn.commit()


# ---------------------------------------------------------------------
# پوسترهای تبلیغاتی (کاملاً مجزا از کسب‌وکارها؛ بدون اشتراک/پرداخت)
# ---------------------------------------------------------------------
def create_poster(user_id, caption, photo_file_id, platform="telegram"):
    with _lock, get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            INSERT INTO posters (user_id, caption, photo_file_id, status, created_at, platform)
            VALUES (?,?,?, 'pending', ?, ?)
        """, (user_id, caption, photo_file_id, now_iso(), platform))
        conn.commit()
        return c.lastrowid


def get_poster(poster_id):
    with _lock, get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM posters WHERE id=?", (poster_id,))
        row = c.fetchone()
        return dict(row) if row else None


def list_posters_by_user(user_id):
    with _lock, get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM posters WHERE user_id=? ORDER BY id DESC", (user_id,))
        return [dict(r) for r in c.fetchall()]


def list_pending_posters():
    with _lock, get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM posters WHERE status='pending' ORDER BY id ASC")
        return [dict(r) for r in c.fetchall()]


def approve_poster(poster_id, channel_message_id):
    with _lock, get_conn() as conn:
        c = conn.cursor()
        c.execute("UPDATE posters SET status='approved', channel_message_id=? WHERE id=?",
                  (channel_message_id, poster_id))
        conn.commit()


def reject_poster(poster_id, reason=""):
    with _lock, get_conn() as conn:
        c = conn.cursor()
        c.execute("UPDATE posters SET status='rejected', reject_reason=? WHERE id=?", (reason, poster_id))
        conn.commit()
