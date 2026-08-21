# -*- coding: utf-8 -*-
"""وابستگی‌های مشترک: گرفتن کاربر جاری از روی نشست (session)."""

from fastapi import Request

from web import db_web as db


def get_current_user(request: Request):
    user_id = request.session.get("web_user_id")
    if not user_id:
        return None
    return db.get_web_user_by_id(user_id)


def is_admin(request: Request) -> bool:
    return bool(request.session.get("is_admin"))
