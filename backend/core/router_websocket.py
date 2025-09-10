"""
WebSocket Router

Provides simple real-time communication for execution completion notifications
and basic log streaming via WebSocket connections.
"""

import asyncio
import uuid
import json
from typing import Set, Dict
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pathlib import Path
from datetime import datetime

from backend.core.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])

# Track active connections and log streamers
active_connections: Dict[str, WebSocket] = {}
active_log_streamers: Set[str] = set()

# Log file path (same as in router_logs.py)
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # Points to project root
LOG_FILE_PATH = BASE_DIR / "logs" / "backend_logs.txt"


class SimpleWebSocketManager:
    """Simple WebSocket manager for broadcasting execution completion"""

    @staticmethod
    async def broadcast_execution_complete(
        execution_id: str, result: dict, output_subfolder: str
    ):
        """Broadcast execution completion to all connected clients"""
        message = {
            "type": "execution_complete",
            "execution_id": execution_id,
            "result": result,
            "timestamp": datetime.now().isoformat(),
            "output_subfolder": output_subfolder,
        }
        await SimpleWebSocketManager._broadcast(message)

    @staticmethod
    async def broadcast_execution_error(
        execution_id: str, error: str, output_subfolder: str
    ):
        """Broadcast execution error to all connected clients"""
        message = {
            "type": "execution_error",
            "execution_id": execution_id,
            "error": error,
            "timestamp": datetime.now().isoformat(),
            "output_subfolder": output_subfolder,
        }
        await SimpleWebSocketManager._broadcast(message)

    @staticmethod
    async def broadcast_execution_progress(
        execution_id: str,
        step_name: str,
        step_num: int,
        total_steps: int,
        output_subfolder: str,
    ):
        """Broadcast execution progress to all connected clients"""
        message = {
            "type": "execution_progress",
            "execution_id": execution_id,
            "step_name": step_name,
            "progress_percentage": (step_num / total_steps) * 100,
            "step_num": step_num,
            "total_steps": total_steps,
            "timestamp": datetime.now().isoformat(),
            "output_subfolder": output_subfolder,
        }
        print("#" * 80)
        print("broadcasting progress", message)
        print("#" * 80)
        await SimpleWebSocketManager._broadcast(message)

    @staticmethod
    async def _broadcast(message: dict):
        """Internal method to broadcast to all connections"""
        if not active_connections:
            return

        message_json = json.dumps(message)
        dead_connections = []

        for connection_id, websocket in active_connections.items():
            try:
                await websocket.send_text(message_json)
            except Exception as e:
                logger.warning(f"Failed to send to connection {connection_id}: {e}")
                dead_connections.append(connection_id)

        # Clean up dead connections
        for connection_id in dead_connections:
            active_connections.pop(connection_id, None)
            active_log_streamers.discard(connection_id)

        # # Always sleep to avoid busy-waiting
        await asyncio.sleep(0)


# Global instance
websocket_manager = SimpleWebSocketManager()


async def tail_log_file_websocket(websocket: WebSocket, connection_id: str):
    """
    Tail the log file and send new lines via WebSocket.
    This runs independently and doesn't block other operations.
    """
    try:
        # Ensure log file exists
        if not LOG_FILE_PATH.exists():
            LOG_FILE_PATH.touch()

        # Open file and seek to end
        with open(LOG_FILE_PATH, "r", encoding="utf-8") as file:
            # Move to end of file
            file.seek(0, 2)

            # Send initial connection message
            initial_message = {
                "type": "log",
                "data": {"message": "Connected to log stream"},
                "timestamp": datetime.now().isoformat(),
            }
            await websocket.send_text(json.dumps(initial_message))

            while connection_id in active_log_streamers:
                line = file.readline()
                if line:
                    # Send log line via WebSocket
                    log_message = {
                        "type": "log",
                        "data": {"message": line.rstrip("\n\r")},
                        "timestamp": datetime.now().isoformat(),
                    }
                    await websocket.send_text(json.dumps(log_message))
                else:
                    # No new data, wait a bit before checking again
                    await asyncio.sleep(0.5)

    except Exception as e:
        logger.error(f"Error in WebSocket log tail for {connection_id}: {e}")
        try:
            error_message = {
                "type": "log_error",
                "data": {"error": f"Error reading log file: {e}"},
                "timestamp": datetime.now().isoformat(),
            }
            await websocket.send_text(json.dumps(error_message))
        except:
            pass  # Connection might be closed


@router.websocket("/connect")
async def websocket_endpoint(websocket: WebSocket):
    """
    Main WebSocket endpoint for real-time communication.
    Handles execution notifications and log streaming.
    """
    await websocket.accept()
    connection_id = str(uuid.uuid4())

    # Register this connection
    active_connections[connection_id] = websocket
    logger.info(f"WebSocket connected: {connection_id}")

    # Start log streaming in background
    active_log_streamers.add(connection_id)
    log_task = asyncio.create_task(tail_log_file_websocket(websocket, connection_id))

    try:
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages from client (like ping/pong)
                message = await websocket.receive_text()

                # Handle client messages
                if message == "ping":
                    pong_response = {
                        "type": "pong",
                        "timestamp": datetime.now().isoformat(),
                    }
                    await websocket.send_text(json.dumps(pong_response))

            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(
                    f"Error handling WebSocket message from {connection_id}: {e}"
                )
                break

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket error for {connection_id}: {e}")
    finally:
        # Clean up
        active_log_streamers.discard(connection_id)
        active_connections.pop(connection_id, None)

        # Cancel log streaming task
        if not log_task.done():
            log_task.cancel()
            try:
                await log_task
            except asyncio.CancelledError:
                pass

        logger.info(f"WebSocket cleanup completed for {connection_id}")


@router.websocket("/logs-only")
async def websocket_logs_only_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint specifically for log streaming only.
    This is simpler and focused only on logs.
    """
    await websocket.accept()
    connection_id = str(uuid.uuid4())

    # Register this connection
    active_connections[connection_id] = websocket
    active_log_streamers.add(connection_id)

    try:
        # Start log streaming
        log_task = asyncio.create_task(
            tail_log_file_websocket(websocket, connection_id)
        )

        # Keep connection alive
        while True:
            await asyncio.sleep(1)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket logs-only error for {connection_id}: {e}")
    finally:
        active_log_streamers.discard(connection_id)
        active_connections.pop(connection_id, None)
