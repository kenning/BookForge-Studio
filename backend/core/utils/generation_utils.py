"""
HTTP Client Utilities for AI Model Microservices

Utilities for calling AI model microservices instead of loading models directly.
"""

import uuid
import numpy as np
import librosa
import os
import asyncio
import aiohttp
from typing import Optional, Dict, Any, List, Tuple
from urllib.parse import quote
from backend.core.data_types.step_context import StepContext
from backend.core.utils.url_utils import (
    add_file_prefix,
    encode_filepath_for_url,
    decode_filepath_from_url,
)
from backend.core.utils.model_ports_config import MODEL_SERVICE_PORTS
from backend.core.utils.sentence_chunking import chunk_sentences
from backend.core.router_websocket import websocket_manager

# Import logging utilities
from backend.core.utils.logger import get_logger
from models.shared_models import TextToSpeechRequest, TextToDialogueRequest
from backend.core.config import PROJECT_ROOT

logger = get_logger(__name__)


def get_testing_mode() -> Optional[str]:
    """
    Check which testing mode is active.

    Returns:
        "TESTING" or "TESTING_UI" for mock service calls
        None for normal operation
    """
    if os.getenv("TESTING_UI", "false").lower() == "true":
        return "TESTING_UI"
    elif os.getenv("TESTING", "false").lower() == "true":
        return "TESTING"
    return None


def get_model_service_port(model_name: str) -> int:
    """Get the port for a model's microservice."""
    testing_mode = get_testing_mode()

    # In testing modes, always use mock service
    if testing_mode:
        logger.info(f"{testing_mode} mode: using mock service")
        return MODEL_SERVICE_PORTS["mock"]

    # Normal operation
    if model_name in MODEL_SERVICE_PORTS:
        return MODEL_SERVICE_PORTS[model_name]
    else:
        raise ValueError(
            f"Unknown model: {model_name}. Available: {list(MODEL_SERVICE_PORTS.keys())}"
        )


async def call_model_service(
    port: int, endpoint: str, payload: Dict[str, Any], timeout: int = 10000
) -> Dict[str, Any]:
    """
    Make an HTTP call to a model microservice.

    Args:
        port: Service port number
        endpoint: API endpoint (e.g., "/v1/text-to-speech/voice.wav")
        payload: Request payload
        timeout: Request timeout in seconds

    Returns:
        Response JSON as dict
    """
    url = f"http://localhost:{port}{endpoint}"

    logger.info(f"Calling model service: {url}")
    logger.debug(f"Payload: {payload}")

    timeout_obj = aiohttp.ClientTimeout(total=timeout)

    try:
        async with aiohttp.ClientSession(timeout=timeout_obj) as session:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(
                        f"Service call successful: {result.get('message', 'OK')}"
                    )
                    return result
                else:
                    error_text = await response.text()
                    logger.error(
                        f"Service call failed (HTTP {response.status}): {error_text}"
                    )
                    raise Exception(f"HTTP {response.status}: {error_text}")

    except aiohttp.ClientError as e:
        logger.error(f"Network error calling service on port {port}: {e}")
        raise Exception(
            f"Failed to connect to model service on port {port}. Is the service running?"
        )
    except asyncio.TimeoutError:
        logger.error(f"Timeout calling service on port {port}")
        raise Exception(f"Service call timed out after {timeout} seconds")


def build_tts_request(
    context: StepContext,
    texts: List[str],
    voice_paths: List[str],
    audio_transcriptions: List[str],
) -> Dict[str, Any]:
    """Build a text-to-speech request payload."""
    # Generate unique output path
    import uuid

    candidate_filename = f"candidate_{uuid.uuid4().hex[:8]}.wav"
    output_path = os.path.join(context.temp_dir, candidate_filename)

    return TextToSpeechRequest(
        text=texts[0],
        output_filepath=output_path,
        parameters=dict(context.parameters),  # Convert to regular dict
        voice_clone_paths=voice_paths,
        audio_transcriptions=audio_transcriptions,
    )


def build_dialogue_request(
    context: StepContext,
    texts: List[str],
    voice_paths: List[str],
    audio_transcriptions: List[str],
) -> Dict[str, Any]:
    """Build a text-to-dialogue request payload."""
    # Generate unique output path
    import uuid

    candidate_filename = f"dialogue_{uuid.uuid4().hex[:8]}.wav"
    output_path = os.path.join(context.temp_dir, candidate_filename)

    # Build dialogue inputs
    inputs = []
    for text, voice_path in zip(texts, voice_paths):
        inputs.append(
            {"text": text, "voice_id": voice_path}  # Will be URL-encoded by the service
        )

    print("inputs", inputs)

    return TextToDialogueRequest(
        inputs=inputs,
        output_filepath=output_path,
        parameters=dict(context.parameters),  # Convert to regular dict
        voice_clone_paths=voice_paths,
        audio_transcriptions=audio_transcriptions,
    )


