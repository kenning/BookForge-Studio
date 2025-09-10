"""
Step: Set Parallel Processing

This step configures parallel processing settings for audio generation.
"""

from backend.core.data_types.step_context import StepContext


async def process(context: StepContext):
    """
    Set parallel processing parameters.

    Args:
        context: StepContext to set parallel processing parameters
    """
    # Parameters are now typed fields on the context object
    # They can be set during initialization and accessed directly
    # No need to set defaults here as they are defined in the ProcessingContext class
    pass


# Step metadata
STEP_METADATA = {
    "name": "set_parallel_processing",
    "display_name": "Set Parallel Processing",
    "description": "Configures parallel processing settings for audio generation",
    "input_type": "parameter",
    "output_type": "parameter",
    "category": "parameter-setting",
    "step_type": "pre_generation_step",
    "version": "1.0.0",
    "parameters": {
        "enable_parallel": {
            "type": "bool",
            "default": True,
            "description": "Enable parallel processing of audio chunks",
        },
        "num_parallel_workers": {
            "type": "int",
            "default": 4,
            "min": 1,
            "max": 16,
            "description": "Number of parallel workers to use",
        },
    },
}
