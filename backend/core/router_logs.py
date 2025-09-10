import asyncio
import os
from pathlib import Path
from typing import AsyncGenerator
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import logging

# Import thread pool utility
from backend.core.utils.threading import run_in_thread_pool

# Create router for log streaming endpoints
router = APIRouter(prefix="/api/logs", tags=["logs"])

# Get the log file path (will be created by main.py)
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # Points to project root
LOG_FILE_PATH = BASE_DIR / "logs" / "backend_logs.txt"

# Ensure logs directory exists
LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger(__name__)


async def tail_log_file() -> AsyncGenerator[str, None]:
    """
    Tail the log file and yield new lines as they appear.
    This is a generator that continuously monitors the log file for new content.
    """
    try:
        # Ensure log file exists
        if not LOG_FILE_PATH.exists():
            LOG_FILE_PATH.touch()
            yield f"data: Log file created at {LOG_FILE_PATH}\n\n"

        # Open file and seek to end
        with open(LOG_FILE_PATH, "r", encoding="utf-8") as file:
            # Move to end of file
            file.seek(0, 2)

            # Send initial connection message
            yield f"data: Connected to log stream\n\n"

            while True:
                line = file.readline()
                if line:
                    # Format as Server-Sent Event
                    # Escape newlines for SSE format
                    escaped_line = (
                        line.rstrip("\n\r").replace("\n", "\\n").replace("\r", "\\r")
                    )
                    yield f"data: {escaped_line}\n\n"
                else:
                    # No new data, wait a bit before checking again
                    await asyncio.sleep(0.5)

    except Exception as e:
        logger.error(f"Error in log tail: {e}")
        yield f"data: Error reading log file: {e}\n\n"


@router.get("/stream")
async def stream_logs():
    """
    Stream server logs in real-time using Server-Sent Events (SSE).

    Returns:
        StreamingResponse: SSE stream of log entries
    """
    return StreamingResponse(
        tail_log_file(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        },
    )


def _read_log_file():
    """Helper function to read log file in thread pool"""
    if not LOG_FILE_PATH.exists():
        return [], 0

    with open(LOG_FILE_PATH, "r", encoding="utf-8") as file:
        all_lines = file.readlines()

    return all_lines, len(all_lines)


@router.get("/history")
async def get_log_history(lines: int = 100):
    """
    Get the last N lines of the log file for historical viewing.

    Args:
        lines: Number of recent log lines to return (default 100)

    Returns:
        dict: Contains the recent log lines
    """
    try:
        # Read file in thread pool to avoid blocking
        all_lines, total_lines = await run_in_thread_pool(_read_log_file)

        # Get the last N lines
        recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines

        # Strip newlines for clean response
        clean_lines = [line.rstrip("\n\r") for line in recent_lines]

        return {
            "lines": clean_lines,
            "total_lines": total_lines,
            "requested_lines": lines,
        }

    except Exception as e:
        logger.error(f"Error reading log history: {e}")
        return {"error": f"Failed to read log history: {e}"}
