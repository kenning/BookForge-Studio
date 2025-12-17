"""
Step: Set Chatterbox Parameters

This step sets various parameters for the Chatterbox TTS model generation.
"""


async def process(context):
    """
    Set Chatterbox TTS generation parameters.

    Args:
        context: StepContext to set TTS parameters
    """
    # Set default values if not already set
    if "cb_turbo" not in context.parameters:
        context.parameters["cb_turbo"] = True

    # if "cb_multilingual" not in context.parameters:
    #     context.parameters["cb_multilingual"] = False

    if "exaggeration" not in context.parameters:
        context.parameters["exaggeration"] = 0.5

    if "cfg" not in context.parameters:
        context.parameters["cfg"] = 0.5

    if "temperature" not in context.parameters:
        context.parameters["temperature"] = 0.75

    if "min_p" not in context.parameters:
        context.parameters["min_p"] = 0.05

    if "top_p" not in context.parameters:
        context.parameters["top_p"] = 1.0

    if "repetition_penalty" not in context.parameters:
        context.parameters["repetition_penalty"] = 1.2

    # if "disable_watermark" not in context.parameters:
    #     context.parameters["disable_watermark"] = False

    if "max_attempts_per_candidate" not in context.parameters:
        context.parameters["max_attempts_per_candidate"] = 3


# Step metadata
STEP_METADATA = {
    "name": "set_chatterbox_params",
    "display_name": "Set Chatterbox Parameters",
    "description": "Sets parameters for Chatterbox TTS model generation",
    "input_type": "parameter",
    "output_type": "parameter",
    "category": "parameter-setting",
    "step_type": "start_step",
    "multi-speaker": False,
    "version": "1.0.0",
    "model_requirement": "chatterbox",
    "parameters": {
        "cb_turbo": {
            "type": "bool",
            "default": True,
            "description": "Use Chatterbox TURBO model!",
        },
        # "cb_multilingual": {
        #     "type": "bool",
        #     "default": False,
        #     "description": "Use Chatterbox Multilingual model",
        # },
        "exaggeration": {
            "type": "float",
            "default": 0.5,
            "min": 0.0,
            "max": 1.0,
            "description": "Voice exaggeration level",
        },
        "cfg": {
            "type": "float",
            "default": 0.5,
            "description": "Classifier-free guidance weight",
        },
        "temperature": {
            "type": "float",
            "default": 0.75,
            "min": 0.1,
            "max": 2.0,
            "description": "Sampling temperature",
        },
        "min_p": {
            "type": "float",
            "default": 0.05,
            "description": "Minimum probability threshold",
        },
        "top_p": {
            "type": "float",
            "default": 1.0,
            "description": "Nucleus sampling threshold",
        },
        "repetition_penalty": {
            "type": "float",
            "default": 1.2,
            "description": "Repetition penalty",
        },
    },
}
