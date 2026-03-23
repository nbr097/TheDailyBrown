from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.database import init_db
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
app.include_router(data_router)
app.include_router(summary_router)


@app.get("/health")
async def health():
    return {"status": "ok", "systems": get_system_health()}
