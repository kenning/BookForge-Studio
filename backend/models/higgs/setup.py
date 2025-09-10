from backend.core.utils.logger import get_logger

logger = get_logger(__name__)


def provide_model_metadata():
    return {
        "name": "Higgs",
        "voice_clone_tips": [
            "The Higgs model is powerful and supports single and multi-speaker workflows, "
            + "Chinese, and has many other features, but requires tons of VRAM (24GB).",
            "Higgs models require a transcription. Audio clips can be quite long.",
            "Higgs has multi-speaker voice clone capabilities, but it doesn't always get the "
            + "right voice. It works best with longer turns in "
            + "dialogue, and differentiated voices (female and male in dialogue for example).",
            "Higgs clips are still being tested for ideal settings...",
        ],
        "default_workflows": [
            {
                "name": "Default Higgs Single-Speaker Workflow",
                "steps": [
                    "set_higgs_singlespeaker_params",
                    "set_seed",
                    "set_approximate_min_chunk_length",
                    "remove_extra_spaces",
                    "fix_dot_letters",
                    "normalize_chinese_punctuation",
                    "normalize_text_for_higgs",
                    "generate_higgs_audio",
                    "normalize_audio",
                    "export_audio",
                ],
            },
            {
                "name": "Default Higgs Multi-Speaker Workflow",
                "steps": [
                    "set_higgs_multispeaker_params",
                    "set_seed",
                    "set_approximate_min_chunk_length",
                    "remove_extra_spaces",
                    "fix_dot_letters",
                    "normalize_chinese_punctuation",
                    "normalize_text_for_higgs",
                    "generate_higgs_audio",
                    "normalize_audio",
                    "export_audio",
                ],
            },
        ],
    }
