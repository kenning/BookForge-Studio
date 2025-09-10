from backend.core.utils.logger import get_logger

logger = get_logger(__name__)


def provide_model_metadata():
    return {
        "name": "Dia",
        "voice_clone_tips": [
            "Dia clips require transcription. It benefits from proper capitalization, punctuation, "
            + "and cues like (laughs) or (coughs).",
            "Voice clips should be short (5-10 seconds).",
            "Dia is VERY expressive, maybe too much; try to keep temperature pretty low and avoid exclamation marks.",
        ],
        "default_workflows": [
            {
                "name": "Default Dia Workflow",
                "steps": [
                    "set_dia_params",
                    # "set_parallel_processing",
                    "set_approximate_min_chunk_length",
                    "set_num_candidates",
                    "set_seed",
                    "remove_extra_spaces",
                    "fix_dot_letters",
                    "generate_dia_audio",
                    "whisper_check",
                    "normalize_audio",
                    "export_audio",
                ],
            }
        ],
    }
