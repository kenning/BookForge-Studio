"""
Step: Convert Text to Lowercase

This step converts any input text to lowercase.
"""

from backend.core.data_types.step_context import StepContext


async def process(context: StepContext):
    """
    Process the input by converting it to lowercase.

    Args:
        context: StepContext containing current text state
    """
    lowercase_array = []
    for text in context.multiple_speaker_text_array:
        lowercase_array.append(text.lower())
    context.multiple_speaker_text_array = lowercase_array


# Step metadata - this is what gets exposed via the API
STEP_METADATA = {
    "name": "to_lowercase",
    "display_name": "Convert to Lowercase",
    "description": "Converts input text to lowercase",
    "input_type": "string",
    "output_type": "string",
    "category": "text-processing",
    "step_type": "pre_generation_step",
    "version": "1.0.0",
}
