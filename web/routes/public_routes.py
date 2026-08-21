# -*- coding: utf-8 -*-
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

import config
from web import db_web as db
from web import media
from web.deps import get_current_user
from web.templating import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def home(request: Request, category: str = None, q: str = None):
    businesses = media.attach_photo_urls(db.list_approved_businesses(category=category, search=q))
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "request": request,
            "site_name": config.SITE_NAME,
            "businesses": businesses,
            "categories": config.CATEGORIES,
            "selected_category": category,
            "search_query": q or "",
            "user": get_current_user(request),
            "settings": db.get_all_settings(),
        },
    )


@router.get("/business/{biz_id}", response_class=HTMLResponse)
def business_detail(request: Request, biz_id: int):
    biz = media.attach_photo_url(db.get_business_by_id(biz_id))
    return templates.TemplateResponse(
        request,
        "business_detail.html",
        {
            "request": request,
            "site_name": config.SITE_NAME,
            "biz": biz,
            "user": get_current_user(request),
            "settings": db.get_all_settings(),
        },
    )
