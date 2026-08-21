# -*- coding: utf-8 -*-

"""
اجرای اصلی kasbyarmarketbot
نسخه‌ی دوپلتفرمی: هم‌زمان تلگرام و بله را پول می‌کند.
ثبت کسب‌وکار از هر دو پلتفرم در همان دیتابیس مشترک ذخیره می‌شود
و بلافاصله در وب‌سایت هم قابل مشاهده است (پس از تایید ادمین).
"""

import time

import database as db
import telegram_api as api
import bale_api
import bot
import scheduler


def main():

    print("در حال راه‌اندازی ربات kasbyarmarket ...")

    # ساخت دیتابیس
    db.init_db()

    # اجرای بررسی اشتراک‌ها
    scheduler.start_scheduler_thread()

    bale_active = bale_api.is_enabled()
    if bale_active:
        print("ربات با موفقیت اجرا شد (تلگرام + بله). در انتظار پیام‌ها ...")
    else:
        print("ربات با موفقیت اجرا شد (فقط تلگرام - توکن بله تنظیم نشده). در انتظار پیام‌ها ...")

    tg_offset = None
    bale_offset = None

    while True:

        # ---------------- تلگرام ----------------
        try:
            bot.set_platform("telegram")
            result = api.get_updates(offset=tg_offset)

            if not result.get("ok"):
                print("خطا در دریافت آپدیت‌های تلگرام:", result)
            else:
                updates = result.get("result", [])
                if updates:
                    print("TELEGRAM UPDATES:", len(updates))
                for update in updates:
                    tg_offset = update["update_id"] + 1
                    try:
                        process_update(update, platform="telegram")
                    except Exception as e:
                        print("[main] خطا در پردازش آپدیت تلگرام:", e)

        except Exception as e:
            print("[MAIN ERROR - telegram]", e)
            time.sleep(5)

        # ---------------- بله ----------------
        if bale_active:
            try:
                bot.set_platform("bale")
                result = bale_api.get_updates(offset=bale_offset)

                if not result.get("ok"):
                    print("خطا در دریافت آپدیت‌های بله:", result)
                else:
                    updates = result.get("result", [])
                    if updates:
                        print("BALE UPDATES:", len(updates))
                    for update in updates:
                        bale_offset = update["update_id"] + 1
                        try:
                            process_update(update, platform="bale")
                        except Exception as e:
                            print("[main] خطا در پردازش آپدیت بله:", e)

            except Exception as e:
                print("[MAIN ERROR - bale]", e)
                time.sleep(5)


def process_update(update, platform="telegram"):

    bot.set_platform(platform)

    # پیام معمولی
    if "message" in update:
        message = update["message"]
        print("MESSAGE:", message)

        # بررسی رسید پرداخت
        try:
            if bot.handle_possible_receipt(message):
                return
        except Exception:
            pass

        bot.handle_message(message)

    # دکمه‌های inline
    elif "callback_query" in update:
        bot.handle_callback_query(update["callback_query"])


if __name__ == "__main__":
    main()
