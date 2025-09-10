"""
WebSocket utilities for text workflows.

Provides functions to send progress updates, completion, and error events
via websocket with proper namespacing.
"""

import asyncio
from typing import Optional
from datetime import datetime

from backend.core.router_websocket import SimpleWebSocketManager


def truncate_message(message: str, max_length: int = 500) -> str:
    """Truncate a message to max_length characters, adding ellipsis if needed."""
    if len(message) <= max_length:
        return message
    return message[:max_length] + "..."


async def send_text_workflow_progress(
    step_num: int,
    total_steps: int,
    message: str,
    workflow_name: str,
    execution_id: Optional[str] = None,
):
    """Send a text-workflow-progress event via websocket."""
    try:

        # Truncate long messages
        truncated_message = truncate_message(message)

        print("Sending text-workflow-progress event")
        await SimpleWebSocketManager._broadcast(
            {
                "type": "text-workflow-progress",
                "workflow_name": workflow_name,
                "execution_id": execution_id,
                "step_num": step_num,
                "total_steps": total_steps,
                "message": truncated_message,
                "timestamp": datetime.now().isoformat(),
            }
        )
    except Exception as e:
        # Don't let websocket errors break the workflow
        print(f"Warning: Failed to send websocket progress: {e}")


async def send_text_workflow_complete(
    result_data: dict,
    workflow_name: str,
    execution_id: Optional[str] = None,
):
    """Send a text-workflow-complete event via websocket."""
    try:

        await SimpleWebSocketManager._broadcast(
            {
                "type": "text-workflow-complete",
                "workflow_name": workflow_name,
                "execution_id": execution_id,
                "result": result_data,
            }
        )
    except Exception as e:
        print(f"Warning: Failed to send websocket completion: {e}")


async def send_text_workflow_error(
    error_message: str,
    workflow_name: str,
    execution_id: Optional[str] = None,
):
    """Send a text-workflow-error event via websocket."""
    try:
        # Truncate long error messages
        truncated_error = truncate_message(error_message)

        await SimpleWebSocketManager._broadcast(
            {
                "type": "text-workflow-error",
                "workflow_name": workflow_name,
                "execution_id": execution_id,
                "error": truncated_error,
            }
        )

    except Exception as e:
        print(f"Warning: Failed to send websocket error: {e}")


def create_progress_reporter(workflow_name: str, execution_id: Optional[str] = None):
    """Create a progress reporting function for a specific workflow."""

    async def report_progress(step_num: int, total_steps: int, message: str):
        await send_text_workflow_progress(
            step_num, total_steps, message, workflow_name, execution_id
        )

    return report_progress
