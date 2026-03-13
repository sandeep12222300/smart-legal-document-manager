"""
main.py — FastAPI application entry point.

Usage:
    uvicorn app.main:app --reload

The server auto-creates SQLite tables on startup (no migrations needed for
local dev). For production PostgreSQL deployments, use Alembic migrations.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base
from app.routes.document_routes import router as document_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)



@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Creating database tables (if they don't exist)…")
    Base.metadata.create_all(bind=engine)
    logger.info("Database ready.")
    yield
    logger.info("Shutting down Smart Legal Document Manager.")


 
app = FastAPI(
    title="Smart Legal Document Manager",
    description=(
        "A production-ready legal document versioning API. "
        "Track changes, compare versions, and audit who edited what and when."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

                                                                  
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

 
app.include_router(document_router)


@app.get("/", tags=["Health"])
def health_check() -> dict:
    """Quick health check endpoint."""
    return {
        "status": "ok",
        "service": "Smart Legal Document Manager",
        "version": "1.0.0",
    }
