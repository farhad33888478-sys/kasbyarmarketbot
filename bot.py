# -*- coding: utf-8 -*-
"""
منطق اصلی ربات kasbyarmarket
پردازش پیام‌ها، مکالمه‌ی چندمرحله‌ای ثبت کسب‌وکار، و callback query ها
"""

import datetime
import config
import database as db
import telegram_api as api
import telegram_api
import eitaa_api
import bale_api
import keyboards as kb

# حالت مکالمه‌ی هر کاربر در حافظه نگهداری می‌شود
# ساختار: { user_id: {"step": "...", "data": {...}} }
user_states = {}

# ---------------------------------------------------------------------
# پشتیبانی چندپلتفرمی (تلگرام + بله)
# ---------------------------------------------------------------------
# نکته‌ی مهم: آیدی کاربرهای تلگرام و بله دو فضای شماره‌گذاری جدا هستند و
# ممکن است تصادفاً یک عدد یکسان داشته باشند. برای جلوگیری از تداخل،
# آیدی کاربرهای بله را به‌صورت داخلی منفی ذخیره می‌کنیم (مثلاً 123 -> -123).
# «chat_id» دست‌نخورده باقی می‌ماند چون برای ارسال پیام واقعی لازم است.

_apis = {"telegram": telegram_api, "bale": bale_api}
current_platform = "telegram"


def set_platform(platform):
    """قبل از پردازش هر آپدیت صدا زده می‌شود تا مشخص کند پیام از کجا آمده."""
    global api, current_platform
    current_platform = platform
    api = _apis.get(platform, telegram_api)


def platform_user_id(raw_id):
    """آیدی خام پلتفرم را به آیدی داخلی (فضای غیرتداخلی) تبدیل می‌کند."""
    if raw_id is None:
        return None
    if current_platform == "bale":
        return -abs(raw_id)
    return raw_id

HELP_TEXT = (
    "🛍 به ربات kasbyarmarket خوش آمدید!\n\n"
    "این ربات به شما کمک می‌کند کسب‌وکار یا فروشگاه خود را در کانال ما معرفی کنید.\n\n"
    "روند کار:\n"
    "۱) اطلاعات کسب‌وکار خود را از طریق گزینه‌ی «ثبت کسب‌وکار جدید» ارسال کنید.\n"
    "۲) درخواست شما توسط مدیر بررسی و تایید می‌شود.\n"
    "۳) پس از تایید، آگهی شما به‌صورت رایگان برای ۳۰ روز در کانال منتشر می‌شود.\n"
    "۴) بعد از پایان دوره رایگان، می‌توانید با انتخاب یکی از پلن‌های اشتراک، آگهی خود را تمدید کنید.\n\n"
    "برای مشاهده وضعیت کسب‌وکارهای خود از «کسب‌وکارهای من» استفاده کنید."
)


def reset_state(user_id):
    user_states.pop(user_id, None)


def is_admin(user_id):
    return user_id in config.ADMIN_IDS


