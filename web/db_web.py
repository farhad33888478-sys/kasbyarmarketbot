# -*- coding: utf-8 -*-
"""
لایه‌ی دیتابیس مخصوص پنل وب.

نکته‌ی مهم: این ماژول هیچ جدولی از دیتابیس فعلی ربات (users, businesses,
payments, posters) را تغییر نمی‌دهد. فقط:
  1) یک جدول جدید web_users می‌سازد (حساب‌های ثبت‌نامی از طریق وب)
  2) یک ستون nullable به businesses اضافه می‌کند تا مالکیت وب مشخص شود

اگر کاربر وب با همان شماره موبایلی که در ربات ثبت کرده وارد شود،
حساب‌ها به‌صورت خودکار به هم متصل می‌شوند (بر اساس شماره موبایل).
"""

import sqlite3
import threading
import datetime

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from web.security import hash_password, verify_password, normalize_phone

_lock = threading.Lock()


def get_conn():
    conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def now_iso():
    return datetime.datetime.utcnow().isoformat()


def init_web_db():
    """جدول‌های وب را می‌سازد و در صورت نیاز ستون پیوند را اضافه می‌کند."""
    with _lock, get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS web_users (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name        TEXT,
                phone            TEXT UNIQUE,
                password_hash    TEXT,
                telegram_user_id INTEGER,
                created_at       TEXT
            )
        """)
        conn.commit()

        # افزودن ستون پیوند به جدول businesses (اگر قبلاً اضافه نشده باشد)
        try:
            c.execute("ALTER TABLE businesses ADD COLUMN web_user_id INTEGER")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # ستون از قبل وجود دارد

        # جدول تنظیمات عمومی سایت (پوستر هیرو، تگ‌لاین، لینک کانال‌ها و ...)
        c.execute("""
            CREATE TABLE IF NOT EXISTS web_settings (
                key   TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        conn.commit()


# ---------------------------------------------------------------------
# تنظیمات سایت (پنل ادمین)
# ---------------------------------------------------------------------
DEFAULT_SETTINGS = {
    "hero_image": "",
    "hero_tagline": "",
    "telegram_channel": "",
    "bale_channel": "",
    "support_phone": "",
    "site_logo": "",
    "about_text": "",
    "instagram": "",
    "whatsapp": "",
}


def get_all_settings():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT key, value FROM web_settings")
        rows = {r["key"]: r["value"] for r in c.fetchall()}
    merged = dict(DEFAULT_SETTINGS)
    merged.update(rows)
    return merged


def set_settings(values: dict):
    with _lock, get_conn() as conn:
        c = conn.cursor()
        for key, value in values.items():
            c.execute(
                "INSERT INTO web_settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )
        conn.commit()


# ---------------------------------------------------------------------
# کاربران وب
# ---------------------------------------------------------------------
def create_web_user(full_name, phone, password):
    phone = normalize_phone(phone)
    telegram_user_id = _find_telegram_user_by_phone(phone)

    with _lock, get_conn() as conn:
        c = conn.cursor()
        c.execute(
            """
            INSERT INTO web_users (full_name, phone, password_hash, telegram_user_id, created_at)
            VALUES (?,?,?,?,?)
            """,
            (full_name, phone, hash_password(password), telegram_user_id, now_iso()),
        )
        conn.commit()
        return c.lastrowid


def _find_telegram_user_by_phone(phone):
    """اگر کاربری با همین شماره از طریق ربات ثبت‌نام کرده بود، آیدی تلگرامش را برمی‌گرداند."""
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE phone=?", (phone,))
        row = c.fetchone()
        return row["user_id"] if row else None


def get_web_user_by_phone(phone):
    phone = normalize_phone(phone)
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM web_users WHERE phone=?", (phone,))
        row = c.fetchone()
        return dict(row) if row else None


def get_web_user_by_id(user_id):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM web_users WHERE id=?", (user_id,))
        row = c.fetchone()
        return dict(row) if row else None


def authenticate_web_user(phone, password):
    user = get_web_user_by_phone(phone)
    if user and verify_password(password, user["password_hash"]):
        return user
    return None


def phone_exists(phone):
    return get_web_user_by_phone(phone) is not None


# ---------------------------------------------------------------------
# کسب‌وکارها (از طریق وب)
# ---------------------------------------------------------------------
def create_business_web(web_user_id, name, category, description, phone, address, photo_path=None):
    with _lock, get_conn() as conn:
        c = conn.cursor()
        c.execute(
            """
            INSERT INTO businesses
                (user_id, web_user_id, name, category, description, phone, address, photo_file_id, status, created_at, platform)
            VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, 'web')
            """,
            (web_user_id, name, category, description, phone, address, photo_path, now_iso()),
        )
        conn.commit()
        return c.lastrowid


def list_businesses_by_web_user(web_user_id):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM businesses WHERE web_user_id=? ORDER BY id DESC", (web_user_id,))
        return [dict(r) for r in c.fetchall()]


def list_approved_businesses(category=None, search=None):
    query = "SELECT * FROM businesses WHERE status='approved'"
    params = []
    if category:
        query += " AND category=?"
        params.append(category)
    if search:
        query += " AND (name LIKE ? OR description LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    query += " ORDER BY id DESC"
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(query, params)
        return [dict(r) for r in c.fetchall()]


def get_business_by_id(biz_id):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM businesses WHERE id=?", (biz_id,))
        row = c.fetchone()
        return dict(row) if row else None


# ---------------------------------------------------------------------
# پنل ادمین
# ---------------------------------------------------------------------
def list_pending_businesses():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM businesses WHERE status='pending' ORDER BY id ASC")
        return [dict(r) for r in c.fetchall()]


def list_all_businesses():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM businesses ORDER BY id DESC")
        return [dict(r) for r in c.fetchall()]


def approve_business_web(biz_id):
    trial_end = (datetime.datetime.utcnow() + datetime.timedelta(days=config.FREE_TRIAL_DAYS)).isoformat()
    with _lock, get_conn() as conn:
        c = conn.cursor()
        c.execute(
            "UPDATE businesses SET status='approved', trial_end=?, paid_until=? WHERE id=?",
            (trial_end, trial_end, biz_id),
        )
        conn.commit()


def reject_business_web(biz_id, reason=""):
    with _lock, get_conn() as conn:
        c = conn.cursor()
        c.execute("UPDATE businesses SET status='rejected', reject_reason=? WHERE id=?", (reason, biz_id))
        conn.commit()


def count_stats():
    with get_conn() as conn:
        c = conn.cursor()
        stats = {}
        c.execute("SELECT COUNT(*) AS n FROM web_users")
        stats["web_users"] = c.fetchone()["n"]
        c.execute("SELECT COUNT(*) AS n FROM users")
        stats["bot_users"] = c.fetchone()["n"]
        c.execute("SELECT COUNT(*) AS n FROM businesses WHERE status='approved'")
        stats["approved_businesses"] = c.fetchone()["n"]
        c.execute("SELECT COUNT(*) AS n FROM businesses WHERE status='pending'")
        stats["pending_businesses"] = c.fetchone()["n"]
        return stats
