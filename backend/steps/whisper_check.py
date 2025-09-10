"""
Step: Whisper Check

This step uses Whisper to validate audio candidates and select the best one.
It transcribes each candidate and compares it to the original text to find the most accurate match.
"""

import os
import re
import torch
from backend.core.data_types.step_context import StepContext
from difflib import SequenceMatcher

# Import logging utilities
from backend.core.utils.logger import get_logger

# Import thread pool utility
from backend.core.utils.threading import run_in_thread_pool

logger = get_logger(__name__)


async def load_whisper_backend(model_key: str, use_faster_whisper: bool, device: str):
    """Load the appropriate Whisper model backend in a thread pool"""

    def _load_model():
        if use_faster_whisper:
            try:
                from faster_whisper import WhisperModel

                return WhisperModel(model_key, device=device, compute_type="float16")
            except ImportError:
                logger.info(
                    "faster-whisper not available, falling back to openai/whisper"
                )
                # Fall through to regular whisper loading
                pass

        import whisper

        return whisper.load_model(model_key, device=device)

    return await run_in_thread_pool(_load_model)


async def whisper_check_mp(
    audio_path: str, expected_text: str, model, use_faster_whisper: bool
):
    """
    Check audio against expected text using Whisper transcription
    Returns (path, similarity_score, transcribed_text)
    """
    try:

        def _transcribe():
            if use_faster_whisper:
                segments, info = model.transcribe(audio_path, beam_size=5)
                return " ".join([segment.text for segment in segments]).strip()
            else:
                result = model.transcribe(audio_path)
                return result["text"].strip()

        # Run transcription in thread pool to avoid blocking the event loop
        transcribed = await run_in_thread_pool(_transcribe)

        # Calculate similarity score
        similarity = SequenceMatcher(
            None, expected_text.lower(), transcribed.lower()
        ).ratio()

        return audio_path, similarity, transcribed

    except Exception as e:
        logger.error(f"Error transcribing {audio_path}: {e}")
        return audio_path, 0.0, ""


async def process(context: StepContext):
    """
    Use Whisper to validate audio candidates and select the best one.

    Args:
        context: StepContext containing audio candidates and parameters
    """
    if not context.audio_candidates:
        raise Exception("No audio candidates available for whisper checking")

    # Get whisper parameters from this step's parameters
    whisper_model = context.parameters.get("whisper_model", "tiny")
    use_faster_whisper = context.parameters.get("use_faster_whisper", False)
    use_longest_transcript_on_fail = context.parameters.get(
        "use_longest_transcript_on_fail", False
    )

    logger.info(
        f"Running whisper validation on {len(context.audio_candidates)} candidates"
    )
    logger.info(f"Using whisper model: {whisper_model}")
    logger.info(f"Using faster-whisper: {use_faster_whisper}")

    # Load whisper model in thread pool
    device = "cuda" if torch.cuda.is_available() else "cpu"
    whisper_model_backend = await load_whisper_backend(
        whisper_model, use_faster_whisper, device
    )

    # Expected text for comparison
    expected_text = (
        " ".join(context.original_text_array) if context.original_text_array else ""
    )
    # Remove speaker tags like [S1], [S2], etc for dia. WIP: make this modular.
    expected_text = re.sub(r"\[S[1-9]\]", "", expected_text).strip()
    logger.info(f"Expected text for comparison: {expected_text}")

    # Validate each candidate
    candidate_scores = []

    for idx, candidate_path in enumerate(context.audio_candidates):
        if not os.path.exists(candidate_path) or os.path.getsize(candidate_path) < 1024:
            logger.warning(f"Candidate {idx} file is invalid or too small")
            candidate_scores.append((candidate_path, 0.0, ""))
            continue

        path, score, transcribed = await whisper_check_mp(
            candidate_path, expected_text, whisper_model_backend, use_faster_whisper
        )

        candidate_scores.append((candidate_path, score, transcribed))
        logger.info(
            f"Candidate {idx}: score={score:.3f}, transcribed='{transcribed[:50]}...'"
        )

    # Find the best candidate
    valid_candidates = [
        (cand_path, score, trans)
        for cand_path, score, trans in candidate_scores
        if score >= 0.95
    ]

    if valid_candidates:
        # Use the candidate with the highest score among valid ones
        best_candidate_path, best_score, best_transcribed = max(
            valid_candidates, key=lambda x: x[1]
        )
        # Find the index of the best candidate for logging
        best_idx = next(
            i
            for i, (cand_path, _, _) in enumerate(candidate_scores)
            if cand_path == best_candidate_path
        )
        logger.info(f"Selected candidate {best_idx} with score {best_score:.3f}")
    else:
        # No candidate passed the threshold
        if use_longest_transcript_on_fail:
            # Use the candidate with the longest transcription
            best_candidate_path, best_score, best_transcribed = max(
                candidate_scores, key=lambda x: len(x[2])
            )
            # Find the index of the best candidate for logging
            best_idx = next(
                i
                for i, (cand_path, _, _) in enumerate(candidate_scores)
                if cand_path == best_candidate_path
            )
            logger.info(
                f"No candidate passed threshold, using longest transcript: candidate {best_idx}"
            )
        else:
            # Use the candidate with the highest score, even if below threshold
            best_candidate_path, best_score, best_transcribed = max(
                candidate_scores, key=lambda x: x[1]
            )
            # Find the index of the best candidate for logging
            best_idx = next(
                i
                for i, (cand_path, _, _) in enumerate(candidate_scores)
                if cand_path == best_candidate_path
            )
            logger.info(
                f"No candidate passed threshold, using highest score: candidate {best_idx} with score {best_score:.3f}"
            )

    # Set the best candidate as the current audio (now just a file path)
    context.set_audio(best_candidate_path)

    # Clean up all NON-SELECTED candidate files
    cleanup_candidates(context.audio_candidates, exclude=best_candidate_path)
    context.audio_candidates = []

    logger.info(
        f"Whisper validation complete. Selected candidate with transcription: '{best_transcribed}'"
    )


def cleanup_candidates(candidates, exclude=None):
    """Clean up temporary candidate audio files, optionally excluding one"""
    cleanup_count = 0
    for candidate_path in candidates:
        # Skip the excluded file (the selected candidate)
        if exclude and candidate_path == exclude:
            continue

        try:
            if os.path.exists(candidate_path):
                os.remove(candidate_path)
                cleanup_count += 1
        except Exception as e:
            logger.error(f"Error cleaning up candidate file {candidate_path}: {e}")

    if cleanup_count > 0:
        logger.info(f"Cleaned up {cleanup_count} non-selected candidate files")


# Step metadata
STEP_METADATA = {
    "name": "whisper_check",
    "display_name": "Whisper Validation",
    "description": "Uses Whisper to validate audio candidates and select the most accurate one",
    "input_type": "audio",
    "output_type": "audio",
    "category": "audio-generation",
    "step_type": "post_generation_step",
    "version": "1.0.0",
    "parameters": {
        "whisper_model": {
            "type": "str",
            "default": "tiny",
            "options": ["tiny", "base", "small", "medium", "large"],
            "description": "Whisper model size for transcription validation",
        },
        "use_faster_whisper": {
            "type": "bool",
            "default": False,
            "description": "Use faster-whisper implementation (requires faster-whisper package)",
        },
        "use_longest_transcript_on_fail": {
            "type": "bool",
            "default": False,
            "description": "If no candidate passes threshold, use the one with longest transcript",
        },
    },
}
