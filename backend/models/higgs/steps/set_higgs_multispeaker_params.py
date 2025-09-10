"""
Step: Set Higgs Multi-Speaker Parameters

This step sets parameters for multi-speaker Higgs audio generation.
"""


async def process(context):
    """
    Set Higgs multi-speaker audio generation parameters.

    Args:
        context: StepContext to set audio generation parameters
    """
    # Set default values if not already set
    if "max_new_tokens" not in context.parameters:
        context.parameters["max_new_tokens"] = 2048

    if "temperature" not in context.parameters:
        context.parameters["temperature"] = 0.5

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

    if "chunk_method" not in context.parameters:
        context.parameters["chunk_method"] = None

    if "chunk_max_word_num" not in context.parameters:
        context.parameters["chunk_max_word_num"] = 200

    if "chunk_max_num_turns" not in context.parameters:
        context.parameters["chunk_max_num_turns"] = 1


# Step metadata
STEP_METADATA = {
    "name": "set_higgs_multispeaker_params",
    "display_name": "Set Higgs Multi-Speaker Parameters",
    "description": "Sets parameters for multi-speaker Higgs audio generation",
    "input_type": "parameter",
    "output_type": "parameter",
    "category": "parameter-setting",
    "step_type": "start_step",
    "multi-speaker": True,
    "version": "1.0.0",
    "model_requirement": "higgs",
    "parameters": {
        "max_new_tokens": {
            "type": "int",
            "default": 2048,
            "min": 512,
            "max": 8192,
            "description": "Maximum new tokens to generate (higher for multi-speaker)",
        },
        "temperature": {
            "type": "float",
            "default": 0.5,
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
        "chunk_method": {
            "type": "str",
            "default": None,
            "description": "Chunking method: 'speaker', 'word', or None",
        },
        "chunk_max_word_num": {
            "type": "int",
            "default": 200,
            "min": 50,
            "max": 500,
            "description": "Maximum words per chunk when using word chunking",
        },
        "chunk_max_num_turns": {
            "type": "int",
            "default": 1,
            "min": 1,
            "max": 10,
            "description": "Maximum turns per chunk when using speaker chunking",
        },
    },
}