async def generate_single_candidate_via_service(
    model_name: str,
    context: StepContext,
    texts: List[str],
    voice_paths: List[str],
    audio_transcriptions: List[str],
    candidate_idx: int,
) -> Tuple[str, List[str], str]:
    # Get service port
    port = get_model_service_port(model_name)

    # Add candidate-specific seed
    candidate_params = dict(context.parameters)
    if context.actual_seed is not None:
        candidate_params["seed"] = context.actual_seed + candidate_idx

    # Update context parameters temporarily
    original_params = context.parameters
    context.parameters = candidate_params
    voice_paths = [
        encode_filepath_for_url(add_file_prefix(vcp))
        for vcp in context.voice_clone_paths
    ]

    its_definitely_multi_speaker = context.is_multi_speaker and len(texts) > 1

    # Determine if single-speaker or multi-speaker
    if its_definitely_multi_speaker:
        # Multi-speaker dialogue
        endpoint = "/v1/text-to-dialogue"
    else:
        # Single-speaker TTS
        if not voice_paths:
            raise Exception("No voice clone path provided for single-speaker TTS")

        # Use first voice and concatenate texts
        voice_path = voice_paths[0]
        endpoint = f"/v1/text-to-speech/{voice_path}"

    # Build payload for each chunk
    sentence_chunks = chunk_sentences(
        texts,
        voice_paths,
        audio_transcriptions,
        context.approximate_min_chunk_length or 20,
    )

    responses = []

    for chunk_idx, chunk in enumerate(sentence_chunks):
        context.parameters["step_index"] += 1
        original_params["step_index"] += 1

        # Send progress update
        await websocket_manager.broadcast_execution_progress(
            context.parameters["execution_id"],
            "Generating chunk "
            + str(chunk_idx + 1)
            + " of "
            + str(len(sentence_chunks)),
            context.parameters["step_index"],
            context.parameters["total_steps"],
            context.output_subfolder,
        )

        print("#" * 80)
        print("chunk", chunk)
        print("#" * 80)
        if its_definitely_multi_speaker:
            payload = build_dialogue_request(
                context,
                chunk["texts"],
                chunk["voice_clones"],
                chunk["voice_transcriptions"],
            )
        else:
            payload = build_tts_request(
                context,
                chunk["texts"],  # This will always be one single string.
                chunk["voice_clones"],
                chunk["voice_transcriptions"],
            )

        # Call service

        print("payload", payload)
        response = await call_model_service(port, endpoint, payload.model_dump())
        responses.append(response)

    # Concatenate responses
    target_sr = 44100
    output_filepaths = [r["output_filepath"] for r in responses]
    output_audios = [librosa.load(fp, sr=target_sr)[0] for fp in output_filepaths]
    concatenated_audio = np.concatenate(output_audios)
    # save to temp file
    temp_file_path = os.path.join(
        context.temp_dir, f"concatenated_{uuid.uuid4().hex[:8]}.wav"
    )
    import soundfile as sf

    sf.write(temp_file_path, concatenated_audio, target_sr)

    # Restore original parameters (??)
    context.parameters = original_params

    logger.info(
        f"Generated candidate {candidate_idx + 1}: {response['output_filepath']}"
    )
    return (
        temp_file_path,
        sentence_chunks,
        f"Using an approximate chunk size of {context.approximate_min_chunk_length} words",
    )


async def generate_candidates_with_service_calls(
    model_name: str,
    context: StepContext,
    texts: List[str],
    voice_paths: List[str],
    audio_transcriptions: List[str],
) -> None:
    """
    Generate multiple candidates by calling model microservices.

    This is the main entry point for generating audio via microservices.
    """
    try:
        assert len(texts) == len(voice_paths) == len(audio_transcriptions)
    except AssertionError:
        raise Exception(
            f"Lengths of texts, voice_paths, and audio_transcriptions must match. "
            + f"Got {len(texts)=}, {len(voice_paths)=}, and {len(audio_transcriptions)=}. "
            + f"texts: {texts}, voice_paths: {voice_paths}, audio_transcriptions: {audio_transcriptions}"
        )

    logger.info(
        f"Generating {context.num_candidates} candidates using {model_name} service"
    )

    # Generate candidates
    candidates = []
    debug_chunks = None
    debug_chunk_help_text = None

    if context.enable_parallel and context.num_candidates > 1:
        # Parallel generation
        logger.info(f"Running {context.num_candidates} candidates in parallel")

        tasks = []
        for candidate_idx in range(context.num_candidates):
            task = generate_single_candidate_via_service(
                model_name,
                context,
                texts,
                voice_paths,
                audio_transcriptions,
                candidate_idx,
            )
            tasks.append(task)

        # Wait for all candidates
        awaited_responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect successful candidates
        for candidate_idx, result in enumerate(awaited_responses):
            if isinstance(result, Exception):
                logger.error(f"Candidate {candidate_idx + 1} failed: {result}")
            elif result is not None:
                result, chunks, help_text = awaited_responses[candidate_idx]
                if debug_chunks is None:
                    debug_chunks = chunks
                if debug_chunk_help_text is None:
                    debug_chunk_help_text = help_text
                candidates.append(result)

    else:
        # Sequential generation
        logger.info(f"Running {context.num_candidates} candidates sequentially")

        for candidate_idx in range(context.num_candidates):
            awaited_response = await generate_single_candidate_via_service(
                model_name,
                context,
                texts,
                voice_paths,
                audio_transcriptions,
                candidate_idx,
            )
            result, chunks, help_text = awaited_response
            if result is not None:
                candidates.append(result)
            if debug_chunks is None:
                debug_chunks = chunks
            if debug_chunk_help_text is None:
                debug_chunk_help_text = help_text

    # Update context
    context.audio_candidates = candidates
    # Reformat voice clones so they are readable
    context.debug_chunks = [
        {
            "texts": chunk["texts"],
            "voice_clones": [
                decode_filepath_from_url(c) for c in chunk["voice_clones"]
            ],
            "voice_transcriptions": chunk["voice_transcriptions"],
        }
        for chunk in debug_chunks
    ]
    context.debug_chunk_help_text = debug_chunk_help_text

    if not candidates:
        raise Exception("No valid candidates generated")

    logger.info(
        f"Successfully generated {len(candidates)} candidates via {model_name} service"
    )
