"""
Test workflow execution using the steps API

This test simulates how the frontend interacts with the backend API to execute
a complete workflow including text processing and audio generation.
"""

import os
import sys
import pytest
import shutil
import asyncio
import json
import websockets
import uvicorn
import threading
import time
import requests
from pathlib import Path

from backend.core.router_steps import StepExecutionRequest

# Add the backend directory to the path so we can import modules
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from backend.core.main import app

# Use the test audio file as voice clone source
test_audio_path = "backend/core/tests/files/scarhand4200_41-laserapuntando.wav"


class WebSocketTestClient:
    """WebSocket client for testing async execution results"""

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
        # Clear any pending executions
        self.pending_executions.clear()

    async def _listen_for_messages(self):
        """Listen for WebSocket messages and resolve pending executions"""
        try:
            async for message in self.websocket:
                data = json.loads(message)

                if data.get("type") == "execution_complete":
                    execution_id = data.get("execution_id")
                    if execution_id in self.pending_executions:
                        self.pending_executions[execution_id]["result"] = data.get(
                            "result"
                        )
                        self.pending_executions[execution_id]["event"].set()

                elif data.get("type") == "execution_error":
                    execution_id = data.get("execution_id")
                    if execution_id in self.pending_executions:
                        self.pending_executions[execution_id]["error"] = data.get(
                            "error"
                        )
                        self.pending_executions[execution_id]["event"].set()

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
        }

        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
            execution_data = self.pending_executions[execution_id]

            if execution_data["error"]:
                raise Exception(execution_data["error"])
            return execution_data["result"]

        except asyncio.TimeoutError:
            raise Exception(
                f"Execution {execution_id} timed out after {timeout} seconds"
            )
        finally:
            self.pending_executions.pop(execution_id, None)


class BackgroundTestServer:
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
                response = requests.get(f"http://localhost:{self.port}/api/steps/")
                if response.status_code == 200:
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
            # Give the server time to shutdown gracefully
            if self.server_thread and self.server_thread.is_alive():
                self.server_thread.join(timeout=2)


