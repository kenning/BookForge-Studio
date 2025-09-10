"""
Step: Generate DIA Audio

Generates multi-speaker dialogue audio using the DIA model microservice.
"""

from backend.core.data_types.step_context import StepContext
from backend.core.utils.generation_utils import generate_candidates_with_service_calls

# Import logging utilities
from backend.core.utils.logger import get_logger

logger = get_logger(__name__)


async def process(context: StepContext):
    """
    Generate dialogue audio using DIA model microservice.

    Args:
        context: StepContext containing texts, voice clone paths, and speaker mapping
    """
    if context.is_multi_speaker is False:
        raise Exception("Dia must be a multi-speaker workflow.")

    # Determine input source - prioritize multiple_speaker_text_array for multi-speaker
    if context.multiple_speaker_text_array:
        texts = context.multiple_speaker_text_array
    else:
        raise Exception("No text input available for DIA audio generation")

    logger.info(f"Starting DIA audio generation for {len(texts)} texts")
    voice_paths = context.voice_clone_paths
    logger.info(f"Voice clone paths: {voice_paths}")
    logger.info(f"Generating {context.num_candidates} candidates")

    # Generate audio via DIA microservice
    await generate_candidates_with_service_calls(
        model_name="dia",
        context=context,
        texts=texts,
        voice_paths=voice_paths,
        audio_transcriptions=context.audio_transcriptions
        or ["" for _ in context.voice_clone_paths],
    )


# Step metadata
STEP_METADATA = {
    "name": "generate_dia_audio",
    "display_name": "Generate DIA Audio",
    "description": "Generates multi-speaker dialogue audio using DIA model",
    "input_type": "string",
    "output_type": "audio",
    "category": "audio-generation",
    "step_type": "generation_step",
    "version": "1.0.0",
    "model_requirement": "dia",
}
