import asyncio
import os
import sys
import argparse
import logging
import traceback
from pathlib import Path
from typing import Dict, List, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware  # Needed for frontend development

from backend.core.router_filesystem import router as filesystem_router

from backend.core.router_steps import router as steps_router

from backend.core.router_text_workflows import router as text_workflows_router

from backend.core.router_models import router as models_router

from backend.core.router_serve_webapp import create_webapp_router

from backend.core.router_logs import router as logs_router

from backend.core.router_data_download import router as data_download_router

from backend.core.router_websocket import router as websocket_router

from backend.core.utils.logger import get_logger

from backend.core.setup.setup import setup_process

logger = get_logger(__name__)

parser = argparse.ArgumentParser(description="Audio AI Studio Backend")
parser.add_argument(
    "--dev",
    action="store_true",
    help="Run in development mode (no static file serving)",
)
parser.add_argument(
    "--skip_setup",
    action="store_true",
    help="Skip the setup process",
    default=False,
)
args, unknown = parser.parse_known_args()

DEV_MODE = args.dev
SKIP_SETUP = args.skip_setup


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    if not SKIP_SETUP:
        await setup_process()

    yield

    # Shutdown (if needed)
    logger.info("Application shutting down")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    # allow_origins=["http://localhost:3000" if DEV_MODE else "http://localhost:8000"],
    allow_origins=["*"],
    # allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler that logs all unhandled exceptions to stdout.
    This makes debugging much easier during development.
    """
    # Log the full exception with traceback
    logger.error(f"Unhandled exception in {request.method} {request.url}:")
    logger.error(f"Exception type: {type(exc).__name__}")
    logger.error(f"Exception message: {str(exc)}")
    logger.error(f"Traceback:\n{traceback.format_exc()}")

    # In development mode, return detailed error info
    if DEV_MODE:
        return JSONResponse(
            status_code=500,
            content={
                "detail": f"{type(exc).__name__}: {str(exc)}",
                "traceback": traceback.format_exc().split("\n") if DEV_MODE else None,
            },
        )
    else:
        # In production, return generic error
        return JSONResponse(
            status_code=500, content={"detail": "Internal server error"}
        )


# HTTP exception handler (for intentionally raised HTTPExceptions)
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Handler for HTTPException - logs them but doesn't change the response.
    """
    logger.warning(
        f"HTTPException in {request.method} {request.url}: {exc.status_code} - {exc.detail}"
    )

    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


# Include the filesystem router
app.include_router(filesystem_router)

# Include the steps router
app.include_router(steps_router)

# Include the text workflows router
app.include_router(text_workflows_router)

# Include the models router
app.include_router(models_router)

# Include the logs router
app.include_router(logs_router)

# Include the data download router
app.include_router(data_download_router)

# Include the WebSocket router
app.include_router(websocket_router)

# Include the webapp router (configured based on dev mode)
webapp_router = create_webapp_router(dev_mode=DEV_MODE)
app.include_router(webapp_router)

print("")
print("")
print("=" * 50)
print("Startup complete")
print(
    "\033[1;96mGo to \033[1;94mhttp://localhost:8000\033[1;96m to access the frontend\033[0m"
)
print("=" * 50)
print("")
print("")