# ---------------------------------------------------------------------
# پردازش پیام‌های متنی/عکس معمولی
# ---------------------------------------------------------------------
def handle_message(message):
    chat = message.get("chat", {})
    chat_id = chat.get("id")

    # جلوگیری از پاسخ دادن به پیام‌های کانال بله
    if message.get("sender_chat"):
        return

    from_user = message.get("from", {})
    user_id = platform_user_id(from_user.get("id"))
    text = message.get("text", "")
    photo = message.get("photo")

    if user_id is None or chat_id is None:
        return

    db.upsert_user(user_id, from_user.get("first_name", ""), from_user.get("username", ""), platform=current_platform)

    state = user_states.get(user_id)

    # لغو در هر مرحله
    if text == "❌ انصراف":
        reset_state(user_id)
        api.send_message(chat_id, "عملیات لغو شد.", reply_markup=kb.main_menu_keyboard())
        return

    # ---------- دستورات اصلی ----------
    if text == "/start":
        reset_state(user_id)
        api.send_message(chat_id, HELP_TEXT, reply_markup=kb.main_menu_keyboard())
        return

    if text == "ℹ️ راهنما":
        api.send_message(chat_id, HELP_TEXT, reply_markup=kb.main_menu_keyboard())
        return

    if "ثبت کسب" in text:
        user_states[user_id] = {"step": "biz_name", "data": {}}
        api.send_message(chat_id, "لطفاً نام کسب‌وکار/فروشگاه خود را وارد کنید:",
                          reply_markup=kb.cancel_keyboard())
        return

    if text == "📋 کسب‌وکارهای من":
        show_my_businesses(chat_id, user_id)
        return

    # ---------- مسیر مستقل پوستر تبلیغاتی ----------
    if text == "📢 ثبت پوستر تبلیغاتی":
        user_states[user_id] = {"step": "poster_photo", "data": {}}
        api.send_message(chat_id, "لطفاً تصویر پوستر تبلیغاتی خود را ارسال کنید:",
                          reply_markup=kb.cancel_keyboard())
        return

    if text == "🖼 پوسترهای من":
        show_my_posters(chat_id, user_id)
        return

    # دستورات مدیریتی
    if text.startswith("/pending") and is_admin(user_id):
        show_pending_list(chat_id)
        return

    if text.startswith("/pending_posters") and is_admin(user_id):
        show_pending_posters(chat_id)
        return

    # ---------- ادامه‌ی مکالمه ثبت کسب‌وکار ----------
    if state:
        step = state["step"]
        data = state["data"]

        if step == "biz_name":
            if not text:
                api.send_message(chat_id, "لطفاً نام کسب‌وکار را به‌صورت متن ارسال کنید.")
                return
            data["name"] = text
            state["step"] = "biz_category"
            api.send_message(chat_id, "دسته‌بندی کسب‌وکار خود را انتخاب یا تایپ کنید:",
                              reply_markup=kb.categories_keyboard())
            return

        if step == "biz_category":
            if not text:
                api.send_message(chat_id, "لطفاً دسته‌بندی را وارد کنید.")
                return
            data["category"] = text
            state["step"] = "biz_desc"
            api.send_message(chat_id, "توضیح کوتاهی درباره‌ی کسب‌وکار/محصولات خود بنویسید:",
                              reply_markup=kb.cancel_keyboard())
            return

        if step == "biz_desc":
            if not text:
                api.send_message(chat_id, "لطفاً توضیحات را به‌صورت متن ارسال کنید.")
                return
            data["description"] = text
            state["step"] = "biz_phone"
            api.send_message(chat_id, "شماره تماس کسب‌وکار را وارد کنید (مثال: 09121234567):",
                              reply_markup=kb.cancel_keyboard())
            return

        if step == "biz_phone":
            if not text:
                api.send_message(chat_id, "لطفاً شماره تماس را وارد کنید.")
                return
            data["phone"] = text
            state["step"] = "biz_address"
            api.send_message(chat_id, "آدرس یا لوکیشن کسب‌وکار خود را وارد کنید (در صورت نداشتن، بنویسید «ندارد»):",
                              reply_markup=kb.cancel_keyboard())
            return

        if step == "biz_address":
            if not text:
                api.send_message(chat_id, "لطفاً آدرس را وارد کنید یا بنویسید «ندارد».")
                return
            data["address"] = text
            state["step"] = "biz_photo"
            api.send_message(chat_id, "یک عکس نمونه از کسب‌وکار/محصول خود ارسال کنید (یا رد کنید):",
                              reply_markup=kb.skip_or_cancel_keyboard())
            return

        if step == "biz_photo":
            if photo:
                # بزرگترین سایز عکس آخرین آیتم آرایه است
                data["photo_file_id"] = photo[-1]["file_id"]
                finalize_business_preview(chat_id, user_id, state)
                return
            if text == "⏭ رد کردن (بدون عکس)":
                data["photo_file_id"] = None
                finalize_business_preview(chat_id, user_id, state)
                return
            api.send_message(chat_id, "لطفاً یک عکس ارسال کنید یا گزینه «رد کردن» را بزنید.")
            return

        # ---------- مراحل مستقل ثبت پوستر تبلیغاتی ----------
        if step == "poster_photo":
            if photo:
                data["photo_file_id"] = photo[-1]["file_id"]
                state["step"] = "poster_caption"
                api.send_message(chat_id, "یک توضیح کوتاه برای پوستر بنویسید (یا بنویسید «ندارد»):",
                                  reply_markup=kb.cancel_keyboard())
                return
            api.send_message(chat_id, "لطفاً تصویر پوستر را ارسال کنید.")
            return

        if step == "poster_caption":
            if not text:
                api.send_message(chat_id, "لطفاً توضیح را به‌صورت متن ارسال کنید یا بنویسید «ندارد».")
                return
            data["caption"] = "" if text == "ندارد" else text
            state["step"] = "poster_confirm"
            preview_caption = data["caption"] or "(بدون توضیح)"
            api.send_photo(
                chat_id, data["photo_file_id"],
                caption=f"📢 پیش‌نمایش پوستر تبلیغاتی:\n\n{preview_caption}\n\nدر صورت تایید، برای بررسی مدیر ارسال می‌شود.",
                reply_markup=kb.confirm_poster_keyboard(),
            )
            return

    # اگر هیچ‌کدام از موارد بالا match نشد
    api.send_message(chat_id, "برای شروع از دستور /start استفاده کنید.", reply_markup=kb.main_menu_keyboard())


