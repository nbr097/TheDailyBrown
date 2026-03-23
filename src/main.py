from fastapi import FastAPI
from src.config import settings
from src.routes.data import router as data_router

app = FastAPI(title="Morning Briefing", docs_url=None, redoc_url=None)
app.include_router(data_router)

@app.get("/health")
async def health():
    return {"status": "ok"}
