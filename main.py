# -*- coding: utf-8 -*-

"""
kasbyarmarketbot
ربات همزمان تلگرام و بله
مناسب برای اجرا روی Render
"""

import os
import time
import threading

import uvicorn
from fastapi import FastAPI

import database as db
import telegram_api as api
import bale_api
import bot
import scheduler


# =========================================================
# Render Web Server
# =========================================================

app = FastAPI()


@app.get("/")
def health():
    return {
        "status": "ok",
        "bot": "kasbyarmarketbot"
    }


@app.get("/health")
def health_check():
    return {
        "status": "running"
    }


def start_web_server():
    """
    Render برای Web Service نیاز دارد که برنامه
    روی PORT مشخص‌شده گوش بدهد.
    """

    port = int(os.environ.get("PORT", "10000"))

    print(f"Web server starting on 0.0.0.0:{port}")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )


# =========================================================
# Main Bot
# =========================================================

def main():

    # -----------------------------------------------------
    # اجرای Web Server در Thread جدا
    # -----------------------------------------------------

    web_thread = threading.Thread(
        target=start_web_server,
        daemon=True
    )

    web_thread.start()

    print("==============================================")
    print("kasbyarmarketbot STARTING")
    print("==============================================")

    # -----------------------------------------------------
    # Database
    # -----------------------------------------------------

    print("Initializing database...")

    db.init_db()

    # -----------------------------------------------------
    # Scheduler
    # -----------------------------------------------------

    print("Starting scheduler...")

    scheduler.start_scheduler_thread()

    # -----------------------------------------------------
    # Bale
    # -----------------------------------------------------

    bale_active = bale_api.is_enabled()

    if bale_active:

        print(
            "Bot started successfully "
            "(Telegram + Bale)"
        )

    else:

        print(
            "Bot started successfully "
            "(Telegram only)"
        )

    # -----------------------------------------------------
    # Update offsets
    # -----------------------------------------------------

    tg_offset = None
    bale_offset = None

    print("Waiting for messages...")

    # =====================================================
    # Main Loop
    # =====================================================

    while True:

        # =================================================
        # Telegram
        # =================================================

        try:

            bot.set_platform("telegram")

            result = api.get_updates(
                offset=tg_offset
            )

            if not result.get("ok"):

                print(
                    "[TELEGRAM ERROR]",
                    result
                )

            else:

                updates = result.get(
                    "result",
                    []
                )

                if updates:

                    print(
                        "TELEGRAM UPDATES:",
                        len(updates)
                    )

                for update in updates:

                    tg_offset = (
                        update["update_id"] + 1
                    )

                    try:

                        process_update(
                            update,
                            platform="telegram"
                        )

                    except Exception as e:

                        print(
                            "[TELEGRAM UPDATE ERROR]",
                            e
                        )

        except Exception as e:

            print(
                "[MAIN ERROR - TELEGRAM]",
                e
            )

            time.sleep(5)

        # =================================================
        # Bale
        # =================================================

        if bale_active:

            try:

                bot.set_platform("bale")

                result = bale_api.get_updates(
                    offset=bale_offset
                )

                if not result.get("ok"):

                    print(
                        "[BALE ERROR]",
                        result
                    )

                else:

                    updates = result.get(
                        "result",
                        []
                    )

                    if updates:

                        print(
                            "BALE UPDATES:",
                            len(updates)
                        )

                    for update in updates:

                        bale_offset = (
                            update["update_id"] + 1
                        )

                        try:

                            process_update(
                                update,
                                platform="bale"
                            )

                        except Exception as e:

                            print(
                                "[BALE UPDATE ERROR]",
                                e
                            )

            except Exception as e:

                print(
                    "[MAIN ERROR - BALE]",
                    e
                )

                time.sleep(5)


# =========================================================
# Process Update
# =========================================================

def process_update(
    update,
    platform="telegram"
):

    bot.set_platform(platform)

    # -----------------------------------------------------
    # Normal Message
    # -----------------------------------------------------

    if "message" in update:

        message = update["message"]

        print(
            "MESSAGE:",
            message
        )

        # -------------------------------------------------
        # Receipt
        # -------------------------------------------------

        try:

            if bot.handle_possible_receipt(
                message
            ):
                return

        except Exception:

            pass

        # -------------------------------------------------
        # Normal Bot Message
        # -------------------------------------------------

        bot.handle_message(
            message
        )

    # -----------------------------------------------------
    # Callback Query
    # -----------------------------------------------------

    elif "callback_query" in update:

        bot.handle_callback_query(
            update["callback_query"]
        )


# =========================================================
# Start
# =========================================================

if __name__ == "__main__":

    main()