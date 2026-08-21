# -*- coding: utf-8 -*-
import os
import uuid

from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse

import config
from web import db_web as db
from web import media
from web.deps import is_admin
from web.templating import templates

router = APIRouter(prefix="/admin")

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.get("/login", response_class=HTMLResponse)
def admin_login_form(request: Request):
    if is_admin(request):
        return RedirectResponse("/admin", status_code=302)
    return templates.TemplateResponse(
        request,
        "admin/login.html", {"request": request, "site_name": config.SITE_NAME, "error": None}
    )


@router.post("/login", response_class=HTMLResponse)
def admin_login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == config.ADMIN_WEB_USERNAME and password == config.ADMIN_WEB_PASSWORD:
        request.session["is_admin"] = True
        return RedirectResponse("/admin", status_code=302)
    return templates.TemplateResponse(
        request,
        "admin/login.html",
        {"request": request, "site_name": config.SITE_NAME, "error": "نام کاربری یا رمز عبور اشتباه است."},
        status_code=400,
    )


@router.get("/logout")
def admin_logout(request: Request):
    request.session.pop("is_admin", None)
    return RedirectResponse("/", status_code=302)


@router.get("", response_class=HTMLResponse)
def admin_dashboard(request: Request):
    if not is_admin(request):
        return RedirectResponse("/admin/login", status_code=302)
    stats = db.count_stats()
    pending = media.attach_photo_urls(db.list_pending_businesses())
    return templates.TemplateResponse(
        request,
        "admin/dashboard.html",
        {"request": request, "site_name": config.SITE_NAME, "stats": stats, "pending": pending},
    )


@router.get("/businesses", response_class=HTMLResponse)
def admin_businesses(request: Request):
    if not is_admin(request):
        return RedirectResponse("/admin/login", status_code=302)
    businesses = media.attach_photo_urls(db.list_all_businesses())
    return templates.TemplateResponse(
        request,
        "admin/businesses.html",
        {"request": request, "site_name": config.SITE_NAME, "businesses": businesses},
    )


@router.get("/settings", response_class=HTMLResponse)
def admin_settings_form(request: Request):
    if not is_admin(request):
        return RedirectResponse("/admin/login", status_code=302)
    return templates.TemplateResponse(
        request,
        "admin/settings.html",
        {"request": request, "site_name": config.SITE_NAME, "settings": db.get_all_settings(), "saved": False},
    )


@router.post("/settings", response_class=HTMLResponse)
async def admin_settings_submit(
    request: Request,
    hero_tagline: str = Form(""),
    telegram_channel: str = Form(""),
    bale_channel: str = Form(""),
    support_phone: str = Form(""),
    about_text: str = Form(""),
    instagram: str = Form(""),
    whatsapp: str = Form(""),
    hero_image: UploadFile = File(None),
    site_logo: UploadFile = File(None),
):
    if not is_admin(request):
        return RedirectResponse("/admin/login", status_code=302)

    values = {
        "hero_tagline": hero_tagline.strip(),
        "telegram_channel": telegram_channel.strip().lstrip("@"),
        "bale_channel": bale_channel.strip().lstrip("@"),
        "support_phone": support_phone.strip(),
        "about_text": about_text.strip(),
        "instagram": instagram.strip().lstrip("@"),
        "whatsapp": whatsapp.strip(),
    }

    if hero_image and hero_image.filename:
        ext = os.path.splitext(hero_image.filename)[1][:10] or ".jpg"
        filename = f"hero_{uuid.uuid4().hex}{ext}"
        dest = os.path.join(UPLOAD_DIR, filename)
        with open(dest, "wb") as f:
            f.write(await hero_image.read())
        values["hero_image"] = f"/static/uploads/{filename}"

    if site_logo and site_logo.filename:
        ext = os.path.splitext(site_logo.filename)[1][:10] or ".png"
        filename = f"logo_{uuid.uuid4().hex}{ext}"
        dest = os.path.join(UPLOAD_DIR, filename)
        with open(dest, "wb") as f:
            f.write(await site_logo.read())
        values["site_logo"] = f"/static/uploads/{filename}"

    db.set_settings(values)
    return templates.TemplateResponse(
        request,
        "admin/settings.html",
        {"request": request, "site_name": config.SITE_NAME, "settings": db.get_all_settings(), "saved": True},
    )


@router.post("/business/{biz_id}/approve")
def admin_approve(request: Request, biz_id: int):
    if not is_admin(request):
        return RedirectResponse("/admin/login", status_code=302)
    db.approve_business_web(biz_id)
    return RedirectResponse("/admin", status_code=302)


@router.post("/business/{biz_id}/reject")
def admin_reject(request: Request, biz_id: int, reason: str = Form("")):
    if not is_admin(request):
        return RedirectResponse("/admin/login", status_code=302)
    db.reject_business_web(biz_id, reason)
    return RedirectResponse("/admin", status_code=302)
