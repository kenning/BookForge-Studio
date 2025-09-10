"""
Shared Pydantic models for all AI model microservices.

This module defines the standard request/response models that all
microservices should use to maintain API consistency.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel


# Request Models
class DialogueInput(BaseModel):
    """Single dialogue input with text and voice reference."""

    text: str
    voice_id: str  # File path to voice audio file


class TextToSpeechRequest(BaseModel):
    """Request for single-speaker text-to-speech generation."""

    text: str
    output_filepath: str
    parameters: Optional[Dict[str, Any]] = {}
    audio_transcriptions: List[str]


class TextToDialogueRequest(BaseModel):
    """Request for multi-speaker dialogue generation."""

    inputs: List[DialogueInput]
    output_filepath: str
    parameters: Optional[Dict[str, Any]] = {}
    voice_clone_paths: List[str]
    audio_transcriptions: List[str]


# Response Models
class GenerationResponse(BaseModel):
    """Standard response for audio generation endpoints."""

    status: str
    output_filepath: str
    message: Optional[str] = None


class LoadModelResponse(BaseModel):
    """Response for model loading endpoint."""

    status: str
    message: str


class UnloadModelResponse(BaseModel):
    """Response for model unloading endpoint."""

    status: str
    message: str


class HealthResponse(BaseModel):
    """Response for health check endpoint."""

    status: str
    model_loaded: bool
    device: str
    dependencies_available: bool
    model_name: str


class ServiceInfoResponse(BaseModel):
    """Response for service info endpoint."""

    message: str
    model: str


# OpenAI-compatible response models
class OpenAIModel(BaseModel):
    """OpenAI-compatible model object with optional health data."""

    id: str
    object: str = "model"
    created: int
    owned_by: str
    # Optional health information for custom services
    status: Optional[str] = None
    model_loaded: Optional[bool] = None
    device: Optional[str] = None
    dependencies_available: Optional[bool] = None


class OpenAIModelsResponse(BaseModel):
    """OpenAI-compatible models list response."""

    object: str = "list"
    data: List[OpenAIModel]


# Common parameter validation
class CommonParameters(BaseModel):
    """Common parameters supported across models."""

    max_new_tokens: Optional[int] = 256
    seed: Optional[int] = None
    temperature: Optional[float] = None
    top_k: Optional[int] = None
    top_p: Optional[float] = None
