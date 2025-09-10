#!/usr/bin/env python3
import sys
import argparse
from pathlib import Path

# Add backend to path so we can import from it
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

import uvicorn

# Import logging utilities
from backend.core.utils.logger import setup_logging, get_logger

# Set up logging first
setup_logging()
logger = get_logger(__name__)


def main():
    parser = argparse.ArgumentParser(description="BookForge Studio")
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Run in development mode (no static file serving)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to run the server on (default: 8000)",
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)"
    )

    args = parser.parse_args()

    # Pass the --dev flag to the backend via sys.argv
    if args.dev and "--dev" not in sys.argv:
        sys.argv.append("--dev")

    logger.info("Starting BookForge Studio...")
    if args.dev:
        logger.info(
            "📱 Development mode: Frontend should be run separately on http://localhost:3000"
        )
        logger.info(f"🔧 Backend API: http://{args.host}:{args.port}/api/")
    else:
        logger.info(
            f"🌐 Production mode: Full app available at http://{args.host}:{args.port}"
        )

    logger.info(f"Server starting on {args.host}:{args.port} (reload=True)")

    # Start the server
    uvicorn.run(
        "core.main:app",
        host=args.host,
        port=args.port,
        reload=True,
        reload_dirs=["backend"],
    )


if __name__ == "__main__":
    main()