def finalize_business_preview(chat_id, user_id, state):
    data = state["data"]
    preview = (
        "📋 پیش‌نمایش آگهی شما:\n\n"
        f"🏪 نام: {data['name']}\n"
        f"🏷 دسته‌بندی: {data['category']}\n"
        f"📝 توضیحات: {data['description']}\n"
        f"📞 تماس: {data['phone']}\n"
        f"📍 آدرس: {data['address']}\n\n"
        "در صورت تایید، درخواست شما برای بررسی مدیر ارسال می‌شود."
    )
    state["step"] = "biz_confirm"
    temp_key = str(user_id)
    if data.get("photo_file_id"):
        api.send_photo(chat_id, data["photo_file_id"], caption=preview,
                        reply_markup=kb.confirm_business_keyboard(temp_key))
    else:
        api.send_message(chat_id, preview, reply_markup=kb.confirm_business_keyboard(temp_key))


def show_my_businesses(chat_id, user_id):
    businesses = db.list_businesses_by_user(user_id)
    if not businesses:
        api.send_message(chat_id, "شما هنوز هیچ کسب‌وکاری ثبت نکرده‌اید.", reply_markup=kb.main_menu_keyboard())
        return

    status_labels = {
        "pending": "⏳ در انتظار بررسی",
        "approved": "✅ فعال",
        "rejected": "🚫 رد شده",
        "expired": "⌛️ منقضی‌شده",
    }

    for biz in businesses:
        status = biz["status"]
        lines = [
            f"🏪 {biz['name']}",
            f"وضعیت: {status_labels.get(status, status)}",
        ]
        if status == "approved" and biz.get("paid_until"):
            lines.append(f"اعتبار تا: {format_date(biz['paid_until'])}")
        if status == "rejected" and biz.get("reject_reason"):
            lines.append(f"دلیل رد: {biz['reject_reason']}")
        if status == "expired":
            lines.append("اشتراک شما به پایان رسیده است. برای تمدید از دکمه زیر استفاده کنید.")

        markup = kb.my_business_action_keyboard(biz["id"], status)
        api.send_message(chat_id, "\n".join(lines), reply_markup=markup)


def show_pending_list(chat_id):
    pending = db.list_pending_businesses()
    if not pending:
        api.send_message(chat_id, "درخواست در انتظار بررسی وجود ندارد.")
        return
    for biz in pending:
        send_business_to_admin(biz)


def format_date(iso_str):
    try:
        d = datetime.datetime.fromisoformat(iso_str)
        return d.strftime("%Y-%m-%d")
    except Exception:
        return iso_str


def notify_owner(internal_user_id, text, reply_markup=None):
    """
    پیام را به صاحب اصلیِ کسب‌وکار/پوستر/پرداخت می‌رساند — حتی اگر این تابع
    از داخل یک اکشن ادمین (که همیشه از تلگرام است) صدا زده شده باشد.
    آیدی داخلی منفی یعنی کاربر بله است؛ مثبت یعنی کاربر تلگرام است.
    """
    if internal_user_id is None:
        return
    try:
        if internal_user_id < 0:
            bale_api.send_message(abs(internal_user_id), text, reply_markup=reply_markup)
        else:
            telegram_api.send_message(internal_user_id, text, reply_markup=reply_markup)
    except Exception as e:
        print(f"[notify_owner] خطا در اطلاع‌رسانی به کاربر {internal_user_id}: {e}")


def _relay_photo_for_telegram(photo_file_id, source_platform):
    """
    اگر عکس از بله آمده باشد، بایت‌هایش را دانلود می‌کند تا بشود در تلگرام
    (چت ادمین) نمایش داد. اگر خودش تلگرامی باشد، همان file_id برگردانده می‌شود.
    خروجی: ("file_id", value) یا ("bytes", value) یا (None, None) در صورت شکست.
    """
    if source_platform == "bale":
        try:
            file_info = bale_api.get_file(photo_file_id)
            file_path = file_info.get("result", {}).get("file_path") if file_info.get("ok") else None
            data = bale_api.download_file(file_path) if file_path else None
            return ("bytes", data) if data else (None, None)
        except Exception as e:
            print(f"[relay] خطا در دریافت عکس از بله: {e}")
            return (None, None)
    return ("file_id", photo_file_id)


