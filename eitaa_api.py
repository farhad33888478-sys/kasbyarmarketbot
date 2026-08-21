# -*- coding: utf-8 -*-
"""
لایه‌ی ارتباط با API ایتا (از طریق eitaayar.ir) - فقط برای کراس‌پست خودکار.
توجه مهم: API ایتایار یک‌طرفه است (فقط ارسال پیام/فایل)؛ امکان دریافت پیام از
کاربر (getUpdates/webhook) در آن وجود ندارد، پس ربات تعاملی روی ایتا ساخته نمی‌شود -
این ماژول صرفاً آگهی‌های تاییدشده در بله را به کانال ایتا ارسال می‌کند.
مستندات: https://eitaayar.ir
"""

import requests
import config


def is_enabled():
    """اگر توکن ایتایار تنظیم نشده باشد، کراس‌پست غیرفعال است."""
    return bool(config.EITAA_TOKEN)


def _post(method, payload=None, files=None):
    if not is_enabled():
        return {"ok": False, "error": "EITAA_TOKEN تنظیم نشده است"}
    url = f"{config.EITAA_API_URL}/{config.EITAA_TOKEN}/{method}"
    try:
        resp = requests.post(url, data=payload, files=files, timeout=40)
        return resp.json()
    except Exception as e:
        print(f"[eitaa_api] خطا در فراخوانی {method}: {e}")
        return {"ok": False, "error": str(e)}


def send_message(chat_id, text):
    if not is_enabled():
        return None
    return _post("sendMessage", {"chat_id": chat_id, "text": text})


def send_photo_bytes(chat_id, photo_bytes, filename="photo.jpg", caption=None, title=None):
    """
    ارسال عکس/فایل با آپلود مستقیم بایت‌ها (نه file_id).
    چون file_id بله روی ایتا معتبر نیست، عکس باید از بله دانلود و اینجا دوباره
    آپلود شود. API ایتایار از متد sendFile برای این کار استفاده می‌کند.
    """
    if not is_enabled():
        return None
    payload = {"chat_id": chat_id}
    if caption:
        payload["caption"] = caption
    if title:
        payload["title"] = title
    files = {"file": (filename, photo_bytes)}
    return _post("sendFile", payload, files=files)
