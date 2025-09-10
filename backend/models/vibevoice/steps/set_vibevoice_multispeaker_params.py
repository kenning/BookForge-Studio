"""
Step: Set VibeVoice Multi-Speaker Parameters

This step sets parameters for multi-speaker VibeVoice audio generation.
"""

default_cfg_scale = 1.6


async def process(context):
    """
    Set VibeVoice multi-speaker audio generation parameters.

    Args:
        context: StepContext to set audio generation parameters
    """
    # Set default values if not already set
    if "cfg_scale" not in context.parameters:
        context.parameters["cfg_scale"] = default_cfg_scale


# Step metadata
STEP_METADATA = {
    "name": "set_vibevoice_multispeaker_params",
    "display_name": "Set VibeVoice Multi-Speaker Parameters",
    "description": "Sets parameters for multi-speaker VibeVoice audio generation",
    "input_type": "parameter",
    "output_type": "parameter",
    "category": "parameter-setting",
    "step_type": "start_step",
    "multi-speaker": True,
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
