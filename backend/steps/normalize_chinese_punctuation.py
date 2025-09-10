"""
Step: Normalize Chinese Punctuation

Converts Chinese (full-width) punctuation marks to English (half-width) equivalents.
"""

from backend.core.data_types.step_context import StepContext


def normalize_chinese_punctuation(text):
    """Convert Chinese (full-width) punctuation marks to English (half-width) equivalents."""
    chinese_to_english_punct = {
        "，": ", ",  # comma
        "。": ".",  # period
        "：": ":",  # colon
        "；": ";",  # semicolon
        "？": "?",  # question mark
        "！": "!",  # exclamation mark
        "（": "(",  # left parenthesis
        "）": ")",  # right parenthesis
        "【": "[",  # left square bracket
        "】": "]",  # right square bracket
        "《": "<",  # left angle quote
        "》": ">",  # right angle quote
        """: '"',  # left double quotation
        """: '"',  # right double quotation
        "'": "'",  # left single quotation
        "'": "'",  # right single quotation
        "、": ",",  # enumeration comma
        "—": "-",  # em dash
        "…": "...",  # ellipsis
        "·": ".",  # middle dot
        "「": '"',  # left corner bracket
        "」": '"',  # right corner bracket
        "『": '"',  # left double corner bracket
        "』": '"',  # right double corner bracket
    }

    for zh_punct, en_punct in chinese_to_english_punct.items():
        text = text.replace(zh_punct, en_punct)

    return text


async def process(context: StepContext):
    """
    Process the input by normalizing Chinese punctuation to English equivalents.

    Args:
        context: StepContext containing current text state
    """
    # Process each text in the array
    normalized_texts = []
    for text in context.multiple_speaker_text_array:
        normalized_text = normalize_chinese_punctuation(text)
        normalized_texts.append(normalized_text)

    context.multiple_speaker_text_array = normalized_texts


# Step metadata
STEP_METADATA = {
    "name": "normalize_chinese_punctuation",
    "display_name": "Normalize Chinese Punctuation",
    "description": "Converts Chinese (full-width) punctuation marks to English (half-width) equivalents",
    "input_type": "string",
    "output_type": "string",
    "category": "text-processing",
    "step_type": "pre_generation_step",
    "version": "1.0.0",
}
