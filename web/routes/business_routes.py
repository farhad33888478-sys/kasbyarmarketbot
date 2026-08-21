# -*- coding: utf-8 -*-
import os
import uuid

from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse

import config
from web import db_web as db
from web import media
from web.deps import get_current_user
from web.templating import templates

router = APIRouter()

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    businesses = media.attach_photo_urls(db.list_businesses_by_web_user(user["id"]))
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"request": request, "site_name": config.SITE_NAME, "user": user, "businesses": businesses},
    )


@router.get("/business/new", response_class=HTMLResponse)
def new_business_form(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse(
        request,
        "business_form.html",
        {"request": request, "site_name": config.SITE_NAME, "user": user, "categories": config.CATEGORIES, "error": None},
    )


@router.post("/business/new", response_class=HTMLResponse)
async def new_business_submit(
    request: Request,
    name: str = Form(...),
    category: str = Form(...),
    description: str = Form(...),
    phone: str = Form(...),
    address: str = Form(...),
    photo: UploadFile = File(None),
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)

    error = None
    if len(name.strip()) < 2:
        error = "نام کسب‌وکار را وارد کنید."
    elif category not in config.CATEGORIES:
        error = "دسته‌بندی معتبر نیست."
    elif len(phone.strip()) < 8:
        error = "شماره تماس معتبر نیست."

    if error:
        return templates.TemplateResponse(
            request,
            "business_form.html",
            {"request": request, "site_name": config.SITE_NAME, "user": user, "categories": config.CATEGORIES, "error": error},
            status_code=400,
        )

    photo_path = None
    if photo and photo.filename:
        ext = os.path.splitext(photo.filename)[1][:10]
        filename = f"{uuid.uuid4().hex}{ext}"
        dest = os.path.join(UPLOAD_DIR, filename)
        with open(dest, "wb") as f:
            f.write(await photo.read())
        photo_path = f"/static/uploads/{filename}"

    db.create_business_web(user["id"], name.strip(), category, description.strip(), phone.strip(), address.strip(), photo_path)
    return RedirectResponse("/dashboard", status_code=302)
