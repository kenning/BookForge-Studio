"""
Steps Router

Provides API endpoints for managing and executing modular processing steps.
Supports text, audio, and parameter processing steps for TTS pipeline.
"""

import os
import importlib.util
import inspect
import uuid
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import tempfile

from backend.core.utils.sentence_chunking import chunk_sentences


from backend.core.data_types.step_context import StepContext
from backend.core.router_websocket import websocket_manager

# Import logging utilities
from backend.core.utils.logger import (
    get_logger,
    log_api_request,
    log_error_with_context,
)

logger = get_logger(__name__)


class StepExecutionRequest(BaseModel):
    """Request model for executing steps on text input"""

    # Support both single text and multiple texts
    texts: Optional[List[str]] = None
    steps: List[str]  # List of step names to execute in order
    voice_clone_paths: List[str]
    audio_transcriptions: List[str]

    parameters: Optional[Dict[str, Any]] = {}  # Initial parameters to set

    output_subfolder: str = ""
    output_file_name: str = ""


class StepExecutionResponse(BaseModel):
    """Response model for step execution"""

    # Use clear, descriptive field names
    multiple_speaker_text_array: Optional[List[str]] = None  # Input texts
    output_files: List[str] = []
    parameters: Dict[str, Any] = {}
    step_results: List[Dict[str, Any]]  # Results from each step


router = APIRouter(prefix="/api/steps", tags=["steps"])

# Global storage for loaded steps
loaded_steps: Dict[str, Dict[str, Any]] = {}


def load_steps():
    """
    Dynamically load all steps from the steps directories.
    This function scans the backend/steps directory and models/*/steps directories,
    importing all Python files and extracting their metadata and process functions.
    """
    global loaded_steps
    loaded_steps = {}

    # Get the path to the backend and models directories
    current_file = Path(__file__)
    backend_dir = current_file.parent.parent

    # Collect all steps directories to scan
    steps_directories = []

    # Add backend/steps directory
    backend_steps_dir = backend_dir / "steps"
    if backend_steps_dir.exists():
        steps_directories.append(("backend", backend_steps_dir))
    else:
        print(f"Backend steps directory not found: {backend_steps_dir}")

    # Add models/*/steps directories
    models_dir = backend_dir / "models"
    if models_dir.exists():
        for model_folder in models_dir.iterdir():
            if model_folder.is_dir():
                model_steps_dir = model_folder / "steps"
                if model_steps_dir.exists():
                    steps_directories.append(
                        (f"models/{model_folder.name}", model_steps_dir)
                    )

    if not steps_directories:
        logger.warning("No steps directories found")
        return

    # Process each steps directory
    for source_name, steps_dir in steps_directories:
        logger.info(f"Loading steps from {source_name}: {steps_dir}")

        # Iterate through all Python files in the steps directory
        for step_file in steps_dir.glob("*.py"):
            if step_file.name.startswith("__"):
                continue  # Skip __init__.py and similar files

            try:
                # Load the module dynamically with unique module name
                module_name = f"step_{source_name.replace('/', '_')}_{step_file.stem}"
                spec = importlib.util.spec_from_file_location(module_name, step_file)
                if spec is None or spec.loader is None:
                    continue

                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Check if the module has the required components
                if not hasattr(module, "STEP_METADATA"):
                    logger.warning(f"{step_file.name} missing STEP_METADATA")
                    continue

                if not hasattr(module, "process"):
                    logger.warning(f"{step_file.name} missing process function")
                    continue

                # Validate the process function signature
                process_func = getattr(module, "process")
                if not callable(process_func):
                    logger.warning(f"{step_file.name} process is not callable")
                    continue

                # Store the step information
                metadata = getattr(module, "STEP_METADATA")
                step_name = metadata.get("name", step_file.stem)

                # Check for name conflicts and warn
                if step_name in loaded_steps:
                    logger.warning(
                        f"Step '{step_name}' already exists. Overwriting with version from {source_name}"
                    )

                loaded_steps[step_name] = {
                    "metadata": metadata,
                    "process": process_func,
                    "file_path": str(step_file),
                    "source": source_name,
                }

                logger.info(f"Loaded step: {step_name} from {source_name}")

            except Exception as e:
                log_error_with_context(
                    e, f"loading step {step_file.name} from {source_name}"
                )
                continue


