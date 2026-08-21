# -*- coding: utf-8 -*-
"""
اپلیکیشن وب کسب‌یار مارکت (FastAPI)

اجرا:
    uvicorn web.app:app --reload --host 127.0.0.1 --port 8000

این فایل کاملاً مجزا از ربات تلگرام است. اجرای وب هیچ تاثیری روی
main.py (ربات) ندارد و می‌توانید هر دو را همزمان و مستقل اجرا کنید.
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

import config
from web import db_web as db
from web.routes import public_routes, auth_routes, business_routes, admin_routes

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI(title=config.SITE_NAME)

app.add_middleware(SessionMiddleware, secret_key=config.WEB_SECRET_KEY)

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

app.include_router(public_routes.router)
app.include_router(auth_routes.router)
app.include_router(business_routes.router)
app.include_router(admin_routes.router)


@app.on_event("startup")
def on_startup():
    # ساخت جدول‌های اصلی ربات (اگر وجود نداشته باشند) + جدول‌های وب
    import database as bot_db
    bot_db.init_db()
    db.init_web_db()
    print(f"[web] {config.SITE_NAME} روی http://{config.WEB_HOST}:{config.WEB_PORT} در حال اجراست")
