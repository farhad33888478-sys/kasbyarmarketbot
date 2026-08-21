# -*- coding: utf-8 -*-
"""
وظیفه‌ی پس‌زمینه‌ای که به‌صورت دوره‌ای اجرا می‌شود و:
  - به کاربرانی که اشتراکشان رو به اتمام است یادآوری پرداخت می‌فرستد
  - کسب‌وکارهایی که اشتراکشان تمام شده را به‌عنوان "expired" علامت می‌زند
    و آگهی آن‌ها را از کانال حذف می‌کند
"""

import time
import datetime
import threading

import config
import database as db
import telegram_api as api
import keyboards as kb

_reminded_ids = set()  # جلوگیری از ارسال یادآوری تکراری در یک اجرا


def check_expirations():
    now = datetime.datetime.utcnow()
    businesses = db.list_approved_businesses()

    for biz in businesses:
        paid_until_str = biz.get("paid_until")
        if not paid_until_str:
            continue
        try:
            paid_until = datetime.datetime.fromisoformat(paid_until_str)
        except ValueError:
            continue

        days_left = (paid_until - now).days

        # یادآوری چند روز قبل از انقضا
        if 0 <= days_left <= config.REMINDER_DAYS_BEFORE_EXPIRY:
            reminder_key = f"{biz['id']}-{paid_until_str}"
            if reminder_key not in _reminded_ids:
                _reminded_ids.add(reminder_key)
                api.send_message(
                    biz["user_id"],
                    f"⏰ اشتراک کسب‌وکار «{biz['name']}» شما تا {days_left} روز دیگر به پایان می‌رسد.\n"
                    "برای جلوگیری از حذف آگهی از کانال، همین حالا تمدید کنید.",
                    reply_markup=kb.my_business_action_keyboard(biz["id"], "approved"),
                )

        # اگر تاریخ اشتراک گذشته باشد -> منقضی کن و از کانال حذف کن
        if paid_until <= now:
            if biz.get("channel_message_id"):
                api.delete_message(config.PUBLIC_CHANNEL_ID, biz["channel_message_id"])
                db.set_channel_message_id(biz["id"], None)
            db.set_business_expired(biz["id"])
            api.send_message(
                biz["user_id"],
                f"⌛️ اشتراک کسب‌وکار «{biz['name']}» شما به پایان رسید و آگهی از کانال حذف شد.\n"
                "برای انتشار مجدد، اشتراک خود را تمدید کنید.",
                reply_markup=kb.my_business_action_keyboard(biz["id"], "expired"),
            )


def run_scheduler_loop():
    while True:
        try:
            check_expirations()
        except Exception as e:
            print(f"[scheduler] خطا: {e}")
        time.sleep(config.EXPIRY_CHECK_INTERVAL_SECONDS)


def start_scheduler_thread():
    t = threading.Thread(target=run_scheduler_loop, daemon=True)
    t.start()
    return t
