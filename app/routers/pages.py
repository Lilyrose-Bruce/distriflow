# app/routers/pages.py
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
def root():
    return RedirectResponse(url="/login", status_code=302)


@router.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/dashboard")
def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request, "active": "dashboard"})


@router.get("/plan/new")
def new_plan_page(request: Request):
    return templates.TemplateResponse("new_plan.html", {"request": request, "active": "new_plan"})


@router.get("/staging")
def staging_page(request: Request):
    return templates.TemplateResponse("staging.html", {"request": request, "active": "staging"})


@router.get("/plans/draft/view")
def draft_view(request: Request):
    return templates.TemplateResponse("plan_draft.html", {"request": request, "active": "draft"})


@router.get("/plans/approved")
def approved_plan_page(request: Request):
    return templates.TemplateResponse("plan_approved.html", {"request": request, "active": "approved"})


@router.get("/plans/history")
def saved_view(request: Request):
    return templates.TemplateResponse("plans_saved.html", {"request": request, "active": "saved"})


@router.get("/admin/customers")
def admin_customers(request: Request):
    return templates.TemplateResponse("admin_cust.html", {"request": request, "active": "admin"})

@router.get("/admin/trucks")
def admin_trucks(request: Request):
    return templates.TemplateResponse("admin_trucks.html", {"request": request, "active": "admin"})

@router.get("/admin/users")
def admin_users(request: Request):
    return templates.TemplateResponse("admin_users.html", {"request": request, "active": "admin"})