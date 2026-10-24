from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from pathlib import Path

router = APIRouter()
ROOT = Path(__file__).parent


@router.get("/login", response_class=HTMLResponse)
def login():
    return (ROOT / "web/templates/login.html").read_text()


@router.get("/register", response_class=HTMLResponse)
def register():
    return (ROOT / "web/templates/register.html").read_text()


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    return (ROOT / "web/templates/dashboard.html").read_text()
