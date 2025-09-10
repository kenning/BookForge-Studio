"""
Step: Export Audio

This step exports the current audio to files in specified formats.
"""

import os
import datetime
import ffmpeg
from pydub import AudioSegment
from backend.core.config import OUTPUT_DIR
from pathlib import Path
from backend.core.data_types.step_context import StepContext

# Import logging utilities
from backend.core.utils.logger import get_logger

logger = get_logger(__name__)


async def process(context: StepContext):
    """
    Export the current audio to files in specified formats.

    Args:
        context: StepContext containing audio and parameters
    """
    logger.info("Starting audio export process")
    audio = context.current_audio
    if audio is None:
        if not context.audio_candidates or len(context.audio_candidates) == 0:
            raise Exception("No audio available for export")
        audio = context.audio_candidates[0]
        logger.info(f"Using first audio candidate: {audio}")

    output_subfolder = context.output_subfolder
    output_file_name = context.output_file_name

    if len(output_file_name) == 0:
        raise Exception("Output file name is empty")

    logger.info(f"Exporting audio in format: wav")
    if output_subfolder:
        logger.info(f"Output subfolder: {output_subfolder}")

    # Setup output directory
    final_output_dir = OUTPUT_DIR
    if output_subfolder:
        # Clean the subfolder path to prevent directory traversal
        subfolder_parts = [
            part.strip()
            for part in output_subfolder.split("/")
            if part.strip() and ".." not in part
        ]
        if subfolder_parts:
            final_output_dir = final_output_dir / Path(*subfolder_parts)
            final_output_dir.mkdir(parents=True, exist_ok=True)

    # Export in requested formats
    format_lower = "wav"
    final_path = final_output_dir / f"{output_file_name}.{format_lower}"
    logger.info(f"Exporting to {format_lower.upper()}: {final_path}")

    if format_lower == "wav":
        # For WAV, check if input is already WAV format
        if audio.lower().endswith(".wav"):
            # Copy directly
            import shutil

            shutil.copy2(audio, final_path)
        else:
            # Convert to WAV using ffmpeg
            (
                ffmpeg
                .input(audio)
                .output(str(final_path))
                .overwrite_output()
                .run(quiet=True)
            )
    else:
        # Convert using pydub
        # Load from input file directly
        audio = AudioSegment.from_file(audio)

        export_kwargs = {}
        if format_lower == "mp3":
            export_kwargs["bitrate"] = "320k"

        audio.export(str(final_path), format=format_lower, **export_kwargs)

    # Construct relative path for response
    if output_subfolder:
        relative_path = f"output/{output_subfolder}/{output_file_name}.{format_lower}"
    else:
        relative_path = f"output/{output_file_name}.{format_lower}"
    print("relative_path", relative_path)
    context.output_files.append(relative_path)
    logger.info(f"Successfully exported {format_lower.upper()} file: {relative_path}")

    logger.info(f"Audio export completed. Generated {len(context.output_files)} files")


# Step metadata
STEP_METADATA = {
    "name": "export_audio",
    "display_name": "Export Audio",
    "description": "Exports audio to files in specified formats",
    "input_type": "audio",
    "output_type": "files",
    "category": "export",
    "step_type": "post_generation_step",
    "version": "1.0.0",
    "parameters": {
        # These parameters should not be set by the user.
    },
}
