"""
Step: Normalize Text for Higgs

Normalizes text for Higgs audio generation following specific patterns.
Includes Chinese punctuation normalization and audio tag processing.
"""

from backend.core.data_types.step_context import StepContext


def normalize_text_for_higgs(text: str) -> str:
    """Normalize text for Higgs generation following the exact patterns from the example."""

    # Basic normalizations from the Higgs example
    text = text.replace("(", " ")
    text = text.replace(")", " ")
    text = text.replace("°F", " degrees Fahrenheit")
    text = text.replace("°C", " degrees Celsius")

    # Handle special audio tags - EXACT same order as examples
    for tag, replacement in [
        ("[laugh]", "<SE>[Laughter]</SE>"),
        ("[humming start]", "<SE>[Humming]</SE>"),
        ("[humming end]", "<SE_e>[Humming]</SE_e>"),
        ("[music start]", "<SE_s>[Music]</SE_s>"),
        ("[music end]", "<SE_e>[Music]</SE_e>"),
        ("[music]", "<SE>[Music]</SE>"),
        ("[sing start]", "<SE_s>[Singing]</SE_s>"),
        ("[sing end]", "<SE_e>[Singing]</SE_e>"),
        ("[applause]", "<SE>[Applause]</SE>"),
        ("[cheering]", "<SE>[Cheering]</SE>"),
        ("[cough]", "<SE>[Cough]</SE>"),
    ]:
        text = text.replace(tag, replacement)

    # Clean up whitespace - exact same logic as examples
    lines = text.split("\n")
    text = "\n".join([" ".join(line.split()) for line in lines if line.strip()])
    text = text.strip()

    # Ensure proper punctuation - exact same logic as examples
    if not any(
        [
            text.endswith(c)
            for c in [".", "!", "?", ",", ";", '"', "'", "</SE_e>", "</SE>"]
        ]
    ):
        text += "."

    return text


async def process(context: StepContext):
    """
    Process the input by normalizing text for Higgs audio generation.

    Args:
        context: StepContext containing current text state
    """
    # Process each text in the array
    normalized_texts = []
    for text in context.multiple_speaker_text_array:
        normalized_text = normalize_text_for_higgs(text)
        normalized_texts.append(normalized_text)

    context.multiple_speaker_text_array = normalized_texts


# Step metadata
STEP_METADATA = {
    "name": "normalize_text_for_higgs",
    "display_name": "Normalize Text for Higgs",
    "description": "Normalizes text for Higgs audio generation with audio tag processing. Read the code on this one if interested.",
    "input_type": "string",
    "output_type": "string",
    "category": "text-processing",
    "step_type": "pre_generation_step",
    "version": "1.0.0",
}
