"""
Step: Remove Extra Spaces

This step removes extra whitespace from text, including multiple spaces,
tabs, and newlines, leaving only single spaces between words.
"""

import re


from backend.core.data_types.step_context import StepContext


async def process(context: StepContext):
    """
    Process the input by removing extra whitespace.

    Args:
        context: StepContext containing current text state
    """

    cleaned_array = []
    for text in context.multiple_speaker_text_array:
        cleaned = re.sub(r"\s+", " ", text)
        cleaned_array.append(cleaned.strip())
    context.multiple_speaker_text_array = cleaned_array


# Step metadata - this is what gets exposed via the API
STEP_METADATA = {
    "name": "remove_extra_spaces",
    "display_name": "Remove Extra Spaces",
    "description": "Removes extra whitespace from text, leaving only single spaces between words",
    "input_type": "string",
    "output_type": "string",
    "category": "text-processing",
    "step_type": "pre_generation_step",
    "version": "1.0.0",
}
