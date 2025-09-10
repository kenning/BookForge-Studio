"""
Test text workflow execution using WebSocket background execution

This test simulates how the frontend should interact with text workflows via WebSocket,
similar to how the steps system works, replacing HTTP synchronous execution.
"""

import os
import sys
import pytest
import asyncio
import json
import websockets
import uvicorn
import threading
import time
import requests
from pathlib import Path

from backend.core.router_text_workflows import CsvToPsssRequest, TextToPsssRequest

# Add the backend directory to the path so we can import modules
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from backend.core.main import app


class TextWorkflowWebSocketTestClient:
    """WebSocket client for testing text workflow background execution"""

    def __init__(self, ws_url="ws://localhost:8001/ws/connect"):
        self.ws_url = ws_url
        self.websocket = None
        self.pending_executions = {}
        self.listening_task = None

    async def connect(self):
        """Connect to WebSocket"""
        self.websocket = await websockets.connect(self.ws_url)
        self.listening_task = asyncio.create_task(self._listen_for_messages())

    async def disconnect(self):
        """Disconnect from WebSocket"""
        if self.listening_task:
            self.listening_task.cancel()
            try:
                await self.listening_task
            except asyncio.CancelledError:
                pass
        if self.websocket:
            await self.websocket.close()

    async def _listen_for_messages(self):
        """Listen for WebSocket messages and resolve pending executions"""
        try:
            async for message in self.websocket:
                data = json.loads(message)

                if data.get("type") == "text-workflow-complete":
                    execution_id = data.get("execution_id")
                    if execution_id in self.pending_executions:
                        self.pending_executions[execution_id]["result"] = data.get(
                            "result"
                        )
                        self.pending_executions[execution_id]["event"].set()

                elif data.get("type") == "text-workflow-error":
                    execution_id = data.get("execution_id")
                    if execution_id in self.pending_executions:
                        self.pending_executions[execution_id]["error"] = data.get(
                            "error"
                        )
                        self.pending_executions[execution_id]["event"].set()

                elif data.get("type") == "text-workflow-progress":
                    # Just log progress messages for now
                    execution_id = data.get("execution_id")
                    if execution_id in self.pending_executions:
                        progress = self.pending_executions[execution_id].setdefault(
                            "progress", []
                        )
                        progress.append(
                            {
                                "step_num": data.get("step_num"),
                                "total_steps": data.get("total_steps"),
                                "message": data.get("message"),
                            }
                        )

        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"WebSocket listening error: {e}")

    async def wait_for_execution(self, execution_id, timeout=30):
        """Wait for execution to complete and return result or raise error"""
        event = asyncio.Event()
        self.pending_executions[execution_id] = {
            "event": event,
            "result": None,
            "error": None,
            "progress": [],
        }

        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
            execution_data = self.pending_executions[execution_id]

            if execution_data["error"]:
                raise Exception(execution_data["error"])
            return execution_data["result"], execution_data["progress"]

        except asyncio.TimeoutError:
            raise Exception(
                f"Text workflow execution {execution_id} timed out after {timeout} seconds"
            )
        finally:
            self.pending_executions.pop(execution_id, None)


class TestServer:
    """Test server manager for running FastAPI with WebSocket support"""

    def __init__(self, port=8001):
        self.port = port
        self.server_thread = None
        self.server = None

    def start(self):
        """Start the test server in a background thread"""

        def run_server():
            config = uvicorn.Config(
                app, host="127.0.0.1", port=self.port, log_level="warning"
            )
            self.server = uvicorn.Server(config)
            asyncio.run(self.server.serve())

        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()

        # Wait for server to start
        for _ in range(50):  # 5 second timeout
            try:
                response = requests.get(
                    f"http://localhost:{self.port}/api/text-workflows/csv-to-psss",
                    json={"filepath": "nonexistent.csv"},
                )
                # We expect this to fail, but if the server responds, it's up
                break
            except:
                pass
            time.sleep(0.1)
        else:
            raise Exception("Test server failed to start")

    def stop(self):
        """Stop the test server"""
        if self.server:
            self.server.should_exit = True


