#!/usr/bin/env python3
"""
Dia Text-to-Dialogue Microservice

A FastAPI service for the Dia model that provides ElevenLabs-compatible endpoints.
Note: Dia only supports multi-speaker dialogue generation, not single-speaker TTS.
"""

import gc
import logging
import os
import tempfile
import uuid
from typing import Dict, List, Optional, Any
from urllib.parse import unquote

import torch
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel

# Import shared models
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Add project root to path for imports
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.append(project_root)

from backend.core.utils.file_utils import concatenate_audio_files
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

try:
    from transformers import AutoProcessor, DiaForConditionalGeneration
    import torchaudio
    import librosa
    import soundfile as sf
    import numpy as np

    DIA_AVAILABLE = True
except ImportError as e:
    print(f"Error importing DIA dependencies: {e}")
    DIA_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global model state
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
MODEL = None
PROCESSOR = None
MODEL_CHECKPOINT = "nari-labs/Dia-1.6B-0626"

app = FastAPI(title="Dia Text-to-Dialogue Service", version="1.0.0")


from model_shared_utils import resolve_file_path


# Helper functions
def load_audio_prompt(audio_path: str, target_sr: int = 44100):
    """Load and preprocess audio for voice cloning."""
    try:
        audio, sr = librosa.load(audio_path, sr=target_sr)
        return audio
    except Exception as e:
        logger.warning(f"Error loading audio {audio_path}: {e}")
        return None


def format_dialogue_text(texts: List[str], voice_paths: List[str] = None) -> str:
    """Format dialogue texts with speaker tags."""
    if not texts:
        return ""

    print(f"Voice paths: {voice_paths}")
    print(f"Texts: {texts}")
    # Generate automatic speaker mapping based on voice_paths
    if voice_paths and len(voice_paths) == len(texts):
        voice_to_speaker = {}
        speaker_counter = 0
        speaker_mapping = []

        for voice_path in voice_paths:
            if voice_path not in voice_to_speaker:
                voice_to_speaker[voice_path] = speaker_counter
                speaker_counter += 1
            speaker_mapping.append(voice_to_speaker[voice_path])
    else:
        # Default to alternating speakers
        speaker_mapping = [i % 2 for i in range(len(texts))]

    dialogue_parts = []
    for text, speaker_idx in zip(texts, speaker_mapping):
        speaker_tag = f"[S{speaker_idx + 1}]"
        dialogue_parts.append(f"{speaker_tag} {text.strip()}")

    return " ".join(dialogue_parts)


def get_or_load_model():
    """Load the Dia model and processor."""
    global MODEL, PROCESSOR

    if MODEL is None:
        if not DIA_AVAILABLE:
            raise HTTPException(
                status_code=500, detail="DIA model dependencies not available"
            )

        logger.info("Loading DIA model...")
        PROCESSOR = AutoProcessor.from_pretrained(MODEL_CHECKPOINT)
        MODEL = DiaForConditionalGeneration.from_pretrained(MODEL_CHECKPOINT).to(DEVICE)
        logger.info(f"DIA model loaded on device: {DEVICE}")

    return MODEL, PROCESSOR


def unload_model():
    """Unload the model and free memory."""
    global MODEL, PROCESSOR

    if MODEL is not None:
        logger.info("Unloading DIA model...")
        del MODEL
        del PROCESSOR
        MODEL = None
        PROCESSOR = None

        # Force garbage collection
        gc.collect()

        # Clear CUDA cache if available
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        logger.info("DIA model unloaded successfully")
        return True

    return False


MODEL_NAME = "Dia"


# API Endpoints
@app.get("/", response_model=ServiceInfoResponse)
async def root():
    return ServiceInfoResponse(message=MODEL_NAME, model=MODEL_CHECKPOINT)


@app.post("/v1/text-to-speech/{voice_id}", response_model=GenerationResponse)
async def text_to_speech(voice_id: str, request: TextToSpeechRequest):
    """
    ElevenLabs-compatible single-speaker TTS endpoint.
    Note: Dia doesn't support single-speaker generation, so this returns an error.
    """
    raise HTTPException(
        status_code=400,
        detail="Dia model only supports multi-speaker dialogue generation. Use /v1/text-to-dialogue instead.",
    )


