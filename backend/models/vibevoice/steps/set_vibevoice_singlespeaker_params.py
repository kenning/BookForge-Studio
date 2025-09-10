"""
Step: Set VibeVoice Single-Speaker Parameters

This step sets parameters for single-speaker VibeVoice audio generation.
"""

default_cfg_scale = 1.6
default_flash_attention = False


async def process(context):
    """
    Set VibeVoice single-speaker audio generation parameters.

    Args:
        context: StepContext to set audio generation parameters
    """
    # Set default values if not already set
    if "cfg_scale" not in context.parameters:
        context.parameters["cfg_scale"] = default_cfg_scale


# Step metadata
STEP_METADATA = {
    "name": "set_vibevoice_singlespeaker_params",
    "display_name": "Set VibeVoice Single-Speaker Parameters",
    "description": "Sets parameters for single-speaker VibeVoice audio generation",
    "input_type": "parameter",
    "output_type": "parameter",
    "category": "parameter-setting",
    "step_type": "start_step",
    "multi-speaker": False,
    "version": "1.0.0",
    "model_requirement": "vibevoice",
    "parameters": {
        "cfg_scale": {
            "type": "float",
            "default": default_cfg_scale,
            "min": 0.1,
            "max": 5.0,
            "description": "CFG (Classifier-Free Guidance) scale for generation quality",
        },
    },
}
