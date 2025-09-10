#!/usr/bin/env python3
"""
Higgs Audio Generation Microservice

A FastAPI service for the Higgs audio model that provides ElevenLabs-compatible endpoints.
Supports both single-speaker TTS and multi-speaker dialogue generation.
"""

import gc
import logging
import os
import re
import uuid
from typing import Dict, List, Optional, Any
from urllib.parse import unquote

import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

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
    from boson_multimodal.serve.serve_engine import (
        HiggsAudioServeEngine,
        HiggsAudioResponse,
    )
    from boson_multimodal.data_types import (
        ChatMLSample,
        Message,
        AudioContent,
        TextContent,
    )
    import torchaudio

    HIGGS_AVAILABLE = True
except ImportError as e:
    print(f"Error importing Higgs dependencies: {e}")
    HIGGS_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global model state
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
MODEL = None
MODEL_PATH = "bosonai/higgs-audio-v2-generation-3B-base"
AUDIO_TOKENIZER_PATH = "bosonai/higgs-audio-v2-tokenizer"

app = FastAPI(title="Higgs Audio Generation Service", version="1.0.0")

from model_shared_utils import resolve_file_path


def get_or_load_model():
    """Load the Higgs model."""
    global MODEL

    if MODEL is None:
        if not HIGGS_AVAILABLE:
            raise HTTPException(
                status_code=500, detail="Higgs dependencies not available"
            )

        logger.info("Loading Higgs model...")
        MODEL = HiggsAudioServeEngine(MODEL_PATH, AUDIO_TOKENIZER_PATH, device=DEVICE)
        logger.info(f"Higgs model loaded on device: {DEVICE}")

    return MODEL


def unload_model():
    """Unload the model and free memory."""
    global MODEL

    if MODEL is not None:
        logger.info("Unloading Higgs model...")
        del MODEL
        MODEL = None

        # Force garbage collection
        gc.collect()

        # Clear CUDA cache if available
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        logger.info("Higgs model unloaded successfully")
        return True

    return False


def prepare_single_speaker_messages(
    text: str,
    scene_prompt: str,
    voice_clone_path: Optional[str] = None,
    transcription: Optional[str] = None,
) -> List[Message]:
    """Prepare ChatML messages for single-speaker generation."""
    messages = []

    # System message with scene description
    system_content = f"Generate audio following instruction.\n\n<|scene_desc_start|>\n{scene_prompt}\n<|scene_desc_end|>"
    messages.append(Message(role="system", content=system_content))

    # If we have a voice clone, include it as a reference
    if voice_clone_path and transcription:
        # Add voice clone example
        messages.append(Message(role="user", content=transcription))
        messages.append(
            Message(
                role="assistant",
                content=AudioContent(
                    audio_url=resolve_file_path(voice_clone_path, project_root)
                ),
            )
        )
    else:
        raise Exception(
            f"No voice clone path or transcription provided, {voice_clone_path=}, {transcription=}"
        )

    # Add the actual text to generate
    messages.append(Message(role="user", content=text))

    return messages


def prepare_multi_speaker_messages(
    texts: List[str],
    scene_prompt: str,
    voice_clone_paths: Optional[List[str]] = None,
    audio_transcriptions: Optional[List[str]] = None,
) -> List[Message]:
    """Prepare ChatML messages for multi-speaker generation."""
    messages = []

    # Build system message with speaker descriptions
    speaker_descriptions = []
    if voice_clone_paths and audio_transcriptions:
        # Create speaker mapping based on unique voice clones
        unique_voices = {}
        speaker_counter = 0

        for i, voice_path in enumerate(voice_clone_paths):
            if voice_path not in unique_voices:
                unique_voices[voice_path] = speaker_counter
                transcription = (
                    audio_transcriptions[i] if i < len(audio_transcriptions) else ""
                )
                speaker_descriptions.append(
                    f"SPEAKER{speaker_counter}: {transcription}"
                )
                speaker_counter += 1
    else:
        # Default speaker descriptions
        speaker_tags = extract_speaker_tags(texts)
        for i, tag in enumerate(speaker_tags):
            gender = "feminine" if i % 2 == 0 else "masculine"
            speaker_descriptions.append(f"{tag}: {gender}")

    scene_desc = f"{scene_prompt}\n\n" + "\n".join(speaker_descriptions)
    system_content = f"Generate audio following instruction.\n\n<|scene_desc_start|>\n{scene_desc}\n<|scene_desc_end|>"
    messages.append(Message(role="system", content=system_content))

    # Add voice clone examples if available
    if voice_clone_paths and audio_transcriptions:
        unique_voices = {}
        for i, voice_path in enumerate(voice_clone_paths):
            if voice_path not in unique_voices:
                unique_voices[voice_path] = True
                transcription = (
                    audio_transcriptions[i] if i < len(audio_transcriptions) else ""
                )
                speaker_id = len(unique_voices) - 1

                messages.append(
                    Message(
                        role="user", content=f"[SPEAKER{speaker_id}] {transcription}"
                    )
                )
                messages.append(
                    Message(
                        role="assistant",
                        content=AudioContent(
                            audio_url=resolve_file_path(voice_path, project_root)
                        ),
                    )
                )

    # Combine all texts with speaker tags
    combined_text = format_multi_speaker_text(texts, voice_clone_paths)
    messages.append(Message(role="user", content=combined_text))

    return messages


