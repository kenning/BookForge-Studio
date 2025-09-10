from backend.core.utils.logger import get_logger

logger = get_logger(__name__)


def provide_model_metadata():
    return {
        "name": "Chatterbox",
        "voice_clone_tips": [
            "Chatterbox clips can be up to 60 seconds. They do not require transcription."
        ],
        "default_workflows": [
            {
                "name": "Default Chatterbox Workflow",
                "steps": [
                    "set_chatterbox_params",
                    # "set_parallel_processing",
                    "set_approximate_min_chunk_length",
                    "set_num_candidates",
                    "set_seed",
                    "remove_extra_spaces",
                    "to_lowercase",
                    "fix_dot_letters",
                    "generate_chatterbox_audio",
                    "whisper_check",
                    "normalize_audio",
                    "export_audio",
                ],
            }
        ],
    }
