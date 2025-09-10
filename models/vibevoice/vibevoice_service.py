#!/usr/bin/env python3
"""
VibeVoice Audio Generation Microservice

A FastAPI service for the VibeVoice audio model that provides ElevenLabs-compatible endpoints.
Supports both single-speaker TTS and multi-speaker dialogue generation.
"""

import argparse
import gc
import importlib
import importlib.metadata
import logging
import os
import re
import uuid
from typing import Dict, List, Optional, Any
from urllib.parse import unquote

import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

default_cfg_scale = 1.6

# Import shared models
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_models import (
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

# Add project root to path for imports
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.append(project_root)
from backend.core.utils.url_utils import decode_filepath_from_url

try:
    from vibevoice.modular.modeling_vibevoice_inference import (
        VibeVoiceForConditionalGenerationInference,
    )
    from vibevoice.processor.vibevoice_processor import VibeVoiceProcessor
    import torchaudio

    VIBEVOICE_AVAILABLE = True
except ImportError as e:
    print(f"Error importing VibeVoice dependencies: {e}")
    VIBEVOICE_AVAILABLE = False

# Import logging utilities
from backend.core.utils.logger import get_logger

logger = get_logger(__name__)

# Global model state
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
MODEL = None
PROCESSOR = None
MODEL_PATH = "microsoft/VibeVoice-1.5b"  # Default model
MODEL_NAME = "VibeVoice"  # Will be updated based on model variant

app = FastAPI(title="VibeVoice Audio Generation Service", version="1.0.0")

from model_shared_utils import resolve_file_path


def is_torch_available():
    return torch.__version__ >= "2.0.0"


def _is_package_available(package_name):
    try:
        importlib.import_module(package_name)
        return True
    except ImportError:
        return False


def is_flash_attn_2_available():
    try:
        if not is_torch_available():
            return False
        if not _is_package_available("flash_attn"):
            return False
        import torch

        if not torch.cuda.is_available():
            return False
        try:
            return int(importlib.metadata.version("flash_attn")[0]) > 1
        except Exception as e:
            return False
    except Exception as e:
        logger.warning(f"Error checking flash_attn: {e}")
        return False


def get_or_load_model():
    """Load the VibeVoice model and processor."""
    global MODEL, PROCESSOR

    if MODEL is None or PROCESSOR is None:
        if not VIBEVOICE_AVAILABLE:
            raise HTTPException(
                status_code=500, detail="VibeVoice dependencies not available"
            )

        logger.info("Loading VibeVoice model and processor...")

        # Load processor
        PROCESSOR = VibeVoiceProcessor.from_pretrained(MODEL_PATH)

        # Load model
        if is_flash_attn_2_available():
            logger.info("Flash attention 2 is available!")
            attn_implementation = "flash_attention_2"
        else:
            logger.info("Flash attention 2 is not available, using eager")
            attn_implementation = "eager"

        MODEL = VibeVoiceForConditionalGenerationInference.from_pretrained(
            MODEL_PATH,
            torch_dtype=torch.bfloat16,
            device_map="cuda" if torch.cuda.is_available() else "cpu",
            attn_implementation=attn_implementation,
        )

        MODEL.eval()
        MODEL.set_ddpm_inference_steps(num_steps=10)

        logger.info(f"VibeVoice model loaded on device: {DEVICE}")

    return MODEL, PROCESSOR


def unload_model():
    """Unload the model and free memory."""
    global MODEL, PROCESSOR

    if MODEL is not None or PROCESSOR is not None:
        logger.info("Unloading VibeVoice model...")

        if MODEL is not None:
            del MODEL
            MODEL = None

        if PROCESSOR is not None:
            del PROCESSOR
            PROCESSOR = None

        # Force garbage collection
        gc.collect()

        # Clear CUDA cache if available
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        logger.info("VibeVoice model unloaded successfully")
        return True

    return False


def prepare_single_speaker_script(
    text: str,
    voice_clone_path: Optional[str] = None,
) -> str:
    """Prepare script for single-speaker generation."""
    if not text.startswith("Speaker 1:"):
        return f"Speaker 1: {text}"
    return text


def prepare_multi_speaker_script(
    texts: List[str],
    voice_clone_paths: Optional[List[str]] = None,
) -> str:
    """Prepare script for multi-speaker generation."""
    formatted_parts = []

    for i, text in enumerate(texts):
        speaker_num = i + 1
        # Check if text already has speaker tags
        if not re.search(r"\[?Speaker\s*\d+\]?:", text, re.IGNORECASE):
            text = f"Speaker {speaker_num}: {text.strip()}"
        formatted_parts.append(text)

    return "\n".join(formatted_parts)


def get_voice_samples_from_paths(voice_paths: List[str]) -> List[str]:
    """Convert voice paths to resolved file paths for VibeVoice."""
    resolved_paths = []
    for voice_path in voice_paths:
        resolved_path = resolve_file_path(
            decode_filepath_from_url(voice_path), project_root
        )
        if not os.path.exists(resolved_path):
            logger.warning(
                f"Voice file not found: {voice_path} (resolved: {resolved_path})"
            )
        resolved_paths.append(resolved_path)
    return resolved_paths


# API Endpoints
@app.get("/", response_model=ServiceInfoResponse)
async def root():
    return ServiceInfoResponse(message=MODEL_NAME, model=MODEL_PATH)


@app.post("/v1/text-to-speech/{voice_id}", response_model=GenerationResponse)
async def text_to_speech(voice_id: str, request: TextToSpeechRequest):
    """Single-speaker text-to-speech generation using VibeVoice."""
    try:
        # Decode URL-encoded voice_id (filepath)
        voice_path = decode_filepath_from_url(voice_id)

        output_path = request.output_filepath

        logger.info(f"VibeVoice TTS: {voice_path} -> {output_path}")
        logger.info(f"Text: {request.text}")

        # Resolve and check if voice file exists
        resolved_voice_path = resolve_file_path(voice_path, project_root)
        if not os.path.exists(resolved_voice_path):
            raise HTTPException(
                status_code=400,
                detail=f"Voice file not found: {voice_path} (resolved: {resolved_voice_path})",
            )

        # Load model and processor
        model, processor = get_or_load_model()

        # Set seed if provided
        if "seed" in request.parameters:
            seed = request.parameters["seed"]
            torch.manual_seed(seed)
            if torch.cuda.is_available():
                torch.cuda.manual_seed(seed)

        # Prepare script for single speaker
        script = prepare_single_speaker_script(request.text)

        # Prepare inputs for the model
        inputs = processor(
            text=[script],  # Wrap in list for batch processing
            voice_samples=[
                [resolved_voice_path]
            ],  # Single voice sample for single speaker
            padding=True,
            return_tensors="pt",
            return_attention_mask=True,
        )

        # Generation parameters
        cfg_scale = request.parameters.get("cfg_scale", default_cfg_scale)

        # Create output directory if needed
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Generate audio
        outputs = model.generate(
            **inputs,
            max_new_tokens=None,
            cfg_scale=cfg_scale,
            tokenizer=processor.tokenizer,
            generation_config={"do_sample": False},
            verbose=False,
        )

        # Save audio
        processor.save_audio(
            outputs.speech_outputs[0],  # First (and only) batch item
            output_path=output_path,
        )

        logger.info(f"VibeVoice TTS completed: {output_path}")
        return GenerationResponse(
            status="success",
            output_filepath=output_path,
            message="VibeVoice TTS generation completed",
        )

    except Exception as e:
        logger.error(f"Error in VibeVoice TTS: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/text-to-dialogue", response_model=GenerationResponse)
async def text_to_dialogue(request: TextToDialogueRequest):
    """Multi-speaker dialogue generation using VibeVoice."""
    try:
        if len(request.inputs) < 1:
            raise HTTPException(status_code=400, detail="At least one input required")

        # Load model and processor
        model, processor = get_or_load_model()

        output_path = request.output_filepath

        # Extract texts and voice paths
        texts = [inp.text for inp in request.inputs]
        voice_paths = [inp.voice_id for inp in request.inputs]

        # Get resolved voice samples
        voice_samples = get_voice_samples_from_paths(voice_paths)

        # Set seed if provided
        if "seed" in request.parameters:
            seed = request.parameters["seed"]
            torch.manual_seed(seed)
            if torch.cuda.is_available():
                torch.cuda.manual_seed(seed)

        # Prepare script for multi-speaker
        full_script = prepare_multi_speaker_script(texts, voice_paths)

        # Prepare inputs for the model
        inputs = processor(
            text=[full_script],  # Wrap in list for batch processing
            voice_samples=[voice_samples],  # Wrap in list for batch processing
            padding=True,
            return_tensors="pt",
            return_attention_mask=True,
        )

        # Generation parameters
        cfg_scale = request.parameters.get("cfg_scale", 1.0)

        # Create output directory if needed
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Generate audio
        outputs = model.generate(
            **inputs,
            max_new_tokens=None,
            cfg_scale=cfg_scale,
            tokenizer=processor.tokenizer,
            generation_config={"do_sample": False},
            verbose=False,
        )

        # Save audio
        processor.save_audio(
            outputs.speech_outputs[0],  # First (and only) batch item
            output_path=output_path,
        )

        logger.info(f"VibeVoice dialogue completed: {output_path}")
        return GenerationResponse(
            status="success",
            output_filepath=output_path,
            message=f"VibeVoice dialogue generation completed ({len(texts)} segments)",
        )

    except Exception as e:
        logger.error(f"Error in VibeVoice dialogue: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/load-model", response_model=LoadModelResponse)
async def load_model():
    """Preload the VibeVoice model."""
    try:
        get_or_load_model()
        return LoadModelResponse(
            status="success", message="VibeVoice model loaded successfully"
        )
    except Exception as e:
        logger.error(f"Error loading model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/unload-model", response_model=UnloadModelResponse)
async def unload_model_endpoint():
    """Unload the VibeVoice model and free memory."""
    try:
        success = unload_model()
        if success:
            return UnloadModelResponse(
                status="success", message="VibeVoice model unloaded successfully"
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

    model_loaded = MODEL is not None and PROCESSOR is not None
    model_data = OpenAIModel(
        id=MODEL_NAME,
        created=int(time.time()),
        owned_by="custom",
        status="healthy",
        model_loaded=model_loaded,
        device=DEVICE,
        dependencies_available=VIBEVOICE_AVAILABLE,
    )

    return OpenAIModelsResponse(data=[model_data])


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="VibeVoice Audio Generation Service")
    parser.add_argument(
        "--large",
        action="store_true",
        help="Use VibeVoice Large (7B) model instead of the default 1.5B model",
    )
    return parser.parse_args()


def configure_model(use_large=False):
    """Configure model path and name based on variant."""
    global MODEL_PATH, MODEL_NAME
    if use_large:
        MODEL_PATH = "aoi-ot/VibeVoice-7B"
        MODEL_NAME = "VibeVoice 7B"
    else:
        MODEL_PATH = "microsoft/VibeVoice-1.5b"
        MODEL_NAME = "VibeVoice"


if __name__ == "__main__":
    import uvicorn

    # Parse command line arguments
    args = parse_args()

    # Configure model based on arguments
    configure_model(use_large=args.large)

    logger.info(f"Starting {MODEL_NAME} service with model: {MODEL_PATH}")

    uvicorn.run(app, host="0.0.0.0", port=8006)