def send_business_to_admin(biz):
    """اطلاع‌رسانی درخواست جدید به ادمین — همیشه از طریق تلگرام (چون ادمین آنجا بررسی می‌کند)،
    مهم نیست کاربر از تلگرام ثبت کرده باشد یا بله."""
    text = (
        "🆕 درخواست ثبت کسب‌وکار جدید\n\n"
        f"شناسه: #{biz['id']}\n"
        f"🏪 نام: {biz['name']}\n"
        f"🏷 دسته‌بندی: {biz['category']}\n"
        f"📝 توضیحات: {biz['description']}\n"
        f"📞 تماس: {biz['phone']}\n"
        f"📍 آدرس: {biz['address']}\n"
        f"منبع ثبت: {'بله' if biz.get('platform') == 'bale' else 'تلگرام'}\n"
        f"کاربر: {biz['user_id']}"
    )
    photo_file_id = biz.get("photo_file_id")
    markup = kb.admin_review_keyboard(biz["id"])

    if photo_file_id:
        kind, payload = _relay_photo_for_telegram(photo_file_id, biz.get("platform") or "telegram")
        if kind == "file_id":
            telegram_api.send_photo(config.ADMIN_REVIEW_CHAT_ID, payload, caption=text, reply_markup=markup)
            return
        if kind == "bytes":
            telegram_api.send_photo_bytes(config.ADMIN_REVIEW_CHAT_ID, payload,
                                           filename=f"biz_{biz['id']}.jpg", caption=text, reply_markup=markup)
            return
    telegram_api.send_message(config.ADMIN_REVIEW_CHAT_ID, text, reply_markup=markup)


def show_my_posters(chat_id, user_id):
    posters = db.list_posters_by_user(user_id)
    if not posters:
        api.send_message(chat_id, "شما هنوز هیچ پوستر تبلیغاتی ثبت نکرده‌اید.", reply_markup=kb.main_menu_keyboard())
        return
    status_labels = {"pending": "⏳ در انتظار بررسی", "approved": "✅ منتشرشده", "rejected": "🚫 رد شده"}
    for p in posters:
        lines = [f"📢 پوستر #{p['id']}", f"وضعیت: {status_labels.get(p['status'], p['status'])}"]
        if p["status"] == "rejected" and p.get("reject_reason"):
            lines.append(f"دلیل رد: {p['reject_reason']}")
        api.send_message(chat_id, "\n".join(lines))


def show_pending_posters(chat_id):
    pending = db.list_pending_posters()
    if not pending:
        api.send_message(chat_id, "پوستر در انتظار بررسی وجود ندارد.")
        return
    for p in pending:
        send_poster_to_admin(p)


def send_poster_to_admin(poster):
    caption = (
        "🆕 پوستر تبلیغاتی جدید (مستقل از کسب‌وکارها)\n\n"
        f"شناسه: #{poster['id']}\n"
        f"توضیح: {poster['caption'] or '(بدون توضیح)'}\n"
        f"منبع ثبت: {'بله' if poster.get('platform') == 'bale' else 'تلگرام'}\n"
        f"کاربر: {poster['user_id']}"
    )
    markup = kb.admin_poster_review_keyboard(poster["id"])
    kind, payload = _relay_photo_for_telegram(poster["photo_file_id"], poster.get("platform") or "telegram")
    if kind == "file_id":
        telegram_api.send_photo(config.ADMIN_REVIEW_CHAT_ID, payload, caption=caption, reply_markup=markup)
    elif kind == "bytes":
        telegram_api.send_photo_bytes(config.ADMIN_REVIEW_CHAT_ID, payload,
                                       filename=f"poster_{poster['id']}.jpg", caption=caption, reply_markup=markup)
    else:
        telegram_api.send_message(config.ADMIN_REVIEW_CHAT_ID, caption, reply_markup=markup)


def publish_poster_to_channel(poster):
    result = api.send_photo(config.POSTER_CHANNEL_ID, poster["photo_file_id"], caption=poster["caption"] or None)
    if result.get("ok"):
        return result["result"]["message_id"]
    return None


def crosspost_business_to_telegram(biz):
    """کراس‌پست best-effort آگهی تاییدشده به کانال تلگرام. شکست آن ربات را متوقف نمی‌کند."""
    if not telegram_api.is_enabled():
        return
    text = (
        f"🏪 {biz['name']}\n"
        f"🏷 دسته‌بندی: {biz['category']}\n\n"
        f"{biz['description']}\n\n"
        f"📞 تماس: {biz['phone']}\n"
        f"📍 آدرس: {biz['address']}\n\n"
        "🔹 معرفی‌شده در ربات kasbyarmarket"
    )
    try:
        if biz.get("photo_file_id"):
            if biz.get("platform") == "bale":
                kind, payload = _relay_photo_for_telegram(biz["photo_file_id"], "bale")
                if kind == "bytes":
                    telegram_api.send_photo_bytes(config.TELEGRAM_CHANNEL_ID, payload,
                                                   filename=f"biz_{biz['id']}.jpg", caption=text)
                    return
            else:
                file_info = telegram_api.get_file(biz["photo_file_id"])
                file_path = file_info.get("result", {}).get("file_path") if file_info.get("ok") else None
                photo_bytes = telegram_api.download_file(file_path) if file_path else None
                if photo_bytes:
                    telegram_api.send_photo_bytes(config.TELEGRAM_CHANNEL_ID, photo_bytes,
                                                   filename=f"biz_{biz['id']}.jpg", caption=text)
                    return
        telegram_api.send_message(config.TELEGRAM_CHANNEL_ID, text)
        bale_api.send_message(config.BALE_CHANNEL_ID, text)
    except Exception as e:
        print(f"[crosspost] خطا در ارسال کسب‌وکار #{biz['id']} به تلگرام: {e}")


