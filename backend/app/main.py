from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import get_settings
from app.routers import auth, watchlists, stocks, preferences

settings = get_settings()

app = FastAPI(
    title="Market Pulse API",
    description="What changed since I last looked? A meaningful-change watchlist engine.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(watchlists.router)
app.include_router(stocks.router)
app.include_router(preferences.router)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "service": settings.APP_NAME}


FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="static-assets")

    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        file_path = FRONTEND_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIR / "index.html")


@app.middleware("http")
async def serve_spa_for_shadowed_routes(request: Request, call_next):
    """Serve the SPA for browser navigations whose path collides with an API route.

    ``GET /preferences`` is both an API endpoint and a client-side route. API
    clients send ``Accept: application/json`` (or ``*/*``), while browser
    navigations send ``Accept: text/html``, so only the latter get the SPA.
    """
    if (
        FRONTEND_DIR.exists()
        and request.method == "GET"
        and request.url.path == "/preferences"
        and "text/html" in request.headers.get("accept", "")
    ):
        return FileResponse(FRONTEND_DIR / "index.html")
    return await call_next(request)