@pytest.mark.asyncio
class TestTextWorkflowWebSocketExecution:
    """Test class for text workflow WebSocket-based execution"""

    @classmethod
    def setup_class(cls):
        """Set up test server and clients"""
        cls.test_server = TestServer()
        cls.test_server.start()
        cls.base_url = f"http://localhost:{cls.test_server.port}"

    @classmethod
    def teardown_class(cls):
        """Clean up test server"""
        if cls.test_server:
            cls.test_server.stop()

    async def _get_ws_client(self):
        """Helper to create and connect WebSocket client"""
        ws_client = TextWorkflowWebSocketTestClient(
            f"ws://localhost:{self.test_server.port}/ws/connect"
        )
        await ws_client.connect()
        return ws_client

    async def test_csv_to_psss_websocket_execution(self):
        """Test CSV to PSSS workflow using WebSocket background execution"""
        ws_client = await self._get_ws_client()

        try:
            # Create test CSV file
            test_csv_content = """Text,Speaker
"It was a dark and stormy night in the countryside.","Narrator"
"Hello there, how are you doing today?","Mrs. Smith"
"I'm doing quite well, thank you for asking.","Mr. Jones"
"The conversation continued for several more minutes.","Narrator"
"""

            # Create the test directory structure
            test_dir = Path("files/input/test")
            test_dir.mkdir(parents=True, exist_ok=True)

            # Save the CSV content to a file
            test_file_path = test_dir / "testcsv_websocket.csv"
            with open(test_file_path, "w", encoding="utf-8") as f:
                f.write(test_csv_content)

            # Start background execution (this endpoint doesn't exist yet - need to create it)
            workflow_request: CsvToPsssRequest = CsvToPsssRequest(
                filepath="input/test/testcsv_websocket.csv"
            )

            response = requests.post(
                f"{self.base_url}/api/text-workflows/csv-to-psss",
                json=workflow_request.model_dump(),
            )

            assert response.status_code == 200

            response_data = response.json()
            execution_id = response_data["execution_id"]

            result, progress = await ws_client.wait_for_execution(execution_id)

            # Verify the script structure
            assert "script" in result
            script = result["script"]
            assert script["type"] == "script"
            assert "history_grid" in script
            assert len(script["history_grid"]["grid"]) == 4

            # Verify progress was reported
            assert len(progress) >= 1
            assert all("step_num" in p for p in progress)
            assert all("total_steps" in p for p in progress)
            assert all("message" in p for p in progress)

            print("CSV to PSSS WebSocket execution test passed")

        finally:
            await ws_client.disconnect()
            # Clean up test file
            if test_file_path.exists():
                test_file_path.unlink()

    async def test_text_to_psss_websocket_execution(self):
        """Test Text to PSSS workflow using WebSocket background execution"""
        ws_client = await self._get_ws_client()

        try:
            test_text = """Narrator: It was a dark and stormy night in the countryside.
Mrs. Smith: Hello there, how are you doing today?
Mr. Jones: I'm doing quite well, thank you for asking.
Narrator: The conversation continued for several more minutes."""

            # Start background execution
            workflow_request: TextToPsssRequest = TextToPsssRequest(text=test_text)

            response = requests.post(
                f"{self.base_url}/api/text-workflows/text-to-psss",
                json=workflow_request.model_dump(),
            )

            # This will fail until we implement the background execution endpoint
            assert response.status_code == 200

            response_data = response.json()
            execution_id = response_data["execution_id"]

            result, progress = await ws_client.wait_for_execution(execution_id)

            # Verify the script structure
            assert "script" in result
            script = result["script"]
            assert script["type"] == "script"
            assert "history_grid" in script
            assert len(script["history_grid"]["grid"]) == 4

            # Verify speaker mapping
            speaker_map = script["speaker_to_actor_map"]
            expected_speakers = {"Narrator", "Mrs. Smith", "Mr. Jones"}
            assert set(speaker_map.keys()) == expected_speakers

            # Verify progress was reported
            assert len(progress) >= 1

            print("Text to PSSS WebSocket execution test passed")

        finally:
            await ws_client.disconnect()

    async def test_websocket_error_handling(self):
        """Test error handling via WebSocket"""
        ws_client = await self._get_ws_client()

        try:
            # Try to process a non-existent file
            workflow_request: CsvToPsssRequest = CsvToPsssRequest(
                filepath="nonexistent.csv"
            )

            response = requests.post(
                f"{self.base_url}/api/text-workflows/csv-to-psss",
                json=workflow_request.model_dump(),
            )

            assert response.status_code == 200

            response_data = response.json()
            execution_id = response_data["execution_id"]

            # Should get an error via WebSocket
            with pytest.raises(Exception) as exc_info:
                await ws_client.wait_for_execution(execution_id)

            assert (
                "not found" in str(exc_info.value).lower()
                or "error" in str(exc_info.value).lower()
            )
            print("WebSocket error handling test passed")

        finally:
            await ws_client.disconnect()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