def crosspost_business_to_bale(biz):
    """ارسال آگهی تایید شده به بله (همراه با عکس، در صورت وجود)"""
    text = (
        f"🏪 {biz['name']}\n"
        f"🏷 دسته‌بندی: {biz['category']}\n\n"
        f"{biz['description']}\n\n"
        f"📞 تماس: {biz['phone']}\n"
        f"📍 آدرس: {biz['address']}\n\n"
        "🔹 معرفی‌شده در ربات kasbyarmarket"
    )

    try:
        if biz.get("photo_file_id"):
            if biz.get("platform") == "bale":
                # عکس همین الان روی بله است؛ مستقیم با همان file_id ارسال می‌شود
                bale_api.send_photo(config.BALE_CHANNEL_ID, biz["photo_file_id"], caption=text)
                return
            # عکس روی تلگرام آپلود شده؛ چون file_id تلگرام روی بله معتبر نیست،
            # باید بایت‌های عکس را از تلگرام دانلود و دوباره روی بله آپلود کنیم.
            file_info = telegram_api.get_file(biz["photo_file_id"])
            file_path = file_info.get("result", {}).get("file_path") if file_info.get("ok") else None
            photo_bytes = telegram_api.download_file(file_path) if file_path else None
            if photo_bytes:
                bale_api.send_photo_bytes(config.BALE_CHANNEL_ID, photo_bytes,
                                           filename=f"biz_{biz['id']}.jpg", caption=text)
                return
        bale_api.send_message(config.BALE_CHANNEL_ID, text)

    except Exception as e:
        print(f"[BALE ERROR] {e}")
def crosspost_poster_to_telegram(poster):
    """کراس‌پست best-effort پوستر تبلیغاتی تاییدشده به کانال تلگرام."""
    if not telegram_api.is_enabled():
        return
    try:
        photo_bytes = None
        if poster.get("platform") == "bale":
            kind, payload = _relay_photo_for_telegram(poster["photo_file_id"], "bale")
            if kind == "bytes":
                photo_bytes = payload
        else:
            file_info = telegram_api.get_file(poster["photo_file_id"])
            file_path = file_info.get("result", {}).get("file_path") if file_info.get("ok") else None
            photo_bytes = telegram_api.download_file(file_path) if file_path else None

        if photo_bytes:
            telegram_api.send_photo_bytes(config.TELEGRAM_POSTER_CHANNEL_ID, photo_bytes,
                                           filename=f"poster_{poster['id']}.jpg",
                                           caption=poster.get("caption") or None)
        elif poster.get("caption"):
            telegram_api.send_message(config.TELEGRAM_POSTER_CHANNEL_ID, poster["caption"])
    except Exception as e:
        print(f"[crosspost] خطا در ارسال پوستر #{poster['id']} به تلگرام: {e}")


def crosspost_business_to_eitaa(biz):
    """کراس‌پست best-effort آگهی تاییدشده به کانال ایتا. شکست آن ربات را متوقف نمی‌کند."""
    if not eitaa_api.is_enabled():
        return
    text = (
        f"🏪 {biz['name']}\n"
        f"🏷 دسته‌بندی: {biz['category']}\n\n"
        f"{biz['description']}\n\n"
        f"📞 تماس: {biz['phone']}\n"
        f"📍 آدرس: {biz['address']}\n\n"
        "🔹 معرفی‌شده در ربات kasbyarmarket"
    )
    try:
        photo_bytes = None
        if biz.get("photo_file_id"):
            if biz.get("platform") == "bale":
                kind, payload = _relay_photo_for_telegram(biz["photo_file_id"], "bale")
                photo_bytes = payload if kind == "bytes" else None
            else:
                file_info = telegram_api.get_file(biz["photo_file_id"])
                file_path = file_info.get("result", {}).get("file_path") if file_info.get("ok") else None
                photo_bytes = telegram_api.download_file(file_path) if file_path else None

            if photo_bytes:
                eitaa_api.send_photo_bytes(config.EITAA_CHANNEL_ID, photo_bytes,
                                            filename=f"biz_{biz['id']}.jpg", caption=text)
                return
        eitaa_api.send_message(config.EITAA_CHANNEL_ID, text)
    except Exception as e:
        print(f"[crosspost] خطا در ارسال کسب‌وکار #{biz['id']} به ایتا: {e}")


