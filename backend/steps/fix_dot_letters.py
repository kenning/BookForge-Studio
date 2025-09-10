"""
Step: Fix Dot Letters

This step fixes letter-dot sequences like "A.B.C." to "A B C".
"""

import re

from backend.core.data_types.step_context import StepContext


async def process(context: StepContext):
    """
    Process the input by fixing letter-dot sequences.

    Args:
        context: StepContext containing current text state
    """

    def replacer(match):
        cleaned = match.group(0).rstrip(".")
        letters = cleaned.split(".")
        return " ".join(letters)

    fixed_array = []
    for text in context.multiple_speaker_text_array:
        fixed = re.sub(r"\b(?:[A-Za-z]\.){2,}", replacer, text)
        fixed_array.append(fixed)
    context.multiple_speaker_text_array = fixed_array


# Step metadata
STEP_METADATA = {
    "name": "fix_dot_letters",
    "display_name": "Fix Dot Letters",
    "description": "Fixes letter-dot sequences like 'A.B.C.' to 'A B C'",
    "input_type": "string",
    "output_type": "string",
    "category": "text-processing",
    "step_type": "pre_generation_step",
    "version": "1.0.0",
}
