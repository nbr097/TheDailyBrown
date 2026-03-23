from fastapi import FastAPI
from src.config import settings

app = FastAPI(title="Morning Briefing", docs_url=None, redoc_url=None)

@app.get("/health")
async def health():
    return {"status": "ok"}
