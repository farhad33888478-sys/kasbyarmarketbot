# -*- coding: utf-8 -*-
"""
حل مشکل نمایش عکس در وب.

عکس‌های ثبت‌شده از طریق ربات به‌صورت photo_file_id تلگرام ذخیره می‌شوند —
این یک شناسه است، نه لینک، و مستقیماً در مرورگر قابل نمایش نیست.
این ماژول عکس را یک‌بار از تلگرام دانلود می‌کند، در web/static/cache/ ذخیره
می‌کند و از آن به بعد همان فایل کش‌شده را برمی‌گرداند (بدون دانلود مجدد).

عکس‌هایی که مستقیم از طریق وب آپلود شده‌اند (مسیر /static/uploads/...) دست‌نخورده
باقی می‌مانند و اصلاً نیازی به این پردازش ندارند.
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import telegram_api
import bale_api

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

_apis = {"telegram": telegram_api, "bale": bale_api}


def resolve_photo_url(photo_ref, cache_key, platform="telegram"):
    """
    photo_ref: مقدار ستون photo_file_id (می‌تواند None، مسیر آپلود وب، یا file_id تلگرام/بله باشد)
    cache_key: یک کلید یکتا برای این عکس (مثلاً 'biz_12')
    platform: 'telegram' یا 'bale' — مشخص می‌کند عکس را از کدام پلتفرم دانلود کنیم

    خروجی: مسیر قابل‌نمایش در وب (مثلاً /static/uploads/x.jpg یا /static/cache/biz_12.jpg) یا None
    """
    if not photo_ref:
        return None

    # عکسی که از طریق فرم وب آپلود شده - همان مسیر معتبر است
    if photo_ref.startswith("/static") or photo_ref.startswith("http"):
        return photo_ref

    # از این به بعد فرض می‌کنیم photo_ref یک file_id تلگرام یا بله است
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        cached_path = os.path.join(CACHE_DIR, f"{cache_key}{ext}")
        if os.path.exists(cached_path):
            return f"/static/cache/{cache_key}{ext}"

    # هنوز کش نشده -> از پلتفرم درست دانلود کن
    api = _apis.get(platform, telegram_api)
    try:
        file_info = api.get_file(photo_ref)
        if not file_info.get("ok"):
            return None
        file_path = file_info["result"]["file_path"]
        data = api.download_file(file_path)
        if not data:
            return None
        ext = os.path.splitext(file_path)[1] or ".jpg"
        filename = f"{cache_key}{ext}"
        with open(os.path.join(CACHE_DIR, filename), "wb") as f:
            f.write(data)
        return f"/static/cache/{filename}"
    except Exception as e:
        print(f"[media] خطا در دریافت عکس از {platform} برای {cache_key}: {e}")
        return None


def attach_photo_url(biz):
    """یک دیکشنری کسب‌وکار را با کلید photo_url غنی می‌کند."""
    if biz is None:
        return biz
    platform = biz.get("platform") or "telegram"
    biz["photo_url"] = resolve_photo_url(biz.get("photo_file_id"), f"biz_{biz['id']}", platform)
    return biz


def attach_photo_urls(businesses):
    return [attach_photo_url(b) for b in businesses]
