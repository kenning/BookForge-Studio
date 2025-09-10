"""
Step: Set Approximate Chunk Length
"""

import random
import numpy as np
import torch

from backend.core.data_types.step_context import StepContext
from backend.core.utils import logger


async def process(context: StepContext):
    approximate_min_chunk_length = context.parameters.get(
        "approximate_min_chunk_length", None
    )

    if approximate_min_chunk_length is not None:
        # Default is very high of 9999999 so only set this if it's provided
        context.approximate_min_chunk_length = approximate_min_chunk_length


# Step metadata
STEP_METADATA = {
    "name": "set_approximate_min_chunk_length",
    "display_name": "Set Approximate Min Chunk Length",
    "description": "Sets approximate minimum chunk length for generation."
    + "Difficult to explain but a critical part of this application. "
    + "Generally, these models perform worse on longer segments of text. Setting this to "
    + "20 for example will try to get the model to generally split audio into chunks of "
    + "20 *words* or less. ",
    "input_type": "parameter",
    "output_type": "parameter",
    "category": "parameter-setting",
    "step_type": "pre_generation_step",
    "version": "1.0.0",
    "parameters": {
        "approximate_min_chunk_length": {
            "type": "int",
            "default": 20,
            "min": 0,
            "description": "Number of WORDS (not characters!)",
        }
    },
}
