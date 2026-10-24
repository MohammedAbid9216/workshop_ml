from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from .config import settings
from .logging_config import setup_logging
from .api.auth import router as auth_router
from .api.chatbot import router as chatbot_router
from .api.dashboard import router as dashboard_router
from .api.appointments import router as appointment_router
from .api.medicines import router as medicine_router
from .api.admin import router as admin_router
from .api.payments import router as payment_router
from .api.prescriptions import router as prescription_router
from .api.orders import router as order_router
from .api.order_payment import router as order_payment_router
from .api.delivery import router as delivery_router
setup_logging()
app=FastAPI(title=settings.app_name,version="1.0.0")
from pathlib import Path
STATIC_DIR = Path(__file__).parent / "web" / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
from .routes import router as page_router
app.include_router(page_router)
app.include_router(auth_router); app.include_router(chatbot_router); app.include_router(dashboard_router); app.include_router(appointment_router); app.include_router(medicine_router); app.include_router(admin_router); app.include_router(payment_router); app.include_router(prescription_router)
app.include_router(order_router)
app.include_router(order_payment_router)
app.include_router(delivery_router)
@app.get("/",response_class=HTMLResponse)
def root(): return '<h1>Sanjeevani Clinic</h1><p>API: <a href="/docs">/docs</a></p>'
@app.get("/health")
def health(): return {"status":"ok","service":"sanjeevani"}