def extract_speaker_tags(texts: List[str]) -> List[str]:
    """Extract unique speaker tags from texts."""
    pattern = re.compile(r"\[(SPEAKER\d+)\]")
    speaker_tags = set()

    for text in texts:
        tags = pattern.findall(text)
        speaker_tags.update(tags)

    return sorted(list(speaker_tags))


def format_multi_speaker_text(
    texts: List[str], voice_clone_paths: Optional[List[str]] = None
) -> str:
    """Format multiple texts with appropriate speaker tags."""
    if not texts:
        return ""

    # Generate speaker mapping based on voice clone paths if available
    if voice_clone_paths and len(voice_clone_paths) == len(texts):
        voice_to_speaker = {}
        speaker_counter = 0
        speaker_mapping = []

        for voice_path in voice_clone_paths:
            if voice_path not in voice_to_speaker:
                voice_to_speaker[voice_path] = speaker_counter
                speaker_counter += 1
            speaker_mapping.append(voice_to_speaker[voice_path])
    else:
        # Default to sequential speakers
        speaker_mapping = list(range(len(texts)))

    formatted_parts = []
    for text, speaker_idx in zip(texts, speaker_mapping):
        # Check if text already has speaker tags
        if not re.search(r"\[SPEAKER\d+\]", text):
            text = f"[SPEAKER{speaker_idx}] {text.strip()}"
        formatted_parts.append(text)

    return "\n".join(formatted_parts)


MODEL_NAME = "Higgs"


# API Endpoints
@app.get("/", response_model=ServiceInfoResponse)
async def root():
    return ServiceInfoResponse(message=MODEL_NAME, model=MODEL_PATH)


@app.post("/v1/text-to-speech/{voice_id}", response_model=GenerationResponse)
async def text_to_speech(voice_id: str, request: TextToSpeechRequest):
    """Single-speaker text-to-speech generation using Higgs."""
    try:
        # Decode URL-encoded voice_id (filepath)
        voice_path = decode_filepath_from_url(voice_id)

        output_path = request.output_filepath

        logger.info(f"Higgs TTS: {voice_path} -> {output_path}")
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

        # Get parameters
        scene_prompt = request.parameters.get(
            "scene_prompt", "Audio is recorded from a quiet room."
        )
        transcription = request.audio_transcriptions[0]

        # Prepare messages for single speaker
        messages = prepare_single_speaker_messages(
            request.text, scene_prompt, voice_path, transcription
        )

        # Create ChatML sample
        chat_ml_sample = ChatMLSample(messages=messages)

        print(f"ChatML sample: {chat_ml_sample}")

        # Generation parameters
        generation_params = {
            "max_new_tokens": request.parameters.get("max_new_tokens", 1024),
            "temperature": request.parameters.get("temperature", 0.3),
            "top_p": request.parameters.get("top_p", 0.95),
            "top_k": request.parameters.get("top_k", 50),
            "stop_strings": ["<|end_of_text|>", "<|eot_id|>"],
        }

        # Add RAS parameters if specified
        ras_win_len = request.parameters.get("ras_win_len", 7)
        if ras_win_len and ras_win_len > 0:
            generation_params["ras_win_len"] = ras_win_len
            generation_params["ras_win_max_num_repeat"] = request.parameters.get(
                "ras_win_max_num_repeat", 2
            )

        # Create output directory if needed
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Generate audio
        response: HiggsAudioResponse = model.generate(
            chat_ml_sample=chat_ml_sample, **generation_params
        )

        # Save audio
        audio_tensor = torch.from_numpy(response.audio)[None, :]
        torchaudio.save(output_path, audio_tensor, response.sampling_rate)

        logger.info(f"Higgs TTS completed: {output_path}")
        return GenerationResponse(
            status="success",
            output_filepath=output_path,
            message="Higgs TTS generation completed",
        )

    except Exception as e:
        logger.error(f"Error in Higgs TTS: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/text-to-dialogue", response_model=GenerationResponse)
