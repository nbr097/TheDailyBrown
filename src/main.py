from __future__ import annotations

import asyncio
import logging
import json as json_lib
import os
from contextlib import asynccontextmanager
from datetime import datetime


class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json_lib.dumps({
            "ts": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        })


handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logging.basicConfig(level=logging.INFO, handlers=[handler])

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from src.database import init_db
from src.auth.webauthn import router as webauthn_router
from src.routes.admin import router as admin_router
from src.routes.data import router as data_router
from src.routes.summary import router as summary_router
from src.scheduler import create_scheduler, get_system_health, run_cache_job

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    scheduler = create_scheduler()
    scheduler.start()
    # Non-blocking startup cache run
    asyncio.create_task(run_cache_job())
    logger.info("Scheduler started, initial cache job dispatched")
    yield
    # Shutdown
    scheduler.shutdown(wait=False)


app = FastAPI(title="Morning Briefing", docs_url=None, redoc_url=None, lifespan=lifespan)
app.include_router(admin_router)
app.include_router(data_router)
app.include_router(summary_router)
app.include_router(webauthn_router)


dashboard_path = os.path.join(os.path.dirname(__file__), "..", "dashboard")
app.mount("/dashboard", StaticFiles(directory=dashboard_path, html=True), name="dashboard")


@app.get("/")
async def root():
    return RedirectResponse("/dashboard/")


@app.get("/health")
async def health():
    systems = get_system_health()
    has_errors = any(s.get("status") == "error" for s in systems.values())
    return {"status": "degraded" if has_errors else "healthy", "systems": systems}
