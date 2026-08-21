# -*- coding: utf-8 -*-
"""
توابع امنیتی پنل وب: هش کردن و بررسی رمز عبور.

از pbkdf2_hmac کتابخانه استاندارد پایتون استفاده می‌کنیم تا نیازی به
نصب پکیج‌های سنگین اضافی (مثل bcrypt که روی ویندوز گاهی نصبش مشکل دارد) نباشد.
"""

import hashlib
import hmac
import os
import secrets

_ITERATIONS = 260_000


def hash_password(password: str) -> str:
    """رمز را هش می‌کند و به‌صورت 'salt$hash' برمی‌گرداند."""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), _ITERATIONS
    )
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """رمز واردشده را با هش ذخیره‌شده مقایسه می‌کند."""
    try:
        salt, hash_hex = stored.split("$", 1)
    except (ValueError, AttributeError):
        return False

    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), _ITERATIONS
    )
    return hmac.compare_digest(digest.hex(), hash_hex)


def normalize_phone(phone: str) -> str:
    """شماره موبایل را به شکل استاندارد 09xxxxxxxxx در می‌آورد."""
    phone = (phone or "").strip().replace(" ", "").replace("-", "")
    phone = phone.replace("+98", "0").replace("0098", "0")
    if phone.startswith("98"):
        phone = "0" + phone[2:]
    if phone and not phone.startswith("0"):
        phone = "0" + phone
    return phone


def is_valid_iran_phone(phone: str) -> bool:
    phone = normalize_phone(phone)
    return len(phone) == 11 and phone.startswith("09") and phone.isdigit()
