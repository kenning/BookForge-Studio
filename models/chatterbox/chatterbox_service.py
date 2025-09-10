#!/usr/bin/env python3
"""
Chatterbox TTS Microservice

A FastAPI service for the Chatterbox TTS model that provides ElevenLabs-compatible endpoints.
Supports single-speaker TTS with voice cloning and advanced parameters.
"""

import gc
import logging
import os
import uuid
from typing import Dict, List, Optional, Any
from urllib.parse import unquote

import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Import shared models
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Add project root to path for imports
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.append(project_root)

from backend.core.utils.url_utils import decode_filepath_from_url
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

from model_shared_utils import resolve_file_path


try:
    from chatterbox_code.tts import ChatterboxTTS
    import torchaudio

    CHATTERBOX_AVAILABLE = True
except ImportError as e:
    print(f"Error importing Chatterbox dependencies: {e}")
    CHATTERBOX_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global model state
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
MODEL = None

app = FastAPI(title="Chatterbox TTS Service", version="1.0.0")


def get_or_load_model():
    """Load the Chatterbox model."""
    global MODEL

    if MODEL is None:
        if not CHATTERBOX_AVAILABLE:
            raise HTTPException(
                status_code=500, detail="Chatterbox dependencies not available"
            )

        logger.info("Loading Chatterbox TTS model...")
        MODEL = ChatterboxTTS.from_pretrained(DEVICE)
        if hasattr(MODEL, "to") and str(MODEL.device) != DEVICE:
            MODEL.to(DEVICE)
        logger.info(
            f"Chatterbox model loaded on device: {getattr(MODEL, 'device', 'unknown')}"
        )

    return MODEL


def unload_model():
    """Unload the model and free memory."""
    global MODEL

    if MODEL is not None:
        logger.info("Unloading Chatterbox model...")
        del MODEL
        MODEL = None

        # Force garbage collection
        gc.collect()

        # Clear CUDA cache if available
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        logger.info("Chatterbox model unloaded successfully")
        return True

    return False


MODEL_NAME = "Chatterbox"


# API Endpoints
@app.get("/", response_model=ServiceInfoResponse)
async def root():
    return ServiceInfoResponse(message=MODEL_NAME, model="ResembleAI/chatterbox")


@app.post("/v1/text-to-speech/{voice_id}", response_model=GenerationResponse)
async def text_to_speech(voice_id: str, request: TextToSpeechRequest):
    """Single-speaker text-to-speech generation using Chatterbox."""
    try:
        # Decode URL-encoded voice_id (filepath)
        voice_path = decode_filepath_from_url(voice_id)

        output_path = request.output_filepath

        logger.info(f"Chatterbox TTS: {voice_path} -> {output_path}")
        logger.info(f"Text: {request.text}")

        # Resolve and check if voice file exists
        resolved_voice_path = resolve_file_path(voice_path, project_root)
        if not os.path.exists(resolved_voice_path):
            raise HTTPException(
                status_code=400,
                detail=f"Voice file not found: {voice_path} (resolved: {resolved_voice_path})",
            )

        # Load model
        model = get_or_load_model()

        # Set seed if provided
        if "seed" in request.parameters:
            seed = request.parameters["seed"]
            torch.manual_seed(seed)
            if torch.cuda.is_available():
                torch.cuda.manual_seed(seed)

        # Prepare generation parameters
        gen_kwargs = {
            "exaggeration": request.parameters.get("exaggeration", 0.5),
            "temperature": request.parameters.get("temperature", 0.75),
            "cfg_weight": request.parameters.get("cfg_weight", 0.5),
            "disable_watermark": request.parameters.get("disable_watermark", False),
            "audio_prompt_path": resolved_voice_path,
        }

        # Create output directory if needed
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Generate audio
        wav = model.generate(request.text.strip(), **gen_kwargs)

        # Save audio
        torchaudio.save(output_path, wav, model.sr)

        logger.info(f"Chatterbox TTS completed: {output_path}")
        return GenerationResponse(
            status="success",
            output_filepath=output_path,
            message="Chatterbox TTS generation completed",
        )

    except Exception as e:
        logger.error(f"Error in Chatterbox TTS: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/text-to-dialogue", response_model=GenerationResponse)