def crosspost_poster_to_eitaa(poster):
    """کراس‌پست best-effort پوستر تبلیغاتی تاییدشده به کانال ایتا."""
    if not eitaa_api.is_enabled():
        return
    try:
        photo_bytes = None
        if poster.get("platform") == "bale":
            kind, payload = _relay_photo_for_telegram(poster["photo_file_id"], "bale")
            if kind == "bytes":
                photo_bytes = payload
        else:
            file_info = telegram_api.get_file(poster["photo_file_id"])
            file_path = file_info.get("result", {}).get("file_path") if file_info.get("ok") else None
            photo_bytes = telegram_api.download_file(file_path) if file_path else None

        if photo_bytes:
            eitaa_api.send_photo_bytes(config.EITAA_POSTER_CHANNEL_ID, photo_bytes,
                                        filename=f"poster_{poster['id']}.jpg",
                                        caption=poster.get("caption") or None)
        elif poster.get("caption"):
            eitaa_api.send_message(config.EITAA_POSTER_CHANNEL_ID, poster["caption"])
    except Exception as e:
        print(f"[crosspost] خطا در ارسال پوستر #{poster['id']} به ایتا: {e}")


def publish_to_channel(biz):
    text = (
        f"🏪 {biz['name']}\n"
        f"📂 دسته‌بندی: {biz['category']}\n\n"
        f"{biz['description']}\n\n"
        f"📞 تماس: {biz['phone']}\n"
        f"📍 آدرس: {biz['address']}\n\n"
        "🔗 معرفی‌شده در ربات @kasbyarMarketbot"
    )

    if biz.get("photo_file_id"):
        if biz.get("platform") == "bale":
            kind, payload = _relay_photo_for_telegram(
                biz["photo_file_id"], "bale"
            )

            if kind == "bytes":
                result = telegram_api.send_photo_bytes(
                    config.PUBLIC_CHANNEL_ID,
                    payload,
                    filename=f"biz_{biz['id']}.jpg",
                    caption=text
                )
            else:
                result = telegram_api.send_message(
                    config.PUBLIC_CHANNEL_ID,
                    text
                )
        else:
            result = telegram_api.send_photo(
                config.PUBLIC_CHANNEL_ID,
                biz["photo_file_id"],
                caption=text
            )
    else:
        result = telegram_api.send_message(
            config.PUBLIC_CHANNEL_ID,
            text
        )

    if result.get("ok"):
        return result["result"]["message_id"]

    return None


