# -*- coding: utf-8 -*-
"""نمونه‌ی مشترک Jinja2Templates به همراه فیلترهای کمکی فارسی."""

import os
import datetime

from fastapi.templating import Jinja2Templates

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

_FA_DIGITS = "۰۱۲۳۴۵۶۷۸۹"


def to_fa_digits(value):
    s = str(value)
    return "".join(_FA_DIGITS[int(ch)] if ch.isdigit() else ch for ch in s)


def fa_number(value):
    try:
        return to_fa_digits(f"{int(value):,}")
    except (ValueError, TypeError):
        return to_fa_digits(value)


def fa_date(value):
    if not value:
        return ""
    try:
        dt = datetime.datetime.fromisoformat(value)
        return to_fa_digits(dt.strftime("%Y/%m/%d"))
    except (ValueError, TypeError):
        return to_fa_digits(value)


templates.env.filters["fa_number"] = fa_number
templates.env.filters["fa_date"] = fa_date
templates.env.filters["fa_digits"] = to_fa_digits


def _site_settings():
    """تنظیمات سایت (لینک کانال‌ها و ...) را برای استفاده در هر صفحه‌ای (مثلاً فوتر) برمی‌گرداند."""
    from web import db_web as db  # ایمپورت تنبل برای جلوگیری از حلقه‌ی ایمپورت
    return db.get_all_settings()


templates.env.globals["site_settings"] = _site_settings
