from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import router
from app.core.config import get_settings
from app.db.seed import initialize_database


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        initialize_database()
        yield

    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description="Read-only curriculum API seeded from the DegreePlanDatabase JSON source.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    app.include_router(router, prefix=settings.api_v1_prefix)

    # Serve the built frontend (Next.js static export) when present. Registered
    # last so it only catches paths not already handled by the API router, /docs,
    # or /openapi.json. In local dev without a build the directory is absent, so
    # the API still runs standalone and "/" returns the JSON info payload.
    static_dir = Path(os.getenv("STATIC_DIR", "static"))
    if static_dir.is_dir():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="frontend")
    else:
        @app.get("/", tags=["system"])
        def root() -> dict[str, str]:
            return {
                "message": "Degree Plan Curriculum API",
                "docs": "/docs",
                "openapi": "/openapi.json",
                "health": f"{settings.api_v1_prefix}/health",
            }

    return app


app = create_app()