# Load steps when the module is imported
load_steps()


@router.get("/", response_model=List[Dict[str, Any]])
async def get_steps():
    """
    Get a list of all available steps with their metadata.

    Returns:
        List of step metadata dictionaries
    """
    log_api_request("/api/steps/", "GET")

    steps_list = []
    for step_name, step_info in loaded_steps.items():
        step_data = step_info["metadata"].copy()
        step_data["file_path"] = step_info["file_path"]
        step_data["multi_speaker"] = step_info["metadata"].get("multi-speaker", False)
        steps_list.append(step_data)

    logger.info(f"Returning {len(steps_list)} available steps")
    return steps_list


async def _execute_steps_impl(
    execution_id: str,
    texts: List[str],
    steps: List[str],
    output_file_name: str,
    output_subfolder: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None,
    voice_clone_paths: Optional[List[str]] = None,
    audio_transcriptions: Optional[List[str]] = None,
):
    """
    Internal implementation of step execution.
    """
    try:
        # Validate that all requested steps exist
        missing_steps = [step for step in steps if step not in loaded_steps]
        if missing_steps:
            error_msg = f"Steps not found: {', '.join(missing_steps)}"
            await websocket_manager.broadcast_execution_error(
                execution_id, error_msg, output_subfolder
            )
            return

        # Create context using the factory method
        context = StepContext.from_request_parameters(
            texts=texts,
            output_subfolder=output_subfolder,
            output_file_name=output_file_name,
            parameters=parameters,
            voice_clone_paths=voice_clone_paths,
            audio_transcriptions=audio_transcriptions,
            execution_id=execution_id,
        )

        step_results = []

        # Set step metadata on context
        if len(steps) > 0:
            first_step_info = loaded_steps[steps[0]]
            context.is_multi_speaker = first_step_info["metadata"].get(
                "multi-speaker", False
            )

        logger.info(
            f"Starting background execution {execution_id} of {len(steps)} steps: {steps}"
        )

        # Pre-chunk just to determine total num steps
        total_steps = len(steps) + (
            len(
                chunk_sentences(
                    texts,
                    voice_clone_paths,
                    audio_transcriptions,
                    context.approximate_min_chunk_length or 20,
                )
            )
            * context.num_candidates
        )

        # Save these just for execution progress notifications
        context.parameters["step_index"] = 0
        context.parameters["execution_id"] = execution_id
        context.parameters["total_steps"] = total_steps

        # Execute steps in sequence
        for _, step_name in enumerate(steps):
            try:
                context.parameters["step_index"] += 1
                # Send progress update
                await websocket_manager.broadcast_execution_progress(
                    execution_id,
                    step_name,
                    context.parameters["step_index"],
                    total_steps,
                    output_subfolder,
                )

                logger.info(
                    f"Background execution {execution_id}: Executing step {step_name}"
                )
                step_info = loaded_steps[step_name]
                process_func = step_info["process"]

                await process_func(context)
                await asyncio.sleep(0.0)

                # Capture step result
                step_result = {
                    "step_name": step_name,
                    "metadata": step_info["metadata"],
                    "multiple_speaker_text_array": context.multiple_speaker_text_array,
                    "has_audio": context.current_audio is not None,
                    "parameters_set": list(context.parameters.keys()),
                    "output_files": context.output_files.copy(),
                }
                step_results.append(step_result)

                logger.info(
                    f"Background execution {execution_id}: Step {step_name} completed"
                )

            except Exception as e:
                error_msg = f"Error executing step '{step_name}': {str(e)}"
                logger.error(f"Background execution {execution_id}: {error_msg}")
                await websocket_manager.broadcast_execution_error(
                    execution_id, error_msg, output_subfolder
                )
                return

        # Prepare final result
        all_parameters = context.parameters.copy()
        typed_fields = StepContext.model_fields.keys()
        for field in typed_fields:
            if field not in [
                "multiple_speaker_text_array",
                "current_audio",
                "audio_sample_rate",
                "temp_dir",
                "output_files",
                "execution_id",
            ]:
                all_parameters[field] = getattr(context, field)

        final_result = {
            "multiple_speaker_text_array": context.multiple_speaker_text_array,
            "output_files": context.output_files,
            "parameters": all_parameters,
            "step_results": step_results,
            "debug_chunks": context.debug_chunks,
            "debug_chunk_help_text": context.debug_chunk_help_text,
        }

        # Broadcast completion
        await websocket_manager.broadcast_execution_complete(
            execution_id, final_result, output_subfolder
        )

        # Send final progress update
        await websocket_manager.broadcast_execution_progress(
            execution_id,
            "Complete",
            total_steps,
            total_steps,
            output_subfolder,
        )

        logger.info(f"Background execution {execution_id} completed successfully")

    except Exception as e:
        error_msg = f"Unexpected error in background execution: {str(e)}"
        logger.error(f"Background execution {execution_id}: {error_msg}")
        await websocket_manager.broadcast_execution_error(
            execution_id, error_msg, output_subfolder
        )


