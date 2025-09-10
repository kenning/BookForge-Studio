"""
Step: Set Seed

This step sets the random seed for reproducible generation.
"""

import random
import numpy as np
import torch

from backend.core.data_types.step_context import StepContext
from backend.core.utils import logger


async def process(context: StepContext):
    seed = context.seed

    # If seed is 0, generate a random seed
    if seed == 0:
        seed = random.randint(1, 2**32 - 1)
        logger.info(f"Randomly etting seed to {seed}")

    # Set the seed in various random number generators
    torch.manual_seed(seed)
    random.seed(seed)
    np.random.seed(seed)

    # Check if CUDA is available and set CUDA seed
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)

    # Store the actual seed used
    context.actual_seed = seed


# Step metadata
STEP_METADATA = {
    "name": "set_seed",
    "display_name": "Set Seed",
    "description": "Sets random seed for reproducible generation",
    "input_type": "parameter",
    "output_type": "parameter",
    "category": "parameter-setting",
    "step_type": "pre_generation_step",
    "version": "1.0.0",
    "parameters": {
        "seed": {
            "type": "int",
            "default": 0,
            "description": "Random seed (0 for random seed)",
        }
    },
}
