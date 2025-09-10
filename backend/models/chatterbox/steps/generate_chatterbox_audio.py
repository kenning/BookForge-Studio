"""
Step: Generate Chatterbox Audio

Generates audio using the Chatterbox TTS model microservice.
"""

from backend.core.data_types.step_context import StepContext
from backend.core.utils.generation_utils import generate_candidates_with_service_calls

# Import logging utilities
from backend.core.utils.logger import get_logger

logger = get_logger(__name__)


async def process(context: StepContext):
    """
    Generate multiple audio candidates using Chatterbox TTS microservice.

    Args:
        context: StepContext containing text array and parameters
    """
    sentences = context.multiple_speaker_text_array or []

    if not sentences:
        raise Exception("No text array available for audio generation")

    logger.info(f"Starting Chatterbox audio generation for {len(sentences)} sentences")
    logger.info(f"Sentences: {sentences}")
    logger.info(f"Voice clone paths: {context.voice_clone_paths}")
    logger.info(f"Transcriptions: {context.audio_transcriptions}")
    logger.info(f"Generating {context.num_candidates} candidates")

    # Generate audio via Chatterbox microservice
    await generate_candidates_with_service_calls(
        model_name="chatterbox",
        context=context,
        texts=sentences,
        voice_paths=context.voice_clone_paths,
        audio_transcriptions=context.audio_transcriptions
        or ["" for _ in context.voice_clone_paths],
    )


# Step metadata
STEP_METADATA = {
    "name": "generate_chatterbox_audio",
    "display_name": "Generate Chatterbox Audio",
    "description": "Generates audio using Chatterbox TTS model",
    "input_type": "string",
    "output_type": "audio",
    "category": "audio-generation",
    "step_type": "generation_step",
    "version": "1.0.0",
    "model_requirement": "chatterbox",
}
