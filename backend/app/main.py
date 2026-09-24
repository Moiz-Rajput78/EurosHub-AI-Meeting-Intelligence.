from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401
from app.api.router import api_router
from app.core.config import settings
from app.core.database import create_database_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.upload_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    create_database_tables()

    yield


app = FastAPI(
    title=settings.app_name,
    description=(
        "Backend API for Meeting Intelligence — "
        "AI Meeting Transcription & Intelligent Notes System."
    ),
    version="0.1.0",
    debug=settings.debug,
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict:
    return {
        "success": True,
        "application": settings.app_name,
        "environment": settings.app_env,
        "message": "Meeting Intelligence API",
        "docs": "/docs",
    }


app.include_router(
    api_router,
    prefix="/api",
)