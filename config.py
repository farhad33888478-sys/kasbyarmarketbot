# -*- coding: utf-8 -*-

"""
تنظیمات اصلی kasbyarmarket
شامل تنظیمات ربات تلگرام/بله و همچنین پنل وب

توکن‌ها و اطلاعات حساس از فایل .env خوانده می‌شوند.
اگر فایل .env وجود نداشته باشد، مقادیر پیش‌فرض پایین استفاده می‌شود
تا ربات فعلی از کار نیفتد؛ اما برای امنیت، حتماً از .env استفاده کن.
"""

import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # اگر پکیج python-dotenv نصب نشده باشد، از متغیرهای محیطی سیستم استفاده می‌شود
    pass


def _env(key, default=""):
    return os.getenv(key, default)


def _env_list_int(key, default):
    raw = os.getenv(key)
    if not raw:
        return default
    return [int(x.strip()) for x in raw.split(",") if x.strip()]


# ===============================
# Telegram Bot
# ===============================

TELEGRAM_BOT_TOKEN = _env("TELEGRAM_BOT_TOKEN", "")

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

TELEGRAM_FILE_API_URL = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}"


# ===============================
# Admin
# ===============================

ADMIN_IDS = _env_list_int("ADMIN_IDS", [5107651828])

ADMIN_REVIEW_CHAT_ID = int(_env("ADMIN_REVIEW_CHAT_ID", "5107651828"))


# ===============================
# Channels
# ===============================

PUBLIC_CHANNEL_ID = _env("PUBLIC_CHANNEL_ID", "@kasbyarmarket")

POSTER_CHANNEL_ID = _env("POSTER_CHANNEL_ID", "@kasbyarmarket")


# ===============================
# Trial / Subscription
# ===============================

FREE_TRIAL_DAYS = 30

REMINDER_DAYS_BEFORE_EXPIRY = 3


PLANS = [

    {
        "id": "p1",
        "title": "یک ماهه",
        "days": 30,
        "price": 150000
    },

    {
        "id": "p3",
        "title": "سه ماهه",
        "days": 90,
        "price": 400000
    },

    {
        "id": "p6",
        "title": "شش ماهه",
        "days": 180,
        "price": 700000
    },

    {
        "id": "p12",
        "title": "یک ساله",
        "days": 365,
        "price": 1200000
    }

]


# ===============================
# Payment
# ===============================

CARD_NUMBER = "6219-8618-6200-6748"

CARD_OWNER = "سیدفرهاد قاسمی کناری"


# ===============================
# Categories
# ===============================

CATEGORIES = [

    "مشاور املاک",
    "فروشگاه پوشاک",
    "مواد غذایی",
    "خدمات فنی",
    "آرایشی و بهداشتی",
    "دیجیتال و موبایل",
    "خانه و آشپزخانه",
    "کودک و اسباب بازی",
    "سایر"

]


# ===============================
# Database
# ===============================

DB_PATH = _env("DB_PATH", "kasbyarmarket.db")


# ===============================
# Polling
# ===============================

POLL_TIMEOUT = 10  # چون تلگرام و بله به‌نوبت (round-robin) پول می‌شوند، مقدار کوچک‌تر پاسخ‌گویی رو بهتر می‌کنه


# ===============================
# Scheduler
# ===============================

EXPIRY_CHECK_INTERVAL_SECONDS = 6 * 60 * 60


# ===============================
# Bale / Eitaa
# ===============================

BALE_ENABLED = True

EITAA_ENABLED = False

BALE_TOKEN = _env("BALE_TOKEN", "")
BALE_API_URL = "https://tapi.bale.ai/bot"
BALE_CHANNEL_ID = _env("BALE_CHANNEL_ID", "@kasbyarmarket")

# ===============================
# Psiphon Proxy
# ===============================

PROXY = {
    "http": "socks5h://127.0.0.1:10808",
    "https": "socks5h://127.0.0.1:10808"
}

# Telegram crosspost
TELEGRAM_CHANNEL_ID = _env("TELEGRAM_CHANNEL_ID", "@kasbyarmarket")
TELEGRAM_POSTER_CHANNEL_ID = _env("TELEGRAM_POSTER_CHANNEL_ID", "@kasbyarmarket")

# Eitaa
EITAA_TOKEN = _env("EITAA_TOKEN", "")
EITAA_API_URL = "https://eitaayar.ir/api"
EITAA_CHANNEL_ID = _env("EITAA_CHANNEL_ID", "")
EITAA_POSTER_CHANNEL_ID = _env("EITAA_POSTER_CHANNEL_ID", "")


# ===============================
# Web Panel
# ===============================

WEB_SECRET_KEY = _env("WEB_SECRET_KEY", "insecure-dev-key-change-me")

ADMIN_WEB_USERNAME = _env("ADMIN_WEB_USERNAME", "admin")
ADMIN_WEB_PASSWORD = _env("ADMIN_WEB_PASSWORD", "admin")

WEB_HOST = _env("WEB_HOST", "127.0.0.1")
WEB_PORT = int(_env("WEB_PORT", "8000"))

SITE_NAME = "کسب‌یار مارکت"