@pytest.mark.asyncio
class TestWorkflowExecution:
    """Test class for workflow execution"""

    @classmethod
    def setup_class(cls):
        """Set up test server and clients"""
        cls.test_server = BackgroundTestServer()
        cls.test_server.start()
        cls.base_url = f"http://localhost:{cls.test_server.port}"

    @classmethod
    def teardown_class(cls):
        """Clean up test server"""
        if cls.test_server:
            cls.test_server.stop()

    async def _get_ws_client(self):
        """Helper to create and connect WebSocket client"""
        ws_client = WebSocketTestClient(
            f"ws://localhost:{self.test_server.port}/ws/connect"
        )
        await ws_client.connect()
        return ws_client

    async def test_get_available_steps(self):
        """Test that we can retrieve available steps"""
        response = requests.get(f"{self.base_url}/api/steps/")
        assert response.status_code == 200

        steps = response.json()
        assert isinstance(steps, list)
        assert len(steps) > 0

        # Check that we have some expected steps
        step_names = [step.get("name") for step in steps]
        assert "generate_chatterbox_audio" in step_names

        for step in steps:
            assert (
                "step_type" in step
            ), f"Step '{step.get('name')}' missing step_type field"
            assert step["step_type"] in [
                "start_step",
                "pre_generation_step",
                "generation_step",
                "post_generation_step",
            ], f"Step '{step.get('name')}' has invalid step_type: {step['step_type']}"

        step_info = {
            step["name"]: {
                "step_type": step["step_type"],
            }
            for step in steps
        }

        # Start steps
        assert (
            step_info.get("set_chatterbox_params", {}).get("step_type") == "start_step"
        )
        assert step_info.get("set_dia_params", {}).get("step_type") == "start_step"

        # Generation steps
        assert (
            step_info.get("generate_chatterbox_audio", {}).get("step_type")
            == "generation_step"
        )
        assert (
            step_info.get("generate_dia_audio", {}).get("step_type")
            == "generation_step"
        )

        # Pre-generation steps that don't map over texts
        assert step_info.get("set_seed", {}).get("step_type") == "pre_generation_step"

        # Post-generation steps
        assert (
            step_info.get("export_audio", {}).get("step_type") == "post_generation_step"
        )

        print(f"Found {len(steps)} available steps: {step_names}")
        print(f"Step metadata verified: {step_info}")

    async def test_simple_text_processing_workflow(self):
        """Test a simple text processing workflow without audio generation"""
        ws_client = await self._get_ws_client()
        try:
            test_text = (
                "Hello world. This is a test.     "  # intentional extra whitespace.
            )

            workflow_request = StepExecutionRequest(
                texts=[test_text],
                voice_clone_paths=[test_audio_path],
                audio_transcriptions=["test"],
                output_file_name="test",
                output_subfolder="test_output",
                steps=[
                    "set_chatterbox_params",
                    "remove_extra_spaces",
                    "to_lowercase",
                ],
                parameters={},
            )

            response = requests.post(
                f"{self.base_url}/api/steps/execute-background",
                json=workflow_request.model_dump(),
            )
            assert response.status_code == 200

            response_data = response.json()
            execution_id = response_data["execution_id"]

            result = await ws_client.wait_for_execution(execution_id)
            # Assert that the input was split into sentences and lowercased
        finally:
            await ws_client.disconnect()

    async def test_voice_clone_workflow(self):
        """Test workflow with voice cloning using test audio file"""
        ws_client = await self._get_ws_client()
        try:
            test_text = "Testing voice cloning functionality."

            assert os.path.exists(test_audio_path)

            workflow_request = StepExecutionRequest(
                texts=[test_text],
                voice_clone_paths=[test_audio_path],
                audio_transcriptions=["test"],
                output_file_name="chatterbox_test",
                output_subfolder="test_output",
                steps=[
                    "set_chatterbox_params",
                    "remove_extra_spaces",
                    "set_num_candidates",
                    "set_seed",
                    "generate_chatterbox_audio",
                    "export_audio",
                ],
                parameters={
                    "num_candidates": 2,
                    "seed": 42,
                    "exaggeration": 0.6,
                    "temperature": 0.8,
                },
            )

            response = requests.post(
                f"{self.base_url}/api/steps/execute-background",
                json=workflow_request.model_dump(),
            )
            assert response.status_code == 200

            response_data = response.json()
            execution_id = response_data["execution_id"]

            result = await ws_client.wait_for_execution(execution_id)
            print(result)

            print("Voice clone workflow executed successfully")
        finally:
            await ws_client.disconnect()

    async def test_parameter_persistence(self):
        """Test that parameters are correctly set and persist through the workflow"""
        ws_client = await self._get_ws_client()
        try:
            test_text = "Parameter persistence test."

            workflow_request = StepExecutionRequest(
                texts=[test_text],
                voice_clone_paths=[test_audio_path],
                audio_transcriptions=["test"],
                output_file_name="test",
                output_subfolder="test_output",
                steps=[
                    "set_chatterbox_params",
                    "set_seed",
                    "set_num_candidates",
                    "set_parallel_processing",
                ],
                parameters={
                    "seed": 999,
                    "num_candidates": 5,
                    "enable_parallel": True,
                    "num_parallel_workers": 8,
                },
            )

            response = requests.post(
                f"{self.base_url}/api/steps/execute-background",
                json=workflow_request.model_dump(),
            )
            assert response.status_code == 200

            response_data = response.json()
            execution_id = response_data["execution_id"]

            result = await ws_client.wait_for_execution(execution_id)
            params = result["parameters"]

            # Check that all parameters were set correctly
            assert params["seed"] == 999
            assert params["num_candidates"] == 5
            assert params["enable_parallel"] is True
            assert params["num_parallel_workers"] == 8

            print("Parameter persistence test passed")
        finally:
            await ws_client.disconnect()

    async def test_dia_multi_speaker_workflow(self):
        """Test DIA multi-speaker dialogue generation workflow"""
        ws_client = await self._get_ws_client()
        try:
            test_texts = [
                "Hello!",
                "Oh hi there.",
                "How's your day going?",
                "Good, let me introduce you to my husband.",
                "Nice to meet you!",
            ]
            # Voice clone paths that will automatically generate speaker mapping [0, 1, 0, 1, 2]
            test_voice_clone_paths = [
                "backend/core/tests/files/scarhand4200_41-laserapuntando.wav",  # Speaker 0
                "backend/core/tests/files/voice_2.wav",  # Speaker 1
                "backend/core/tests/files/scarhand4200_41-laserapuntando.wav",  # Speaker 0 (same as index 0)
                "backend/core/tests/files/voice_2.wav",  # Speaker 1 (same as index 1)
                "backend/core/tests/files/voice_3.wav",  # Speaker 2
            ]
            test_audio_transcriptions = [
                "I'm gonna make him an offer he can't refuse.",
                "Life is like a box of chocolates.",
                "I'm gonna make him an offer he can't refuse.",
                "Life is like a box of chocolates.",
                "Houston, we have a problem.",
            ]

            workflow_request = StepExecutionRequest(
                texts=test_texts,
                voice_clone_paths=test_voice_clone_paths,
                audio_transcriptions=test_audio_transcriptions,
                output_subfolder="test_output",
                output_file_name="dia_test",
                steps=[
                    "set_dia_params",
                    "set_num_candidates",
                    "generate_dia_audio",
                    "export_audio",
                ],
                parameters={
                    "num_candidates": 1,
                    "max_new_tokens": 256,
                    "temperature": 1.0,
                },
            )

            response = requests.post(
                f"{self.base_url}/api/steps/execute-background",
                json=workflow_request.model_dump(),
            )
            assert response.status_code == 200

            response_data = response.json()
            execution_id = response_data["execution_id"]

            result = await ws_client.wait_for_execution(execution_id)
            print(result)
            assert result["multiple_speaker_text_array"] == test_texts
            assert len(result["step_results"]) == 4

            # Check that files were exported
            assert len(result["output_files"]) > 0
            assert result["output_files"][0] == "output/test_output/dia_test.wav"

            print(
                f"DIA multi-speaker workflow completed successfully. Output files: {result['output_files']}"
            )
        finally:
            await ws_client.disconnect()

    async def test_error_handling_missing_step(self):
        """Test error handling for missing steps"""
        ws_client = await self._get_ws_client()
        try:
            workflow_request = StepExecutionRequest(
                texts=["test"],
                voice_clone_paths=[test_audio_path],
                audio_transcriptions=["test"],
                output_file_name="test",
                output_subfolder="test_output",
                steps=["nonexistent-step"],
                parameters={},
            )

            response = requests.post(
                f"{self.base_url}/api/steps/execute-background",
                json=workflow_request.model_dump(),
            )
            assert response.status_code == 200

            response_data = response.json()
            execution_id = response_data["execution_id"]

            # Should get an error via WebSocket
            with pytest.raises(Exception) as exc_info:
                await ws_client.wait_for_execution(execution_id)

            assert "not found" in str(exc_info.value).lower()

            print("Error handling for missing steps works correctly")
        finally:
            await ws_client.disconnect()

    async def test_error_handling_dia_but_single_speaker(self):
        """Test error handling for missing steps"""
        ws_client = await self._get_ws_client()
        try:
            workflow_request = StepExecutionRequest(
                texts=["test"],
                voice_clone_paths=[test_audio_path],
                audio_transcriptions=["test"],
                output_file_name="test",
                output_subfolder="test_output",
                steps=["generate_dia_audio"],
                parameters={},
            )

            response = requests.post(
                f"{self.base_url}/api/steps/execute-background",
                json=workflow_request.model_dump(),
            )
            assert response.status_code == 200

            response_data = response.json()
            execution_id = response_data["execution_id"]
            with pytest.raises(Exception) as exc_info:
                await ws_client.wait_for_execution(execution_id)
            assert "multi-speaker" in str(exc_info.value).lower()

            print("Error handling for missing steps works correctly")
        finally:
            await ws_client.disconnect()

    async def test_empty_steps_workflow(self):
        """Test error handling for empty steps list"""
        workflow_request = StepExecutionRequest(
            texts=["test"],
            voice_clone_paths=[test_audio_path],
            audio_transcriptions=["test"],
            output_file_name="test",
            output_subfolder="test_output",
            steps=[],
            parameters={},
        )

        response = requests.post(
            f"{self.base_url}/api/steps/execute-background",
            json=workflow_request.model_dump(),
        )
        assert response.status_code == 400
        assert "no steps" in response.json()["detail"].lower()

        print("Error handling for empty steps works correctly")

    async def test_candidate_generation_with_failures(self):
        """Test workflow where some candidates fail to generate and errors should be reported"""
        ws_client = await self._get_ws_client()

        # Track all WebSocket messages to verify error reporting
        received_messages = []

        # Override the message listener to capture all messages
        original_listen = ws_client._listen_for_messages

        async def capture_messages():
            try:
                async for message in ws_client.websocket:
                    data = json.loads(message)
                    received_messages.append(data)

                    # Still handle execution completion/error as before
                    if data.get("type") == "execution_complete":
                        execution_id = data.get("execution_id")
                        if execution_id in ws_client.pending_executions:
                            ws_client.pending_executions[execution_id]["result"] = (
                                data.get("result")
                            )
                            ws_client.pending_executions[execution_id]["event"].set()
                    elif data.get("type") == "execution_error":
                        execution_id = data.get("execution_id")
                        if execution_id in ws_client.pending_executions:
                            ws_client.pending_executions[execution_id]["error"] = (
                                data.get("error")
                            )
                            ws_client.pending_executions[execution_id]["event"].set()
            except asyncio.CancelledError:
                pass
            except Exception as e:
                print(f"WebSocket listening error: {e}")

        # Replace the listening task
        if ws_client.listening_task:
            ws_client.listening_task.cancel()
            try:
                await ws_client.listening_task
            except asyncio.CancelledError:
                pass
        ws_client.listening_task = asyncio.create_task(capture_messages())

        try:
            # Create a workflow that's likely to have some failure scenarios
            # Use a large number of candidates to increase chance of failures
            test_text = "Test candidate generation with potential failures."

            workflow_request = StepExecutionRequest(
                texts=[test_text],
                output_file_name="test",
                output_subfolder="test_output",
                steps=[
                    "set_chatterbox_params",
                    "set_num_candidates",
                    "generate_chatterbox_audio",
                ],
                parameters={
                    "num_candidates": 5,  # More candidates = more chance for individual failures
                },
                voice_clone_paths=[test_audio_path],
                audio_transcriptions=["test"],
            )

            response = requests.post(
                f"{self.base_url}/api/steps/execute-background",
                json=workflow_request.model_dump(),
            )
            assert response.status_code == 200

            response_data = response.json()
            execution_id = response_data["execution_id"]

            result = await ws_client.wait_for_execution(execution_id)

            # Print captured messages for debugging
            print("Captured WebSocket messages:")
            for i, msg in enumerate(received_messages):
                print(
                    f"  {i}: {msg.get('type', 'unknown')} - {msg.get('step_name', '')} - {msg.get('message', msg.get('error', ''))}"
                )

            # The workflow should complete, but we want to test that individual candidate
            # failures would be reported if they occurred
            assert result is not None

            # Look for any candidate error messages (this will fail until we implement error reporting)
            candidate_error_messages = [
                msg for msg in received_messages if msg.get("type") == "candidate_error"
            ]

            # Currently this will be 0 because we haven't implemented candidate error reporting yet
            print(f"Found {len(candidate_error_messages)} candidate error messages")

            print(
                "Candidate generation failure test completed - error reporting mechanism needed"
            )

        finally:
            await ws_client.disconnect()

    async def test_higgs_text_normalization_workflow(self):
        """Test Higgs workflow with Chinese punctuation and text normalization steps"""
        ws_client = await self._get_ws_client()
        try:
            # Test text with Chinese punctuation and elements that need Higgs normalization
            test_text = "你好，世界！这是一个测试。Temperature is 25°C (77°F) today. [laugh] That's funny! (parentheses should be removed)"

            workflow_request = StepExecutionRequest(
                texts=[test_text],
                output_file_name="higgs_normalization_test",
                output_subfolder="test_output",
                steps=[
                    "set_higgs_singlespeaker_params",
                    "normalize_chinese_punctuation",
                    "normalize_text_for_higgs",
                    "generate_higgs_audio",
                    "normalize_audio",
                    "export_audio",
                ],
                parameters={},
                voice_clone_paths=[test_audio_path],
                audio_transcriptions=["test"],
            )

            response = requests.post(
                f"{self.base_url}/api/steps/execute-background",
                json=workflow_request.model_dump(),
            )
            assert response.status_code == 200

            response_data = response.json()
            execution_id = response_data["execution_id"]

            result = await ws_client.wait_for_execution(execution_id)

            # Verify the text was processed correctly
            processed_text = result["multiple_speaker_text_array"][0]

            print(f"Processed text: {processed_text}")
            # Check Chinese punctuation normalization
            assert "，" not in processed_text  # Chinese comma should be converted
            assert "。" not in processed_text  # Chinese period should be converted
            assert "！" not in processed_text  # Chinese exclamation should be converted

            # Check Higgs-specific normalizations
            assert "(" not in processed_text  # Parentheses should be removed
            assert ")" not in processed_text  # Parentheses should be removed
            assert "degrees Celsius" in processed_text  # °C should be converted
            assert "degrees Fahrenheit" in processed_text  # °F should be converted
            assert (
                "<SE>[Laughter]</SE>" in processed_text
            )  # [laugh] should be converted

            # Check that text ends with proper punctuation
            assert processed_text.endswith(
                (".", "!", "?", ",", ";", '"', "'", "</SE_e>", "</SE>")
            )

            print(f"Original text: {test_text}")
            print(f"Processed text: {processed_text}")
            print("Higgs text normalization workflow completed successfully")

        finally:
            await ws_client.disconnect()

    async def test_higgs_single_speaker_workflow(self):
        """Test complete Higgs single-speaker workflow including text normalization"""
        ws_client = await self._get_ws_client()
        try:
            # Test text with mixed content requiring normalization
            test_text = "Hello world！This is a test with Chinese punctuation， and some [laugh] audio tags."

            assert os.path.exists(test_audio_path)

            workflow_request = StepExecutionRequest(
                texts=[test_text],
                output_file_name="higgs_single_speaker_test",
                output_subfolder="test_output",
                steps=[
                    "set_higgs_singlespeaker_params",
                    "set_seed",
                    "remove_extra_spaces",
                    "fix_dot_letters",
                    "normalize_chinese_punctuation",
                    "normalize_text_for_higgs",
                    "generate_higgs_audio",
                    "normalize_audio",
                    "export_audio",
                ],
                parameters={
                    "seed": 42,
                    "transcription": "Test transcription for voice cloning",
                    "scene_prompt": "Audio is recorded from a quiet room.",
                    "max_new_tokens": 512,
                    "temperature": 0.3,
                },
                voice_clone_paths=[test_audio_path],
                audio_transcriptions=["test"],
            )

            response = requests.post(
                f"{self.base_url}/api/steps/execute-background",
                json=workflow_request.model_dump(),
            )
            assert response.status_code == 200

            response_data = response.json()
            execution_id = response_data["execution_id"]

            result = await ws_client.wait_for_execution(execution_id, timeout=60)

            # Verify workflow completed successfully
            assert result is not None
            assert len(result["step_results"]) == 9  # All 9 steps executed

            # Check that text normalization steps ran
            step_names = [step["step_name"] for step in result["step_results"]]
            assert "normalize_chinese_punctuation" in step_names
            assert "normalize_text_for_higgs" in step_names
            assert "generate_higgs_audio" in step_names

            # Check output files were created
            assert len(result["output_files"]) > 0
            assert result["output_files"][0].endswith(".wav")

            print(f"Higgs single-speaker workflow completed successfully")
            print(f"Steps executed: {step_names}")
            print(f"Output files: {result['output_files']}")

        finally:
            await ws_client.disconnect()


if __name__ == "__main__":
    # Run tests directly if script is called
    pytest.main([__file__, "-v"])
