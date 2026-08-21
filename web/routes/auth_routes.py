# -*- coding: utf-8 -*-
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse

import config
from web import db_web as db
from web.security import is_valid_iran_phone, normalize_phone
from web.deps import get_current_user
from web.templating import templates

router = APIRouter()


@router.get("/register", response_class=HTMLResponse)
def register_form(request: Request):
    if get_current_user(request):
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse(
        request,
        "register.html", {"request": request, "site_name": config.SITE_NAME, "error": None}
    )


@router.post("/register", response_class=HTMLResponse)
def register_submit(
    request: Request,
    full_name: str = Form(...),
    phone: str = Form(...),
    password: str = Form(...),
    password2: str = Form(...),
):
    error = None
    phone_n = normalize_phone(phone)

    if len(full_name.strip()) < 3:
        error = "لطفاً نام و نام خانوادگی کامل را وارد کنید."
    elif not is_valid_iran_phone(phone_n):
        error = "شماره موبایل معتبر نیست. مثال: 09123456789"
    elif len(password) < 6:
        error = "رمز عبور باید حداقل ۶ کاراکتر باشد."
    elif password != password2:
        error = "رمز عبور و تکرار آن یکسان نیستند."
    elif db.phone_exists(phone_n):
        error = "کاربری با این شماره موبایل قبلاً ثبت‌نام کرده است."

    if error:
        return templates.TemplateResponse(
            request,
            "register.html",
            {"request": request, "site_name": config.SITE_NAME, "error": error},
            status_code=400,
        )

    user_id = db.create_web_user(full_name.strip(), phone_n, password)
    request.session["web_user_id"] = user_id
    return RedirectResponse("/dashboard", status_code=302)


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    if get_current_user(request):
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse(
        request,
        "login.html", {"request": request, "site_name": config.SITE_NAME, "error": None}
    )


@router.post("/login", response_class=HTMLResponse)
def login_submit(request: Request, phone: str = Form(...), password: str = Form(...)):
    user = db.authenticate_web_user(phone, password)
    if not user:
        return templates.TemplateResponse(
            request,
            "login.html",
            {"request": request, "site_name": config.SITE_NAME, "error": "شماره موبایل یا رمز عبور اشتباه است."},
            status_code=400,
        )
    request.session["web_user_id"] = user["id"]
    return RedirectResponse("/dashboard", status_code=302)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=302)