async def text_to_dialogue(request: TextToDialogueRequest):
    """Multi-speaker dialogue generation using Higgs."""
    try:
        if len(request.inputs) < 1:
            raise HTTPException(status_code=400, detail="At least one input required")

        # Load model
        model = get_or_load_model()

        output_path = request.output_filepath

        # Extract texts and voice paths
        texts = [inp.text for inp in request.inputs]
        voice_paths = [inp.voice_id for inp in request.inputs]

        # Check if voice files exist
        resolved_voice_paths = []
        for voice_path in voice_paths:
            resolved_path = resolve_file_path(
                decode_filepath_from_url(voice_path), project_root
            )
            if not os.path.exists(resolved_path):
                logger.warning(
                    f"Voice file not found: {voice_path} (resolved: {resolved_path})"
                )
            resolved_voice_paths.append(resolved_path)

        # Set seed if provided
        if "seed" in request.parameters:
            seed = request.parameters["seed"]
            torch.manual_seed(seed)
            if torch.cuda.is_available():
                torch.cuda.manual_seed(seed)

        # Get parameters
        scene_prompt = request.parameters.get(
            "scene_prompt", "Audio is recorded from a quiet room."
        )
        audio_transcriptions = request.audio_transcriptions

        # Prepare messages for multi-speaker
        messages = prepare_multi_speaker_messages(
            texts, scene_prompt, resolved_voice_paths, audio_transcriptions
        )

        # Create ChatML sample
        chat_ml_sample = ChatMLSample(messages=messages)

        # Generation parameters
        generation_params = {
            "max_new_tokens": request.parameters.get("max_new_tokens", 1024),
            "temperature": request.parameters.get("temperature", 0.3),
            "top_p": request.parameters.get("top_p", 0.95),
            "top_k": request.parameters.get("top_k", 50),
            "stop_strings": ["<|end_of_text|>", "<|eot_id|>"],
        }

        # Add RAS parameters if specified
        ras_win_len = request.parameters.get("ras_win_len", 7)
        if ras_win_len and ras_win_len > 0:
            generation_params["ras_win_len"] = ras_win_len
            generation_params["ras_win_max_num_repeat"] = request.parameters.get(
                "ras_win_max_num_repeat", 2
            )

        # Create output directory if needed
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Generate audio
        response: HiggsAudioResponse = model.generate(
            chat_ml_sample=chat_ml_sample, **generation_params
        )

        # Save audio
        audio_tensor = torch.from_numpy(response.audio)[None, :]
        torchaudio.save(output_path, audio_tensor, response.sampling_rate)

        logger.info(f"Higgs dialogue completed: {output_path}")
        return GenerationResponse(
            status="success",
            output_filepath=output_path,
            message=f"Higgs dialogue generation completed ({len(texts)} segments)",
        )

    except Exception as e:
        logger.error(f"Error in Higgs dialogue: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/load-model", response_model=LoadModelResponse)
async def load_model():
    """Preload the Higgs model."""
    try:
        get_or_load_model()
        return LoadModelResponse(
            status="success", message="Higgs model loaded successfully"
        )
    except Exception as e:
        logger.error(f"Error loading model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/unload-model", response_model=UnloadModelResponse)
async def unload_model_endpoint():
    """Unload the Higgs model and free memory."""
    try:
        success = unload_model()
        if success:
            return UnloadModelResponse(
                status="success", message="Higgs model unloaded successfully"
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
        dependencies_available=HIGGS_AVAILABLE,
    )
    
    return OpenAIModelsResponse(data=[model_data])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8005)
