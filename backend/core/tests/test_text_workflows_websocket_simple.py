"""
Simple test for text workflow websocket functionality

This test validates that websocket events are properly sent during text workflow execution
by checking that the websocket utility functions work correctly.
"""

import os
import sys
import pytest
import asyncio
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

# Add the backend directory to the path so we can import modules
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from backend.text_workflows.websocket_utils import (
    send_text_workflow_progress,
    send_text_workflow_complete,
    send_text_workflow_error,
)


class TestTextWorkflowWebSocketUtils:
    """Test websocket utility functions"""

    @pytest.mark.asyncio
    async def test_send_text_workflow_progress(self):
        """Test sending progress messages"""
        with patch(
            "backend.core.router_websocket.SimpleWebSocketManager._broadcast"
        ) as mock_broadcast:
            await send_text_workflow_progress(
                step_num=2,
                total_steps=4,
                message="Processing text data",
                workflow_name="text_to_psss",
                execution_id="test-123",
            )

            # Verify _broadcast was called with correct parameters
            mock_broadcast.assert_called_once()
            call_args = mock_broadcast.call_args[0]

            data = call_args[0]
            assert data["type"] == "text-workflow-progress"
            assert data["step_num"] == 2
            assert data["total_steps"] == 4
            assert data["message"] == "Processing text data"
            assert data["workflow_name"] == "text_to_psss"
            assert data["execution_id"] == "test-123"

    @pytest.mark.asyncio
    async def test_send_text_workflow_complete(self):
        """Test sending completion messages"""
        with patch(
            "backend.core.router_websocket.SimpleWebSocketManager._broadcast"
        ) as mock_broadcast:
            test_result = {"script": {"type": "script", "history_grid": {"grid": []}}}

            await send_text_workflow_complete(
                result_data=test_result,
                workflow_name="csv_to_psss",
                execution_id="test-456",
            )

            # Verify _broadcast was called with correct parameters
            mock_broadcast.assert_called_once()
            call_args = mock_broadcast.call_args[0]

            data = call_args[0]
            assert data["type"] == "text-workflow-complete"
            assert data["result"] == test_result
            assert data["workflow_name"] == "csv_to_psss"
            assert data["execution_id"] == "test-456"

    @pytest.mark.asyncio
    async def test_send_text_workflow_error(self):
        """Test sending error messages"""
        with patch(
            "backend.core.router_websocket.SimpleWebSocketManager._broadcast"
        ) as mock_broadcast:
            await send_text_workflow_error(
                error_message="File not found",
                workflow_name="text_to_llm_api",
                execution_id="test-789",
            )

            # Verify _broadcast was called with correct parameters
            mock_broadcast.assert_called_once()
            call_args = mock_broadcast.call_args[0]

            data = call_args[0]
            assert data["type"] == "text-workflow-error"
            assert data["error"] == "File not found"
            assert data["workflow_name"] == "text_to_llm_api"
            assert data["execution_id"] == "test-789"

    @pytest.mark.asyncio
    async def test_message_truncation(self):
        """Test that long messages are properly truncated"""
        with patch(
            "backend.core.router_websocket.SimpleWebSocketManager._broadcast"
        ) as mock_broadcast:
            # Create a message longer than 500 characters
            long_message = "A" * 600

            await send_text_workflow_progress(
                step_num=1,
                total_steps=1,
                message=long_message,
                workflow_name="test_workflow",
            )

            # Verify message was truncated
            mock_broadcast.assert_called_once()
            call_args = mock_broadcast.call_args[0]
            data = call_args[0]

            assert len(data["message"]) == 503  # 500 + "..."
            assert data["message"].endswith("...")
            assert data["message"].startswith("A")

    @pytest.mark.asyncio
    async def test_optional_execution_id(self):
        """Test that execution_id is optional"""
        with patch(
            "backend.core.router_websocket.SimpleWebSocketManager._broadcast"
        ) as mock_broadcast:
            await send_text_workflow_progress(
                step_num=1,
                total_steps=1,
                message="Test message",
                workflow_name="test_workflow",
                # No execution_id provided
            )

            mock_broadcast.assert_called_once()
            call_args = mock_broadcast.call_args[0]
            data = call_args[0]

            assert data["execution_id"] is None

    @pytest.mark.asyncio
    async def test_websocket_message_timing_not_queued(self):
        """Test that websocket messages are sent immediately, not queued"""
        message_timestamps = []

        # Mock broadcast function that captures timestamps
        async def mock_broadcast(data):
            message_timestamps.append(time.time())
            # Simulate some small processing delay
            await asyncio.sleep(0.001)

        with patch(
            "backend.core.router_websocket.SimpleWebSocketManager._broadcast",
            side_effect=mock_broadcast,
        ):
            # Record start time
            start_time = time.time()

            # Send first progress message
            await send_text_workflow_progress(
                step_num=1,
                total_steps=3,
                message="Starting process",
                workflow_name="test_timing",
                execution_id="timing-test-123",
            )

            # Wait 0.2 seconds
            await asyncio.sleep(0.2)

            # Send second progress message
            await send_text_workflow_progress(
                step_num=2,
                total_steps=3,
                message="Processing data",
                workflow_name="test_timing",
                execution_id="timing-test-123",
            )

            # Wait another 0.2 seconds
            await asyncio.sleep(0.2)

            # Send completion message
            await send_text_workflow_complete(
                result_data={"status": "success"},
                workflow_name="test_timing",
                execution_id="timing-test-123",
            )

        # Verify we received exactly 3 messages
        assert (
            len(message_timestamps) == 3
        ), f"Expected 3 messages, got {len(message_timestamps)}"

        # Calculate time differences between messages
        time_diff_1_to_2 = message_timestamps[1] - message_timestamps[0]
        time_diff_2_to_3 = message_timestamps[2] - message_timestamps[1]

        print(f"Time between message 1 and 2: {time_diff_1_to_2:.3f}s")
        print(f"Time between message 2 and 3: {time_diff_2_to_3:.3f}s")

        # Verify messages were sent with proper timing (0.18-0.22 second intervals)
        # This proves they weren't queued up and sent all at once
        assert (
            0.18 <= time_diff_1_to_2 <= 0.22
        ), f"First interval should be ~0.2s, got {time_diff_1_to_2:.3f}s"
        assert (
            0.18 <= time_diff_2_to_3 <= 0.22
        ), f"Second interval should be ~0.2s, got {time_diff_2_to_3:.3f}s"

        # Verify total time is approximately 0.4 seconds (2 * 0.2s delays)
        total_time = message_timestamps[2] - message_timestamps[0]
        assert (
            0.38 <= total_time <= 0.42
        ), f"Total time should be ~0.4s, got {total_time:.3f}s"

        print(f"✓ WebSocket messages sent in real-time with proper timing")
        print(f"  - Total duration: {total_time:.3f}s")
        print(
            f"  - Message intervals: {time_diff_1_to_2:.3f}s, {time_diff_2_to_3:.3f}s"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