@app.post("/v1/text-to-dialogue", response_model=GenerationResponse)
async def text_to_dialogue(request: TextToDialogueRequest):
    """Generate multi-speaker dialogue audio using Dia model."""
    try:
        # Load model
        model, processor = get_or_load_model()

        # Extract texts and voice paths
        texts = request.audio_transcriptions
        for inp in request.inputs:
            texts.append(inp.text)
        # texts = [inp.text for inp in request.inputs]
        voice_paths = request.voice_clone_paths
        for inp in request.inputs:
            voice_paths.append(inp.voice_id)
        voice_paths = [
            resolve_file_path(decode_filepath_from_url(vp), project_root)
            for vp in voice_paths
        ]

        # Format dialogue text with speaker tags
        dialogue_text = format_dialogue_text(texts, voice_paths)
        logger.info(f"Generated dialogue text: {dialogue_text}")
        logger.info(f"Voice paths: {voice_paths}")

        # Prepare generation parameters
        gen_kwargs = {
            "max_new_tokens": request.parameters.get("max_new_tokens", 256),
        }

        # Set seed if provided
        if "seed" in request.parameters:
            seed = request.parameters["seed"]
            torch.manual_seed(seed)
            if torch.cuda.is_available():
                torch.cuda.manual_seed(seed)

        print(f"Voice paths: {voice_paths}")
        # Check if we have voice clone paths for multi-speaker generation
        if voice_paths and all(os.path.exists(path) for path in voice_paths):
            logger.info("Using voice cloning with audio prompts")

            # Get unique voice paths
            unique_voice_paths = []
            seen_voices = set()
            for voice_path in voice_paths:
                if voice_path not in seen_voices:
                    unique_voice_paths.append(voice_path)
                    seen_voices.add(voice_path)

            # Create concatenated audio prompt using unique voices
            concatenated_audio = concatenate_audio_files(unique_voice_paths)

            if concatenated_audio is not None:
                # Process inputs with concatenated audio prompt
                inputs = processor(
                    text=[dialogue_text],
                    audio=concatenated_audio,
                    padding=True,
                    return_tensors="pt",
                ).to(DEVICE)

                # Get audio prompt length for proper decoding
                prompt_len = processor.get_audio_prompt_len(
                    inputs["decoder_attention_mask"]
                )

                logger.info(f"Actual text sent to Dia: {dialogue_text}")

                # Generate audio
                outputs = model.generate(**inputs, **gen_kwargs)

                # Decode generated audio (excluding prompt)
                generated_audio = processor.batch_decode(
                    outputs, audio_prompt_len=prompt_len
                )
            else:
                logger.warning(
                    "Failed to load voice clones, falling back to text-only generation"
                )
                inputs = processor(
                    text=[dialogue_text], padding=True, return_tensors="pt"
                ).to(DEVICE)
                outputs = model.generate(**inputs, **gen_kwargs)
                generated_audio = processor.batch_decode(outputs)
        else:
            # Text-only generation
            logger.info("Using text-only generation (no valid voice clones)")
            inputs = processor(
                text=[dialogue_text], padding=True, return_tensors="pt"
            ).to(DEVICE)
            outputs = model.generate(**inputs, **gen_kwargs)
            generated_audio = processor.batch_decode(outputs)

        # Save generated audio to specified filepath
        output_path = request.output_filepath

        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Save audio using processor
        processor.save_audio(generated_audio, output_path)

        logger.info(f"Successfully generated dialogue audio: {output_path}")
        return GenerationResponse(
            status="success",
            output_filepath=output_path,
            message="Dialogue audio generated successfully",
        )

    except Exception as e:
        logger.error(f"Error generating dialogue audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/load-model", response_model=LoadModelResponse)
async def load_model():
    """Preload the Dia model."""
    try:
        get_or_load_model()
        return LoadModelResponse(
            status="success", message="Dia model loaded successfully"
        )
    except Exception as e:
        logger.error(f"Error loading model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/unload-model", response_model=UnloadModelResponse)
async def unload_model_endpoint():
    """Unload the Dia model and free memory."""
    try:
        success = unload_model()
        if success:
            return UnloadModelResponse(
                status="success", message="Dia model unloaded successfully"
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
        dependencies_available=DIA_AVAILABLE,
    )

    return OpenAIModelsResponse(data=[model_data])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8003)