async def text_to_dialogue(request: TextToDialogueRequest):
    """
    Multi-speaker dialogue generation.
    Note: Chatterbox is primarily single-speaker, so this concatenates individual TTS calls.
    """
    try:
        if len(request.inputs) < 1:
            raise HTTPException(status_code=400, detail="At least one input required")

        # Load model
        model = get_or_load_model()

        output_path = request.output_filepath

        # Create output directory if needed
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Set seed if provided
        if "seed" in request.parameters:
            seed = request.parameters["seed"]
            torch.manual_seed(seed)
            if torch.cuda.is_available():
                torch.cuda.manual_seed(seed)

        waveform_list = []

        for i, inp in enumerate(request.inputs):
            voice_path = decode_filepath_from_url(inp.voice_id)

            # Resolve and check if voice file exists
            resolved_voice_path = resolve_file_path(voice_path, project_root)
            if not os.path.exists(resolved_voice_path):
                logger.warning(
                    f"Voice file not found: {voice_path} (resolved: {resolved_voice_path}), skipping"
                )
                continue

            # Prepare generation parameters
            gen_kwargs = {
                "exaggeration": request.parameters.get("exaggeration", 0.5),
                "temperature": request.parameters.get("temperature", 0.75),
                "cfg_weight": request.parameters.get("cfg_weight", 0.5),
                "disable_watermark": request.parameters.get("disable_watermark", False),
                "audio_prompt_path": resolved_voice_path,
            }

            # Generate audio for this input
            wav = model.generate(inp.text.strip(), **gen_kwargs)
            waveform_list.append(wav)

            logger.info(f"Generated segment {i+1}: {inp.text[:50]}...")

        if not waveform_list:
            raise HTTPException(
                status_code=400, detail="No valid audio generated from inputs"
            )

        # Concatenate all waveforms
        full_audio = torch.cat(waveform_list, dim=1)

        # Save concatenated audio
        torchaudio.save(output_path, full_audio, model.sr)

        logger.info(f"Chatterbox dialogue completed: {output_path}")
        return GenerationResponse(
            status="success",
            output_filepath=output_path,
            message=f"Chatterbox dialogue generation completed ({len(waveform_list)} segments)",
        )

    except Exception as e:
        logger.error(f"Error in Chatterbox dialogue: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/load-model", response_model=LoadModelResponse)
async def load_model():
    """Preload the Chatterbox model."""
    try:
        get_or_load_model()
        return LoadModelResponse(
            status="success", message="Chatterbox model loaded successfully"
        )
    except Exception as e:
        logger.error(f"Error loading model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/unload-model", response_model=UnloadModelResponse)
async def unload_model_endpoint():
    """Unload the Chatterbox model and free memory."""
    try:
        success = unload_model()
        if success:
            return UnloadModelResponse(
                status="success", message="Chatterbox model unloaded successfully"
            )
        else:
            return UnloadModelResponse(status="info", message="No model was loaded")
    except Exception as e:
        logger.error(f"Error unloading model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/models", response_model=OpenAIModelsResponse)
async def list_models():
    """OpenAI-compatible models endpoint with health data."""
    import time
    
    model_loaded = MODEL is not None
    model_data = OpenAIModel(
        id=MODEL_NAME,
        created=int(time.time()),
        owned_by="custom",
        status="healthy",
        model_loaded=model_loaded,
        device=DEVICE,
        dependencies_available=CHATTERBOX_AVAILABLE,
    )
    
    return OpenAIModelsResponse(data=[model_data])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8004)
