# -*- coding: utf-8 -*-
"""
توابع کمکی برای ساخت کیبوردهای اینلاین (Inline) و کیبوردهای معمولی (Reply)
"""

import config


def main_menu_keyboard():
    return {
        "keyboard": [
            [{"text": "🏪 ثبت کسب‌وکار جدید"}],
            [{"text": "📢 ثبت پوستر تبلیغاتی"}],
            [{"text": "📋 کسب‌وکارهای من"}, {"text": "🖼 پوسترهای من"}],
            [{"text": "ℹ️ راهنما"}],
        ],
        "resize_keyboard": True,
    }


def cancel_keyboard():
    return {
        "keyboard": [[{"text": "❌ انصراف"}]],
        "resize_keyboard": True,
    }


def categories_keyboard():
    rows = []
    row = []
    for i, cat in enumerate(config.CATEGORIES, start=1):
        row.append({"text": cat})
        if i % 2 == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([{"text": "❌ انصراف"}])
    return {"keyboard": rows, "resize_keyboard": True}


def skip_or_cancel_keyboard():
    return {
        "keyboard": [[{"text": "⏭ رد کردن (بدون عکس)"}], [{"text": "❌ انصراف"}]],
        "resize_keyboard": True,
    }


def confirm_business_keyboard(temp_key):
    return {
        "inline_keyboard": [
            [
                {"text": "✅ تایید و ارسال برای بررسی", "callback_data": f"submit:{temp_key}"},
                {"text": "❌ انصراف", "callback_data": f"cancel_submit:{temp_key}"},
            ]
        ]
    }


def admin_review_keyboard(biz_id):
    return {
        "inline_keyboard": [
            [
                {"text": "✅ تایید", "callback_data": f"approve:{biz_id}"},
                {"text": "🚫 رد", "callback_data": f"reject:{biz_id}"},
            ]
        ]
    }


def admin_poster_review_keyboard(poster_id):
    return {
        "inline_keyboard": [
            [
                {"text": "✅ تایید پوستر", "callback_data": f"approve_poster:{poster_id}"},
                {"text": "🚫 رد پوستر", "callback_data": f"reject_poster:{poster_id}"},
            ]
        ]
    }


def confirm_poster_keyboard():
    return {
        "inline_keyboard": [
            [
                {"text": "✅ تایید و ارسال برای بررسی", "callback_data": "submit_poster"},
                {"text": "❌ انصراف", "callback_data": "cancel_poster"},
            ]
        ]
    }


def plans_keyboard(biz_id):
    rows = []
    for plan in config.PLANS:
        label = f"{plan['title']} - {plan['price']:,} تومان"
        rows.append([{"text": label, "callback_data": f"plan:{biz_id}:{plan['id']}"}])
    return {"inline_keyboard": rows}


def admin_payment_keyboard(payment_id):
    return {
        "inline_keyboard": [
            [
                {"text": "✅ تایید پرداخت", "callback_data": f"payconfirm:{payment_id}"},
                {"text": "🚫 رد پرداخت", "callback_data": f"payreject:{payment_id}"},
            ]
        ]
    }


def my_business_action_keyboard(biz_id, status):
    buttons = []
    if status in ("approved", "expired"):
        buttons.append([{"text": "💳 تمدید / پرداخت اشتراک", "callback_data": f"renew:{biz_id}"}])
    return {"inline_keyboard": buttons} if buttons else None
