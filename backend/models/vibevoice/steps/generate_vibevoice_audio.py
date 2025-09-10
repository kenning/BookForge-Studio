"""
Step: Generate VibeVoice Audio

Generates audio using the VibeVoice model microservice.
Supports both single-speaker and multi-speaker workflows.
"""

from backend.core.data_types.step_context import StepContext
from backend.core.utils.generation_utils import generate_candidates_with_service_calls

# Import logging utilities
from backend.core.utils.logger import get_logger

logger = get_logger(__name__)


async def process(context: StepContext):
    """
    Generate audio using VibeVoice model microservice.
    Supports both single-speaker and multi-speaker workflows.

    Args:
        context: StepContext containing texts, voice clone paths, and parameters
    """
    # Get texts from context
    texts = context.multiple_speaker_text_array or []

    if not texts:
        raise Exception("No text input available for VibeVoice audio generation")

    logger.info(f"Starting VibeVoice audio generation for {len(texts)} texts")
    logger.info(f"Is multi-speaker: {context.is_multi_speaker}")
    logger.info(f"Voice clone paths: {context.voice_clone_paths}")
    logger.info(f"Generating {context.num_candidates} candidates")
    logger.info(f"Multiple speaker text array: {context.multiple_speaker_text_array}")

    print("context.audio_transcriptions", context.audio_transcriptions)
    print("context.voice_clone_paths", context.voice_clone_paths)
    await generate_candidates_with_service_calls(
        model_name="vibevoice",
        context=context,
        texts=texts,
        voice_paths=context.voice_clone_paths,
        audio_transcriptions=context.audio_transcriptions
        or ["" for _ in context.voice_clone_paths],
    )


# Step metadata
STEP_METADATA = {
    "name": "generate_vibevoice_audio",
    "display_name": "Generate VibeVoice Audio",
    "description": "Generates audio using VibeVoice model (supports both single and multi-speaker)",
    "input_type": "string",
    "output_type": "audio",
    "category": "audio-generation",
    "step_type": "generation_step",
    "version": "1.0.0",
    "model_requirement": "vibevoice",
}
