"""
Step: Set Number of Candidates

This step configures the number of audio candidates to generate for selection.
"""

from backend.core.data_types.step_context import StepContext


async def process(context: StepContext):
    """
    Set number of candidates parameter.

    Args:
        context: StepContext to set candidate generation parameters
    """
    # The num_candidates parameter is now a typed field on the context object
    # It can be set during initialization and accessed directly
    # No need to set defaults here as they are defined in the StepContext class
    pass


# Step metadata
STEP_METADATA = {
    "name": "set_num_candidates",
    "display_name": "Set Number of Candidates",
    "description": "Configures the number of audio candidates to generate for selection",
    "input_type": "parameter",
    "output_type": "parameter",
    "category": "parameter-setting",
    "step_type": "pre_generation_step",
    "version": "1.0.0",
    "parameters": {
        "num_candidates": {
            "type": "int",
            "default": 3,
            "min": 1,
            "max": 10,
            "description": "Number of audio candidates to generate for selection",
        },
    },
}
