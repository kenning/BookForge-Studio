"""
Step Context for TTS Pipeline

This module contains the StepContext class that flows through all pipeline steps.
It includes typed fields for common parameters and an untyped parameters dict for model-specific settings.
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
import tempfile
#import torchaudio


class StepContext(BaseModel):
    """Context object that flows through the pipeline steps with typed common parameters"""

    # Execution tracking
    execution_id: Optional[str] = None  # For tracking background execution

    # Original input text
    original_text_array: List[str]
    # Core processing state
    multiple_speaker_text_array: List[str]
    current_audio: Optional[str] = None  # File path instead of tensor
    audio_sample_rate: Optional[int] = None
    temp_dir: Optional[str] = None
    output_files: List[str] = Field(default_factory=list)

    # Common non-model-specific parameters (typed)
    enable_parallel: bool = False
    num_parallel_workers: int = 4
    seed: int = 0
    actual_seed: Optional[int] = None
    max_chars: int = 400
    output_subfolder: str = ""
    output_file_name: str = ""
    voice_clone_paths: Optional[List[str]] = None  # Voice clone paths (always a list)
    audio_transcriptions: Optional[List[str]] = (
        None  # Audio transcriptions (always a list)
    )
    num_candidates: int = 1
    approximate_min_chunk_length: int = 9999999

    # Step metadata fields (set by router)
    is_multi_speaker: bool = (
        False  # Whether current step supports multi-speaker generation
    )

    # Audio candidate storage (simplified to just file paths)
    audio_candidates: List[str] = Field(default_factory=list)
    debug_chunks: List[Dict[str, Any]] = Field(default_factory=list)
    debug_chunk_help_text: str = ""

    # Model-specific parameters (untyped dict for flexibility)
    parameters: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, initial_texts: List[str] = None, **data):
        # Always use multiple_speaker_text_array (list format) even for single text
        data["multiple_speaker_text_array"] = initial_texts
        data["original_text_array"] = initial_texts

        if "temp_dir" not in data:
            data["temp_dir"] = tempfile.mkdtemp()
        super().__init__(**data)

    def set_audio(self, audio_path: str, sample_rate: Optional[int] = None):
        """Set the current audio file path and optionally sample rate"""
        self.current_audio = audio_path


    @classmethod
    def from_request_parameters(
        cls,
        texts: List[List[str]],
        output_subfolder: str,
        output_file_name: str,
        parameters: Optional[Dict[str, Any]] = None,
        voice_clone_paths: Optional[List[str]] = None,
        audio_transcriptions: Optional[List[str]] = None,
        execution_id: Optional[str] = None,
    ) -> "StepContext":
        """
        Create a StepContext from API request parameters.

        Args:
            texts: List of input texts
            parameters: Optional parameter dictionary
            voice_clone_paths: Optional voice clone file paths
            audio_transcriptions: Optional audio transcriptions
            execution_id: Optional execution ID for tracking

        Returns:
            Configured StepContext instance
        """
        # Initialize typed parameters
        init_params = {}
        if parameters:
            typed_fields = cls.model_fields.keys()
            for key, value in parameters.items():
                if key in typed_fields:
                    init_params[key] = value

        # Set up voice clone and transcription parameters
        if voice_clone_paths:
            init_params["voice_clone_paths"] = voice_clone_paths
        if audio_transcriptions:
            init_params["audio_transcriptions"] = audio_transcriptions
        if execution_id:
            init_params["execution_id"] = execution_id

        init_params["output_subfolder"] = output_subfolder
        init_params["output_file_name"] = output_file_name

        # Create context
        context = cls(initial_texts=texts, **init_params)

        # Set model-specific parameters directly
        if parameters:
            typed_fields = cls.model_fields.keys()
            for key, value in parameters.items():
                if key not in typed_fields:
                    context.parameters[key] = value

        return context
