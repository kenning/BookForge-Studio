"""
Step: Use Auto Editor

This step applies auto-editor to remove silence and clean up audio.
"""

import os
import subprocess
import tempfile
#import torchaudio
from backend.core.data_types.step_context import StepContext


async def process(context: StepContext):
    """
    Process audio using auto-editor to remove silence and clean up.

    Args:
        context: StepContext containing audio and parameters
    """
    audio = context.current_audio
    if audio is None:
        if not context.audio_candidates or len(context.audio_candidates) == 0:
            raise Exception("No audio available for auto-editor processing")
        audio = context.audio_candidates[0]

    # Get auto-editor parameters
    threshold = context.parameters.get("ae_threshold", 0.04)
    margin = context.parameters.get("ae_margin", 0.1)

    # Input file is already available as a path
    input_path = context.current_audio

    # Create temporary output file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as output_file:
        output_path = output_file.name

    try:

        # Run auto-editor
        auto_editor_cmd = [
            "auto-editor",
            "--edit",
            f"audio:threshold={threshold}",
            "--margin",
            f"{margin}s",
            "--export",
            "audio",
            input_path,
            "-o",
            output_path,
        ]

        result = subprocess.run(
            auto_editor_cmd, check=True, capture_output=True, text=True
        )

        # Set the processed audio file as the new current audio
        if os.path.exists(output_path):
            context.set_audio(output_path)
        else:
            raise Exception("Auto-editor did not produce output file")

    except subprocess.CalledProcessError as e:
        raise Exception(f"Auto-editor processing failed: {e.stderr}")
    except Exception as e:
        raise Exception(f"Auto-editor processing error: {str(e)}")
    finally:
        # Clean up temporary output file only if there was an error
        # On success, the output file becomes the new current_audio
        if not context.current_audio or context.current_audio != output_path:
            if os.path.exists(output_path):
                os.remove(output_path)


# Step metadata
STEP_METADATA = {
    "name": "use_auto_editor",
    "display_name": "Use Auto Editor",
    "description": "Applies auto-editor to remove silence and clean up audio",
    "input_type": "audio",
    "output_type": "audio",
    "category": "audio-processing",
    "step_type": "post_generation_step",
    "version": "1.0.0",
    "parameters": {
        "ae_threshold": {
            "type": "float",
            "default": 0.04,
            "min": 0.01,
            "max": 1.0,
            "description": "Audio threshold for silence detection",
        },
        "ae_margin": {
            "type": "float",
            "default": 0.1,
            "min": 0.0,
            "max": 5.0,
            "description": "Margin (in seconds) to keep around non-silent audio",
        },
    },
}