async def execute_steps_async(
    execution_id: str,
    texts: List[str],
    steps: List[str],
    output_file_name: str,
    output_subfolder: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None,
    voice_clone_paths: Optional[List[str]] = None,
    audio_transcriptions: Optional[List[str]] = None,
):
    """
    Execute steps asynchronously and notify via WebSocket when complete.
    """

    await _execute_steps_impl(
        execution_id,
        texts,
        steps,
        output_file_name,
        output_subfolder,
        parameters,
        voice_clone_paths,
        audio_transcriptions,
    )


@router.post("/execute-background", response_model=Dict[str, str])
async def execute_steps_background(request: StepExecutionRequest):
    """
    Execute a sequence of steps in the background and return an execution ID for monitoring.

    Args:
        request: Contains the text input and list of step names to execute

    Returns:
        Response containing execution ID for monitoring progress via WebSocket
    """
    log_api_request(
        "/api/steps/execute-background",
        "POST",
        {
            "steps": request.steps,
            "num_texts": len(request.texts) if request.texts else 0,
            "num_voice_clones": (
                len(request.voice_clone_paths) if request.voice_clone_paths else 0
            ),
        },
    )

    if not request.steps:
        raise HTTPException(status_code=400, detail="No steps provided")

    if not request.texts:
        raise HTTPException(status_code=400, detail="'texts' must be provided")

    # Generate execution ID
    execution_id = str(uuid.uuid4())

    print("#" * 80)
    print("request", request)
    print("#" * 80)
    # Start the background task
    asyncio.create_task(
        execute_steps_async(
            execution_id=execution_id,
            texts=request.texts,
            steps=request.steps,
            output_subfolder=request.output_subfolder,
            output_file_name=request.output_file_name,
            parameters=request.parameters,
            voice_clone_paths=request.voice_clone_paths,
            audio_transcriptions=request.audio_transcriptions,
        )
    )

    logger.info(f"Created background step execution {execution_id}")
    return {"execution_id": execution_id}


# Note: Could have this called in the frontend in the header of the steps sidebar thing
@router.post("/reload")
async def reload_steps():
    """
    Reload all steps from the steps directory.
    Useful for development when adding new steps without restarting the server.
    """
    log_api_request("/api/steps/reload", "POST")
    logger.info("Reloading all steps")

    load_steps()

    logger.info(f"Successfully reloaded {len(loaded_steps)} steps")
    return {"message": f"Reloaded {len(loaded_steps)} steps"}
