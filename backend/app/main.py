import secrets
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.routes import uploads, embed, chat, sessions, textbooks, sample
from app import config
from app.services import lmstudio, jobs
from app.routes import jobs as job_routes
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app):
    stop, thread = jobs.start()
    yield
    stop.set()
    thread.join(6)


app = FastAPI(title="DRAX · Document study workspace", version="3.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "X-DRAX-Key"],
)


@app.middleware("http")
async def protect_workspace(request: Request, call_next):
    # Single shared workspace. Network use requires an explicit key.
    if request.url.path.startswith("/api") and request.method != "OPTIONS":
        if config.API_KEY:
            if not secrets.compare_digest(request.headers.get("X-DRAX-Key", ""), config.API_KEY):
                return JSONResponse({"detail": "Enter the workspace access key."}, status_code=401)
        elif request.client and request.client.host not in {"127.0.0.1", "::1", "testclient"}:
            return JSONResponse({"detail": "Network access requires DRAX_API_KEY."}, status_code=403)
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.get("/health")
def health():
    return {"status": "ok", "version": "3.0.0"}


@app.get("/api/status")
def status():
    try:
        models = lmstudio.available_models()
        return {
            "model_ready": bool(models),
            "models": models,
            "retrieval": config.RETRIEVAL_MODE,
            "max_file_mb": config.MAX_FILE_BYTES // 1024 // 1024,
            "max_pages": config.MAX_PAGES,
        }
    except lmstudio.ModelUnavailable:
        return {
            "model_ready": False,
            "models": [],
            "retrieval": config.RETRIEVAL_MODE,
            "max_file_mb": config.MAX_FILE_BYTES // 1024 // 1024,
            "max_pages": config.MAX_PAGES,
        }


for route in [uploads, embed, chat, sessions, textbooks, sample, job_routes]:
    app.include_router(route.router, prefix="/api")
