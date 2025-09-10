from backend.core.utils.logger import get_logger

logger = get_logger(__name__)


def provide_model_metadata():
    return {
        "name": "VibeVoice",
        "voice_clone_tips": [
            "The VibeVoice model is Microsoft's latest text-to-speech model with excellent "
            + "voice cloning capabilities and multi-speaker support.",
            "VibeVoice works well with shorter audio clips (5-30 seconds) and doesn't require "
            + "transcriptions like some other models.",
            "VibeVoice has strong multi-speaker dialogue generation capabilities and maintains "
            + "speaker consistency across longer conversations.",
            "The model uses CFG (Classifier-Free Guidance) for generation quality control. "
            + "Higher CFG scale values (1.3-2.0) generally produce better quality audio.",
            "VibeVoice supports both sampling and greedy decoding, with greedy being the default "
            + "for more consistent results.",
        ],
        "default_workflows": [
            {
                "name": "Default VibeVoice Single-Speaker Workflow",
                "steps": [
                    "set_vibevoice_singlespeaker_params",
                    "set_seed",
                    # "set_approximate_min_chunk_length", # Vibevoice does not require chunking!
                    "remove_extra_spaces",
                    "fix_dot_letters",
                    "generate_vibevoice_audio",
                    "normalize_audio",
                    "export_audio",
                ],
            },
            {
                "name": "Default VibeVoice Multi-Speaker Workflow",
                "steps": [
                    "set_vibevoice_multispeaker_params",
                    "set_seed",
                    # "set_approximate_min_chunk_length", # Vibevoice does not require chunking!
                    "remove_extra_spaces",
                    "fix_dot_letters",
                    "generate_vibevoice_audio",
                    "normalize_audio",
                    "export_audio",
                ],
            },
        ],
    }
