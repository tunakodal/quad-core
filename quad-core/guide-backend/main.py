"""
GUIDE API — Entry point.

Initializes the FastAPI application, wires all dependencies via the
AppContainer, and registers routers and exception handlers.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.error_mapper import ErrorMapper
from app.core.containers import create_container


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan:
      - Startup : DI container oluşturulur, DB pool açılır (DATABASE_URL varsa)
      - Shutdown: DB pool kapatılır
    """
    from app.core.database import close_pool

    container = await create_container()
    app.state.container = container
    yield
    if container.db_pool is not None:
        await close_pool(container.db_pool)


app = FastAPI(
    title="GUIDE API",
    description="Guided User Itinerary & Destination Explorer — Backend API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — frontend (React) talks to this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Import routers AFTER app creation ─────────────────────────────
from app.api.routes import route_endpoints, poi_endpoints  # noqa: E402

app.include_router(route_endpoints.router, prefix="/api/v1")
app.include_router(poi_endpoints.router, prefix="/api/v1")


# ── Exception handlers ────────────────────────────────────────────

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    status_code, api_error = ErrorMapper.to_api_error(exc)
    return JSONResponse(status_code=status_code, content=api_error.model_dump())


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    status_code, api_error = ErrorMapper.to_api_error(exc)
    return JSONResponse(status_code=status_code, content=api_error.model_dump())


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    status_code, api_error = ErrorMapper.to_api_error(exc)
    return JSONResponse(status_code=status_code, content=api_error.model_dump())


@app.get("/health")
async def health():
    return {"status": "ok", "service": "GUIDE API"}
