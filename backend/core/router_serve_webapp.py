from pathlib import Path
from fastapi import APIRouter, HTTPException, FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Import logging utilities
from backend.core.utils.logger import get_logger

logger = get_logger(__name__)

# Create router for webapp serving endpoints
router = APIRouter(tags=["webapp"])

# --- Configuration for Frontend ---
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # Points to project root
FRONTEND_BUILD_DIR = BASE_DIR / "frontend-build"


def create_webapp_router(dev_mode: bool = False):
    """
    Creates and configures the webapp router based on the development mode.

    Args:
        dev_mode: Whether the app is running in development mode

    Returns:
        Configured APIRouter for webapp serving
    """
    webapp_router = APIRouter(tags=["webapp"])

    if dev_mode:

        @webapp_router.get("/")
        async def root():
            logger.info("Dev mode root endpoint accessed")
            return {
                "message": "You are running in dev mode, which means you can/should run the react app locally.",
                "dev_mode": True,
                "frontend_url": "http://localhost:3000",
            }

    # Only add frontend serving routes when not in dev mode
    if not dev_mode:

        @webapp_router.get("/{full_path:path}")
        async def serve_frontend(full_path: str):
            """
            Serves the React frontend for all non-API routes.
            This enables client-side routing to work properly.
            """
            # Skip API routes
            if full_path.startswith("api/"):
                logger.warning(
                    f"API route accessed through frontend handler: {full_path}"
                )
                raise HTTPException(status_code=404, detail="API endpoint not found")

            # Check if frontend build exists
            if not FRONTEND_BUILD_DIR.exists():
                logger.error("Frontend build directory not found")
                raise HTTPException(
                    status_code=503,
                    detail="Frontend not built. Please run 'npm run build' in the frontend directory.",
                )

            # Try to serve the requested file
            requested_file = FRONTEND_BUILD_DIR / full_path
            if requested_file.is_file():
                logger.info(f"Serving frontend file: {full_path}")
                return FileResponse(requested_file)

            # For all other routes (including SPA routes), serve index.html
            index_file = FRONTEND_BUILD_DIR / "index.html"
            if index_file.exists():
                logger.info(f"Serving SPA route: {full_path} -> index.html")
                return FileResponse(index_file)
            else:
                logger.error("Frontend index.html not found")
                raise HTTPException(
                    status_code=503,
                    detail="Frontend index.html not found. Please ensure the frontend is properly built.",
                )

    return webapp_router
