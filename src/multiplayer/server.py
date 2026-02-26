"""
src/multiplayer/server.py
=========================
FastAPI application entry point for the Scopa multiplayer backend.

Run (development)
-----------------
::

    uvicorn src.multiplayer.server:app --reload --host 0.0.0.0 --port 8000

Run (production)
----------------
::

    uvicorn src.multiplayer.server:app --workers 1 --host 0.0.0.0 --port 8000

Note: use ``--workers 1``.  The in-memory ``SessionManager`` is a single
process object.  For multi-worker/multi-replica deployments, switch to
Redis-backed session storage (see README).
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .manager import manager
from .router import rest_router, ws_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
log = logging.getLogger(__name__)

_CLEANUP_INTERVAL = 600          # run cleanup every 10 minutes
_ROOT             = Path(__file__).resolve().parent.parent.parent
_FRONTEND_DIR     = _ROOT / "frontend" / "build"
_NAPOLITANE_DIR   = _ROOT / "napolitane"


# ─────────────────────────────────────────────────────────────────────────────
#  Application lifecycle
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_cleanup_loop())
    log.info("Scopa multiplayer server started.")
    yield
    task.cancel()
    log.info("Scopa multiplayer server stopped.")


async def _cleanup_loop() -> None:
    while True:
        await asyncio.sleep(_CLEANUP_INTERVAL)
        removed = manager.cleanup_old_sessions()
        if removed:
            log.info("Cleaned up %d stale session(s).", removed)


# ─────────────────────────────────────────────────────────────────────────────
#  Application
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Scopa Multiplayer",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# Allow all origins in development.  Restrict to your domain in production:
#   allow_origins=["https://your-app.onrender.com"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API routers ───────────────────────────────────────────────────────────────
app.include_router(rest_router, prefix="/api")
app.include_router(ws_router)

# ── Static: card images (standalone API / development fallback) ───────────────
# In production the SvelteKit frontend serves images from /assets/napolitane/.
# This mount lets the backend serve them directly when the frontend is absent
# (e.g., during API development or when testing with Postman).
if _NAPOLITANE_DIR.is_dir():
    app.mount(
        "/assets/napolitane",
        StaticFiles(directory=str(_NAPOLITANE_DIR)),
        name="napolitane_assets",
    )

# ── Static: SvelteKit build (production) ─────────────────────────────────────
# When the frontend is built (`cd frontend && npm run build`), FastAPI serves
# the static output.  The catch-all route below handles SPA deep-link routing.
_SVELTE_ASSETS = _FRONTEND_DIR / "_app"
if _SVELTE_ASSETS.is_dir():
    app.mount(
        "/_app",
        StaticFiles(directory=str(_SVELTE_ASSETS)),
        name="svelte_app",
    )


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", include_in_schema=False)
async def health() -> dict:
    return {
        "status":   "ok",
        "sessions": len(manager._sessions),
    }


# ── SPA catch-all (must be registered last) ───────────────────────────────────
@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str) -> FileResponse:
    """
    Serve SvelteKit static files.

    For any path that is not an API or WS route:
    * If the exact file exists in the build output, return it.
    * Otherwise return ``index.html`` so client-side routing can handle
      deep links (e.g. ``/game/abc123``).
    """
    if not _FRONTEND_DIR.is_dir():
        raise HTTPException(
            status_code=503,
            detail="Frontend not built. Run: cd frontend && npm run build",
        )
    target = _FRONTEND_DIR / full_path
    if target.is_file():
        return FileResponse(str(target))
    index = _FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    raise HTTPException(status_code=404, detail="Not found.")
