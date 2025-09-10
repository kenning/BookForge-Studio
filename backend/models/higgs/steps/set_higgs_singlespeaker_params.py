"""
Step: Set Higgs Single-Speaker Parameters

This step sets parameters for single-speaker Higgs audio generation.
"""


async def process(context):
    """
    Set Higgs single-speaker audio generation parameters.

    Args:
        context: StepContext to set audio generation parameters
    """
    # Set default values if not already set
    if "max_new_tokens" not in context.parameters:
        context.parameters["max_new_tokens"] = 1024

    if "temperature" not in context.parameters:
        context.parameters["temperature"] = 0.3

    if "top_p" not in context.parameters:
        context.parameters["top_p"] = 0.95

    if "top_k" not in context.parameters:
        context.parameters["top_k"] = 50

    if "ras_win_len" not in context.parameters:
        context.parameters["ras_win_len"] = 7

    if "ras_win_max_num_repeat" not in context.parameters:
        context.parameters["ras_win_max_num_repeat"] = 2

    if "scene_prompt" not in context.parameters:
        context.parameters["scene_prompt"] = "Audio is recorded from a quiet room."


# Step metadata
STEP_METADATA = {
    "name": "set_higgs_singlespeaker_params",
    "display_name": "Set Higgs Single-Speaker Parameters",
    "description": "Sets parameters for single-speaker Higgs audio generation",
    "input_type": "parameter",
    "output_type": "parameter",
    "category": "parameter-setting",
    "step_type": "start_step",
    "multi-speaker": False,
    "version": "1.0.0",
    "model_requirement": "higgs",
    "parameters": {
        "max_new_tokens": {
            "type": "int",
            "default": 1024,
            "min": 256,
            "max": 4096,
            "description": "Maximum new tokens to generate",
        },
        "temperature": {
            "type": "float",
            "default": 0.3,
            "min": 0.1,
            "max": 2.0,
            "description": "Sampling temperature for generation",
        },
        "top_p": {
            "type": "float",
            "default": 0.95,
            "min": 0.1,
            "max": 1.0,
            "description": "Nucleus sampling threshold",
        },
        "top_k": {
            "type": "int",
            "default": 50,
            "min": 1,
            "max": 200,
            "description": "Top-k sampling parameter",
        },
        "ras_win_len": {
            "type": "int",
            "default": 7,
            "min": 0,
            "max": 20,
            "description": "RAS sampling window length (0 to disable)",
        },
        "ras_win_max_num_repeat": {
            "type": "int",
            "default": 2,
            "min": 1,
            "max": 10,
            "description": "Maximum number of RAS window repeats",
        },
        "scene_prompt": {
            "type": "str",
            "default": "Audio is recorded from a quiet room.",
            "description": "Scene description for audio generation context",
        },
    },
}
