#!/usr/bin/env python3
"""
Mock AI Model Service

A FastAPI service that fakes AI model endpoints without requiring VRAM.
- Single-speaker TTS: copies input voice file to output
- Multi-speaker dialogue: concatenates all voice files
- Follows standard API but uses no actual AI models
"""

import gc
import logging
import os
import shutil
import time
from typing import Dict, List, Optional, Any
from urllib.parse import unquote

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Import shared models
import sys
import os

project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.append(project_root)
print(f"Current working directory: {os.getcwd()}")

from backend.core.utils.file_utils import concatenate_audio_files
from models.shared_models import (
    DialogueInput,
    TextToSpeechRequest,
    TextToDialogueRequest,
    GenerationResponse,
    LoadModelResponse,
    UnloadModelResponse,
    ServiceInfoResponse,
    OpenAIModel,
    OpenAIModelsResponse,
)

from backend.core.utils.url_utils import decode_filepath_from_url

try:
    import librosa
    import soundfile as sf
    import numpy as np

    AUDIO_LIBS_AVAILABLE = True
except ImportError as e:
    print(f"Error importing audio dependencies: {e}")
    AUDIO_LIBS_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Mock AI Model Service", version="1.0.0")


from models.model_shared_utils import resolve_file_path


def simulate_processing_delay(parameters: Dict[str, Any], base_delay: float = 2.0):
    logger.info(f"Simulating processing delay: {base_delay:.2f}s")
    time.sleep(base_delay)


MODEL_NAME = "Mock Service"


# API Endpoints
@app.get("/", response_model=ServiceInfoResponse)
async def root():
    return ServiceInfoResponse(message=MODEL_NAME, model="mock-testing-service")


@app.post("/v1/text-to-speech/{voice_id}", response_model=GenerationResponse)
async def text_to_speech(voice_id: str, request: TextToSpeechRequest):
    """Mock single-speaker TTS: copies input voice file to output location."""
    try:
        # Decode URL-encoded voice_id (filepath)
        voice_path = decode_filepath_from_url(voice_id)
        output_path = request.output_filepath

        logger.info(f"Mock TTS: {voice_path} -> {output_path}")
        logger.info(f"Text: {request.text}")

        # Resolve and check if voice file exists
        resolved_voice_path = resolve_file_path(voice_path, project_root)
        if not os.path.exists(resolved_voice_path):
            raise HTTPException(
                status_code=400,
                detail=f"Voice file not found: {voice_path} (resolved: {resolved_voice_path})",
            )

        # Simulate processing delay
        simulate_processing_delay(request.parameters)

        # Create output directory if needed
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Copy voice file to output location
        shutil.copy2(resolved_voice_path, output_path)

        logger.info(f"Mock TTS completed: {output_path}")
        return GenerationResponse(
            status="success",
            output_filepath=output_path,
            message="Mock TTS generation completed (copied voice file)",
        )

    except Exception as e:
        logger.error(f"Error in mock TTS: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/text-to-dialogue", response_model=GenerationResponse)
async def text_to_dialogue(request: TextToDialogueRequest):
    """Mock multi-speaker dialogue: concatenates all voice files."""
    try:
        print("request", request)

        # Extract and resolve voice paths
        voice_paths = [
            resolve_file_path(decode_filepath_from_url(inp.voice_id), project_root)
            for inp in request.inputs
        ]
        output_path = request.output_filepath

        logger.info(f"Mock Dialogue: {len(voice_paths)} voices -> {output_path}")
        for i, inp in enumerate(request.inputs):
            logger.info(f"  {i+1}: {inp.text} (voice: {voice_paths[i]})")

        # Check if all voice files exist
        missing_files = [path for path in voice_paths if not os.path.exists(path)]
        if missing_files:
            raise HTTPException(
                status_code=400, detail=f"Voice files not found: {missing_files}"
            )

        # Simulate processing delay
        simulate_processing_delay(request.parameters)

        # Create output directory if needed
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Concatenate audio files
        if AUDIO_LIBS_AVAILABLE:
            concatenated_audio = concatenate_audio_files(voice_paths)

            if concatenated_audio is not None:
                # Save concatenated audio
                sf.write(output_path, concatenated_audio, 44100)
                logger.info(f"Mock dialogue completed: {output_path}")
                return GenerationResponse(
                    status="success",
                    output_filepath=output_path,
                    message=f"Mock dialogue generation completed (concatenated {len(voice_paths)} voices)",
                )
            else:
                raise Exception("Failed to concatenate audio files")
        else:
            # Fallback: just copy the first voice file
            shutil.copy2(voice_paths[0], output_path)
            logger.info(f"Mock dialogue completed (fallback): {output_path}")
            return GenerationResponse(
                status="success",
                output_filepath=output_path,
                message="Mock dialogue generation completed (audio libs unavailable, used first voice)",
            )

    except Exception as e:
        logger.error(f"Error in mock dialogue: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/load-model", response_model=LoadModelResponse)
async def load_model():
    """Mock model loading (no-op)."""
    logger.info("Mock model load (no-op)")
    time.sleep(1.0)  # Simulate loading time
    return LoadModelResponse(
        status="success", message="Mock model loaded (no actual model)"
    )


@app.post("/v1/unload-model", response_model=UnloadModelResponse)
async def unload_model_endpoint():
    """Mock model unloading (no-op)."""
    logger.info("Mock model unload (no-op)")
    time.sleep(0.5)  # Simulate unloading time
    return UnloadModelResponse(
        status="success", message="Mock model unloaded (no actual model)"
    )


@app.get("/v1/models", response_model=OpenAIModelsResponse)
async def list_models():
    """OpenAI-compatible models endpoint with health data."""
    import time

    model_data = OpenAIModel(
        id=MODEL_NAME,
        created=int(time.time()),
        owned_by="custom",
        status="healthy",
        model_loaded=True,  # Always "loaded" since it's mock
        device="cpu",  # Mock service uses no GPU
        dependencies_available=AUDIO_LIBS_AVAILABLE,
    )

    return OpenAIModelsResponse(data=[model_data])


if __name__ == "__main__":
    import argparse
    import uvicorn

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Mock AI Model Service")
    parser.add_argument(
        "--fast-delay",
        action="store_true",
        help="Use fast delay (0.01s) instead of default 2.0s for testing",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=None,
        help="Custom base delay in seconds (overrides --fast-delay)",
    )

    args = parser.parse_args()

    # Set global base delay based on arguments
    if args.delay is not None:
        global_base_delay = args.delay
    elif args.fast_delay:
        global_base_delay = 0.01
    else:
        global_base_delay = 2.0

    logger.info(f"Starting mock service with base delay: {global_base_delay}s")

    # Patch the simulate_processing_delay function to use our global delay
    original_simulate_delay = simulate_processing_delay

    def patched_simulate_delay(parameters):
        return original_simulate_delay(parameters, global_base_delay)

    # Replace the function globally
    globals()["simulate_processing_delay"] = patched_simulate_delay

    uvicorn.run(app, host="0.0.0.0", port=8999)