# ---------------------------------------------------------------------
# پردازش Callback Query ها (دکمه‌های اینلاین)
# ---------------------------------------------------------------------
def handle_callback_query(cq):
    cq_id = cq["id"]
    from_user = cq.get("from", {})
    user_id = platform_user_id(from_user.get("id"))
    message = cq.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    message_id = message.get("message_id")
    data = cq.get("data", "")

    parts = data.split(":")
    action = parts[0]

    # ---------- تایید نهایی کاربر برای ارسال درخواست ثبت ----------
    if action == "submit":
        state = user_states.get(user_id)
        if not state or state.get("step") != "biz_confirm":
            api.answer_callback_query(cq_id, "این درخواست دیگر معتبر نیست.")
            return
        d = state["data"]
        biz_id = db.create_business(
            user_id, d["name"], d["category"], d["description"],
            d["phone"], d["address"], d.get("photo_file_id"),
            platform=current_platform,
        )
        reset_state(user_id)
        api.answer_callback_query(cq_id, "درخواست شما ثبت شد ✅")
        api.send_message(chat_id, "✅ درخواست شما برای بررسی مدیر ارسال شد. پس از تایید، به شما اطلاع داده می‌شود.",
                          reply_markup=kb.main_menu_keyboard())
        biz = db.get_business(biz_id)
        send_business_to_admin(biz)
        return

    if action == "cancel_submit":
        reset_state(user_id)
        api.answer_callback_query(cq_id, "لغو شد.")
        api.send_message(chat_id, "ثبت کسب‌وکار لغو شد.", reply_markup=kb.main_menu_keyboard())
        return

    # ---------- تایید نهایی کاربر برای ارسال پوستر تبلیغاتی (مسیر مستقل) ----------
    if action == "submit_poster":
        state = user_states.get(user_id)
        if not state or state.get("step") != "poster_confirm":
            api.answer_callback_query(cq_id, "این درخواست دیگر معتبر نیست.")
            return
        d = state["data"]
        poster_id = db.create_poster(user_id, d.get("caption", ""), d["photo_file_id"], platform=current_platform)
        reset_state(user_id)
        api.answer_callback_query(cq_id, "پوستر شما ثبت شد ✅")
        api.send_message(chat_id, "✅ پوستر تبلیغاتی شما برای بررسی مدیر ارسال شد.",
                          reply_markup=kb.main_menu_keyboard())
        poster = db.get_poster(poster_id)
        send_poster_to_admin(poster)
        return

    if action == "cancel_poster":
        reset_state(user_id)
        api.answer_callback_query(cq_id, "لغو شد.")
        api.send_message(chat_id, "ثبت پوستر تبلیغاتی لغو شد.", reply_markup=kb.main_menu_keyboard())
        return

    # ---------- تایید/رد پوستر تبلیغاتی توسط ادمین (مسیر مستقل، بدون اشتراک/پرداخت) ----------
    if action == "approve_poster":
        if not is_admin(user_id):
            api.answer_callback_query(cq_id, "شما دسترسی ادمین ندارید.")
            return
        poster_id = int(parts[1])
        poster = db.get_poster(poster_id)
        if not poster or poster["status"] != "pending":
            api.answer_callback_query(cq_id, "این پوستر قبلاً پردازش شده است.")
            return
        channel_msg_id = publish_poster_to_channel(poster)
        db.approve_poster(poster_id, channel_msg_id)
        crosspost_poster_to_telegram(poster)
        crosspost_poster_to_eitaa(poster)
        api.answer_callback_query(cq_id, "پوستر تایید شد ✅")
        api.edit_message_reply_markup(chat_id, message_id, reply_markup={"inline_keyboard": []})
        notify_owner(poster["user_id"], "🎉 پوستر تبلیغاتی شما تایید و در کانال منتشر شد.")
        return

    if action == "reject_poster":
        if not is_admin(user_id):
            api.answer_callback_query(cq_id, "شما دسترسی ادمین ندارید.")
            return
        poster_id = int(parts[1])
        poster = db.get_poster(poster_id)
        if not poster or poster["status"] != "pending":
            api.answer_callback_query(cq_id, "این پوستر قبلاً پردازش شده است.")
            return
        db.reject_poster(poster_id, reason="عدم تطابق با قوانین کانال")
        api.answer_callback_query(cq_id, "پوستر رد شد 🚫")
        api.edit_message_reply_markup(chat_id, message_id, reply_markup={"inline_keyboard": []})
        notify_owner(poster["user_id"], "متاسفانه پوستر تبلیغاتی شما رد شد.")
        return

    # ---------- تایید/رد توسط ادمین (کسب‌وکار) ----------
    if action == "approve":
        if not is_admin(user_id):
            api.answer_callback_query(cq_id, "شما دسترسی ادمین ندارید.")
            return
        biz_id = int(parts[1])
        biz = db.get_business(biz_id)
        if not biz or biz["status"] != "pending":
            api.answer_callback_query(cq_id, "این درخواست قبلاً پردازش شده است.")
            return
        channel_msg_id = publish_to_channel(biz)
        trial_end = db.approve_business(biz_id, channel_msg_id)
        crosspost_business_to_bale(biz)
        # crosspost_business_to_telegram(biz)
        crosspost_business_to_eitaa(biz)
        api.answer_callback_query(cq_id, "تایید شد ✅")
        api.edit_message_reply_markup(chat_id, message_id, reply_markup={"inline_keyboard": []})
        notify_owner(
            biz["user_id"],
            f"🎉 تبریک! کسب‌وکار «{biz['name']}» شما تایید و در کانال منتشر شد.\n"
            f"اشتراک رایگان شما تا تاریخ {format_date(trial_end)} فعال است.",
        )
        return

    if action == "reject":
        if not is_admin(user_id):
            api.answer_callback_query(cq_id, "شما دسترسی ادمین ندارید.")
            return
        biz_id = int(parts[1])
        biz = db.get_business(biz_id)
        if not biz or biz["status"] != "pending":
            api.answer_callback_query(cq_id, "این درخواست قبلاً پردازش شده است.")
            return
        db.reject_business(biz_id, reason="عدم تطابق با قوانین کانال")
        api.answer_callback_query(cq_id, "رد شد 🚫")
        api.edit_message_reply_markup(chat_id, message_id, reply_markup={"inline_keyboard": []})
        notify_owner(
            biz["user_id"],
            f"متاسفانه درخواست ثبت «{biz['name']}» رد شد.\n"
            "برای اطلاعات بیشتر با پشتیبانی در تماس باشید.",
        )
        return

    # ---------- تمدید/پرداخت اشتراک ----------
    if action == "renew":
        biz_id = int(parts[1])
        biz = db.get_business(biz_id)
        if not biz or biz["user_id"] != user_id:
            api.answer_callback_query(cq_id, "دسترسی غیرمجاز.")
            return
        api.answer_callback_query(cq_id)
        api.send_message(chat_id, "لطفاً یکی از پلن‌های زیر را انتخاب کنید:", reply_markup=kb.plans_keyboard(biz_id))
        return

    if action == "plan":
        biz_id = int(parts[1])
        plan_id = parts[2]
        plan = next((p for p in config.PLANS if p["id"] == plan_id), None)
        biz = db.get_business(biz_id)
        if not plan or not biz or biz["user_id"] != user_id:
            api.answer_callback_query(cq_id, "خطا در پردازش.")
            return
        payment_id = db.create_payment(biz_id, user_id, plan["id"], plan["title"], plan["price"])
        user_states[user_id] = {"step": "awaiting_receipt", "data": {"payment_id": payment_id}}
        api.answer_callback_query(cq_id)
        api.send_message(
            chat_id,
            f"پلن «{plan['title']}» به مبلغ {plan['price']:,} تومان انتخاب شد.\n\n"
            f"لطفاً مبلغ را به شماره کارت زیر واریز کرده و تصویر رسید را ارسال کنید:\n\n"
            f"💳 {config.CARD_NUMBER}\n👤 {config.CARD_OWNER}",
            reply_markup=kb.cancel_keyboard(),
        )
        return

    # ---------- تایید/رد پرداخت توسط ادمین ----------
    if action == "payconfirm":
        if not is_admin(user_id):
            api.answer_callback_query(cq_id, "شما دسترسی ادمین ندارید.")
            return
        payment_id = int(parts[1])
        payment = db.get_payment(payment_id)
        if not payment or payment["status"] != "pending":
            api.answer_callback_query(cq_id, "این پرداخت قبلاً پردازش شده است.")
            return
        plan = next((p for p in config.PLANS if p["id"] == payment["plan_id"]), None)
        days = plan["days"] if plan else 30
        new_end = db.extend_business(payment["business_id"], days)
        db.confirm_payment(payment_id)
        biz = db.get_business(payment["business_id"])
        # اگر آگهی منقضی شده بود، دوباره در کانال منتشر می‌شود
        if biz["status"] == "approved" and not biz.get("channel_message_id"):
            msg_id = publish_to_channel(biz)
            db.set_channel_message_id(biz["id"], msg_id)
            # crosspost_business_to_telegram(biz)
            crosspost_business_to_eitaa(biz)
        api.answer_callback_query(cq_id, "پرداخت تایید شد ✅")
        api.edit_message_reply_markup(chat_id, message_id, reply_markup={"inline_keyboard": []})
        notify_owner(
            payment["user_id"],
            f"✅ پرداخت شما تایید شد. اشتراک کسب‌وکار «{biz['name']}» تا تاریخ {format_date(new_end)} تمدید شد.",
        )
        return

    if action == "payreject":
        if not is_admin(user_id):
            api.answer_callback_query(cq_id, "شما دسترسی ادمین ندارید.")
            return
        payment_id = int(parts[1])
        payment = db.get_payment(payment_id)
        if not payment or payment["status"] != "pending":
            api.answer_callback_query(cq_id, "این پرداخت قبلاً پردازش شده است.")
            return
        db.reject_payment(payment_id)
        api.answer_callback_query(cq_id, "پرداخت رد شد 🚫")
        api.edit_message_reply_markup(chat_id, message_id, reply_markup={"inline_keyboard": []})
        notify_owner(
            payment["user_id"],
            "متاسفانه رسید پرداخت شما تایید نشد. لطفاً دوباره تلاش کنید یا با پشتیبانی تماس بگیرید.",
        )
        return


