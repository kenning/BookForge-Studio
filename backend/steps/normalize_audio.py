"""
Step: Normalize Audio

This step normalizes audio using ffmpeg with EBU R128 or peak normalization methods.
"""

import os
import tempfile
import ffmpeg
from backend.core.data_types.step_context import StepContext


def normalize_with_ffmpeg(input_wav, output_wav, method="ebu", i=-24, tp=-2, lra=7):
    """
    Normalize audio using ffmpeg with different methods.

    Args:
        input_wav: Input audio file path
        output_wav: Output audio file path
        method: Normalization method ("ebu" or "peak")
        i: Integrated loudness target for EBU (LUFS)
        tp: True peak target for EBU (dBFS)
        lra: Loudness range for EBU (LU)
    """
    if method == "ebu":
        loudnorm = f"loudnorm=I={i}:TP={tp}:LRA={lra}"
        (
            ffmpeg.input(input_wav)
            .output(output_wav, af=loudnorm)
            .overwrite_output()
            .run(quiet=True)
        )
    elif method == "peak":
        (
            ffmpeg.input(input_wav)
            .output(output_wav, af="dynaudnorm")
            .overwrite_output()
            .run(quiet=True)
        )
    else:
        raise ValueError(f"Unknown normalization method: {method}")


async def process(context: StepContext):
    """
    Normalize the current audio using ffmpeg.

    Args:
        context: StepContext containing audio and parameters
    """
    # Determine which audio file to normalize
    input_audio_path = None

    if context.current_audio and os.path.exists(context.current_audio):
        input_audio_path = context.current_audio
    elif context.audio_candidates and len(context.audio_candidates) > 0:
        # Find the first existing candidate
        for candidate in context.audio_candidates:
            if candidate and os.path.exists(candidate):
                input_audio_path = candidate
                break

    if not input_audio_path:
        raise Exception("No audio available for normalization")

    # Get normalization parameters
    method = context.parameters.get("norm_method", "ebu")
    i_value = context.parameters.get("norm_i", -24)
    tp_value = context.parameters.get("norm_tp", -2)
    lra_value = context.parameters.get("norm_lra", 7)

    # Create temporary output file in the same directory as the input
    input_dir = os.path.dirname(input_audio_path)
    input_name = os.path.splitext(os.path.basename(input_audio_path))[0]
    output_path = os.path.join(input_dir, f"{input_name}_normalized.wav")

    try:
        # Run normalization
        normalize_with_ffmpeg(
            input_audio_path,
            output_path,
            method=method,
            i=i_value,
            tp=tp_value,
            lra=lra_value,
        )

        # Verify output file was created
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise Exception("Normalization failed - no output file generated")

        # Replace the input with normalized output
        os.replace(output_path, input_audio_path)

        # Update context to point to the normalized file
        if context.current_audio == input_audio_path:
            # Current audio was normalized, path stays the same
            pass
        elif input_audio_path in context.audio_candidates:
            # A candidate was normalized, update that candidate
            candidate_index = context.audio_candidates.index(input_audio_path)
            context.audio_candidates[candidate_index] = input_audio_path

        # If current_audio was None, set it to the normalized file
        if not context.current_audio:
            context.current_audio = input_audio_path

    except ffmpeg.Error as e:
        # Clean up temp file on error
        if os.path.exists(output_path):
            os.remove(output_path)
        raise Exception(f"FFmpeg normalization failed: {e}")
    except Exception as e:
        # Clean up temp file on error
        if os.path.exists(output_path):
            os.remove(output_path)
        raise Exception(f"Audio normalization error: {str(e)}")


# Step metadata
STEP_METADATA = {
    "name": "normalize_audio",
    "display_name": "Normalize Audio",
    "description": "Normalizes audio using ffmpeg with EBU R128 or peak normalization",
    "input_type": "audio",
    "output_type": "audio",
    "category": "audio-processing",
    "step_type": "post_generation_step",
    "version": "1.0.0",
    "parameters": {
        "norm_method": {
            "type": "str",
            "default": "ebu",
            "options": ["ebu", "peak"],
            "description": "Normalization method: EBU R128 loudness or peak normalization",
        },
        "norm_i": {
            "type": "float",
            "default": -24,
            "min": -70,
            "max": -5,
            "description": "Integrated loudness target in LUFS (EBU method only)",
        },
        "norm_tp": {
            "type": "float",
            "default": -2,
            "min": -9,
            "max": 0,
            "description": "True peak target in dBFS (EBU method only)",
        },
        "norm_lra": {
            "type": "float",
            "default": 7,
            "min": 1,
            "max": 50,
            "description": "Loudness range target in LU (EBU method only)",
        },
    },
}
