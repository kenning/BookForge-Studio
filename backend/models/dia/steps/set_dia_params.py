"""
Step: Set DIA Parameters

This step sets parameters for the DIA dialogue model generation.
"""


async def process(context):
    """
    Set DIA dialogue model generation parameters.

    Args:
        context: StepContext to set dialogue generation parameters
    """
    # Set default values if not already set
    if "max_new_tokens" not in context.parameters:
        context.parameters["max_new_tokens"] = 4096

    # if "temperature" not in context.parameters:
    #     context.parameters["temperature"] = 1.0

    # if "do_sample" not in context.parameters:
    #     context.parameters["do_sample"] = True

    # if "top_k" not in context.parameters:
    #     context.parameters["top_k"] = 50

    # if "top_p" not in context.parameters:
    #     context.parameters["top_p"] = 0.95


# Step metadata
STEP_METADATA = {
    "name": "set_dia_params",
    "display_name": "Set DIA Parameters",
    "description": "Sets parameters for DIA dialogue model generation",
    "input_type": "parameter",
    "output_type": "parameter",
    "category": "parameter-setting",
    "step_type": "start_step",
    "multi-speaker": True,
    "version": "1.0.0",
    "model_requirement": "dia",
    "parameters": {
        "max_new_tokens": {
            "type": "int",
            "default": 4096,
            "min": 256,
            "max": 32768,
            "description": "Maximum new tokens to generate (corresponds to ~2s at 256)",
        },
        "temperature": {
            "type": "float",
            "default": 1.4,
            "min": 0.1,
            "max": 2.0,
            "description": "Sampling temperature. Dia authors propose 1.8 but a little lower can "
            + "be better.",
        },
        "guidance_scale": {
            "type": "float",
            "default": 3.0,
            "min": 0.1,
            "description": "Guidance scale",
        },
        "top_k": {
            "type": "int",
            "default": 45,
            "min": 0,
            "max": 100,
            "description": "Top-k sampling parameter",
        },
        "top_p": {
            "type": "float",
            "default": 0.90,
            "min": 0,
            "max": 100,
            "description": "Top-p (nucleus) sampling parameter",
        },
    },
}