# ---------------------------------------------------------------------
# دریافت رسید پرداخت (ارسال عکس در حالت awaiting_receipt)
# ---------------------------------------------------------------------
def handle_possible_receipt(message):
    from_user = message.get("from", {})
    user_id = platform_user_id(from_user.get("id"))
    chat_id = message.get("chat", {}).get("id")
    photo = message.get("photo")
    state = user_states.get(user_id)

    if state and state.get("step") == "awaiting_receipt" and photo:
        payment_id = state["data"]["payment_id"]
        file_id = photo[-1]["file_id"]
        db.attach_receipt(payment_id, file_id)
        payment = db.get_payment(payment_id)
        reset_state(user_id)
        api.send_message(chat_id, "✅ رسید شما دریافت شد و برای تایید نهایی به مدیر ارسال شد.",
                          reply_markup=kb.main_menu_keyboard())
        caption = (
            f"🧾 رسید پرداخت جدید\n\n"
            f"شناسه پرداخت: #{payment_id}\n"
            f"کسب‌وکار: #{payment['business_id']}\n"
            f"پلن: {payment['plan_title']}\n"
            f"مبلغ: {payment['amount']:,} تومان\n"
            f"کاربر: {payment['user_id']}"
        )
        kind, payload = _relay_photo_for_telegram(file_id, current_platform)
        markup = kb.admin_payment_keyboard(payment_id)
        if kind == "file_id":
            telegram_api.send_photo(config.ADMIN_REVIEW_CHAT_ID, payload, caption=caption, reply_markup=markup)
        elif kind == "bytes":
            telegram_api.send_photo_bytes(config.ADMIN_REVIEW_CHAT_ID, payload,
                                           filename=f"receipt_{payment_id}.jpg", caption=caption, reply_markup=markup)
        else:
            telegram_api.send_message(config.ADMIN_REVIEW_CHAT_ID, caption, reply_markup=markup)
        return True
    return False

     
