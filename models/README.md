# AI Models Microservices API

This document defines the standard API for all AI model microservices. Use this as a reference when implementing new models.

## Standard Endpoints

All model microservices MUST implement these endpoints:

### Core Generation Endpoints

#### POST `/v1/text-to-speech/{voice_id}`
Single-speaker text-to-speech generation.

**Request:**
```json
{
  "text": "Text to generate",
  "output_filepath": "/path/to/output.wav",
  "parameters": {
    "max_new_tokens": 256,
    "seed": 42,
    "temperature": 1.0
  }
}
```

**Response:**
```json
{
  "status": "success",
  "output_filepath": "/path/to/output.wav",
  "message": "Audio generated successfully"
}
```

#### POST `/v1/text-to-dialogue`
Multi-speaker dialogue generation.

**Request:**
```json
{
  "inputs": [
    {
      "text": "First speaker text",
      "voice_id": "/path/to/voice1.wav"
    },
    {
      "text": "Second speaker text", 
      "voice_id": "/path/to/voice2.wav"
    }
  ],
  "output_filepath": "/path/to/output.wav",
  "parameters": {
    "max_new_tokens": 256,
    "seed": 42
  }
}
```

**Response:**
```json
{
  "status": "success",
  "output_filepath": "/path/to/output.wav",
  "message": "Dialogue generated successfully"
}
```

### Model Management Endpoints

#### POST `/v1/load-model`
Preload model into memory.

**Response:**
```json
{
  "status": "success",
  "message": "Model loaded successfully"
}
```

#### POST `/v1/unload-model`
Unload model and free memory/VRAM.

**Response:**
```json
{
  "status": "success",
  "message": "Model unloaded successfully"
}
```

### Health & Info Endpoints

#### GET `/health`
Health check and model status.

**Response:**
```json
{
  "status": "healthy",
  "model_loaded": true,
  "device": "cuda",
  "dependencies_available": true
}
```

#### GET `/`
Service info and model details.

**Response:**
```json
{
  "message": "Model Name Service",
  "model": "model-checkpoint-name"
}
```

## Voice ID Format

- `voice_id` parameters are **file paths** to audio files
- Paths are URL-encoded in requests and decoded by the service
- Services should handle both absolute and relative paths
- Invalid/missing files should fallback gracefully

## Parameters Object

Common parameters supported across models:
- `max_new_tokens`: Maximum tokens to generate (default varies by model)
- `seed`: Random seed for reproducible output
- `temperature`: Sampling temperature (if supported)
- `top_k`: Top-K sampling (if supported)
- `top_p`: Top-P/nucleus sampling (if supported)

## Error Handling

All endpoints should return HTTP error codes with JSON error details:

```json
{
  "detail": "Error description"
}
```

Common error codes:
- `400`: Bad request (invalid parameters, unsupported operation)
- `500`: Internal server error (model/generation failure)

## Model Implementations

### Dia (Port 8003)
**Capabilities:**
- ✅ Multi-speaker dialogue generation (`/v1/text-to-dialogue`)
- ❌ Single-speaker TTS (returns 400 error)

**Requirements:**
- Minimum 2 dialogue inputs
- Python 3.10+, transformers>=4.53.2
- Model: `nari-labs/Dia-1.6B-0626`
- VRAM: ~3-4GB

**Special Features:**
- Voice cloning via audio prompts
- Automatic speaker mapping
- Concatenated audio prompt support

**Parameters:**
- `max_new_tokens`: 256 (default)
- `seed`: Optional

### Chatterbox (Port 8004)
**Capabilities:**
- ✅ Single-speaker TTS (`/v1/text-to-speech/{voice_id}`)
- ✅ Multi-speaker dialogue (concatenated TTS calls)

**Requirements:**
- Python 3.10+, torch==2.6.0, transformers==4.46.3
- Model: `ResembleAI/chatterbox`
- VRAM: ~2-3GB

**Special Features:**
- Advanced voice cloning (up to 60 seconds)
- Expression and emotion control
- Watermark options

**Parameters:**
- `exaggeration`: 0.5 (default)
- `temperature`: 0.75 (default)
- `cfg_weight`: 0.5 (default)
<!-- - `disable_watermark`: false (default) -->
- `seed`: Optional

### Higgs (Port 8005)
**Capabilities:**
- ✅ Single-speaker TTS (`/v1/text-to-speech/{voice_id}`)
- ✅ Multi-speaker dialogue (`/v1/text-to-dialogue`)

**Requirements:**
- Python 3.10+, transformers==4.47.0, torch>=2.0.0
- Model: `bosonai/higgs-audio-v2-generation-3B-base`
- VRAM: ~6-8GB

**Special Features:**
- Advanced multi-modal audio generation
- ChatML-based conversation system
- Chinese punctuation normalization
- Special audio effects tags (laughter, music, etc.)
- Scene description prompts
- RAS (Repetition Avoidance System)

**Parameters:**
- `scene_prompt`: Scene description (default: "Audio is recorded from a quiet room.")
- `transcription`: Voice clone transcription text
- `audio_transcriptions`: List of transcriptions for multi-speaker
- `max_new_tokens`: 1024 (default)
- `temperature`: 0.3 (default)
- `top_p`: 0.95 (default)
- `top_k`: 50 (default)
- `ras_win_len`: 7 (default) - RAS window length
- `ras_win_max_num_repeat`: 2 (default) - RAS max repeats
- `seed`: Optional

### Mock (Port 8999)
**Capabilities:**
- ✅ Single-speaker TTS (copies voice file)
- ✅ Multi-speaker dialogue (concatenates voice files)

**Requirements:**
- Python 3.10+, minimal dependencies
- No GPU required

**Special Features:**
- Zero VRAM usage
- Realistic processing delays
- Perfect for testing and development

**Parameters:**
- All parameters accepted but ignored

---

## Shared Pydantic Models

All microservices MUST use the shared Pydantic models from `models/shared_models.py`:

```python
# Import shared models in your service
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_models import (
    DialogueInput, TextToSpeechRequest, TextToDialogueRequest,
    GenerationResponse, LoadModelResponse, UnloadModelResponse,
    HealthResponse, ServiceInfoResponse
)
```

**Benefits:**
- Consistent API across all services
- Single source of truth for request/response formats
- Easier maintenance and updates
- Type safety and validation

## Implementation Checklist

**New Model Microservice:**
- [ ] Create `models/{model_name}/` directory
- [ ] Add `requirements.txt` with FastAPI + model dependencies
- [ ] Create `{model_name}_service.py` with all standard endpoints
- [ ] **Import shared Pydantic models from `shared_models.py`**
- [ ] Implement proper voice_id filepath handling with URL decoding
- [ ] Add model loading/unloading with VRAM cleanup
- [ ] Use next available port (8005, 8006, etc.)
- [ ] Handle parameters Dict[str, Any] for model-specific config
- [ ] Return JSON responses with output_filepath
- [ ] Add error handling for unsupported operations
- [ ] Test with `python run_model.py {model_name}`

**Update Step File:**
- [ ] Remove all model imports (torch, transformers, etc.)
- [ ] Replace complex generation logic with single call to `generate_candidates_with_service_calls()`
- [ ] Update `MODEL_SERVICE_PORTS` in `generation_utils.py`
- [ ] Step should be ~50 lines total

**Port Assignments:**
- 8003: dia
- 8004: chatterbox
- 8005: higgs
- 8999: mock (testing)
- 8006+: future models

## HTTP-Based Architecture

**Steps are now lightweight HTTP clients:**
- `generate_dia_audio.py`: ~55 lines (was 442 lines)
- `generate_chatterbox_audio.py`: ~51 lines (was 185 lines)
- `generate_higgs_audio.py`: ~55 lines (was 513 lines)
- No model imports, no VRAM management
- Pure HTTP orchestration

**Testing modes use mock service:**
- `TESTING=true` or `TESTING_UI=true` → calls port 8999
- No more file copying or environment-specific logic
- Consistent API testing

## Service Architecture

```
/models/
├── README.md              # This file
├── shared_models.py       # Shared Pydantic models
├── dia/
│   ├── requirements.txt
│   └── dia_service.py     # Port 8003
├── chatterbox/
│   ├── requirements.txt
│   ├── chatterbox_service.py  # Port 8004
│   └── chatterbox_code/   # Moved from backend/
├── higgs/
│   ├── requirements.txt
│   ├── higgs_service.py   # Port 8005
│   └── boson_multimodal/  # Moved from backend/
├── mock/
│   ├── requirements.txt
│   └── mock_service.py    # Port 8999
└── [future models]/
    ├── requirements.txt
    └── model_service.py   # Port 8006+
```

Each model runs as an independent microservice with its own:
- Virtual environment
- Dependencies
- Port
- Process

This allows for:
- Conflicting dependency versions
- Independent scaling
- Separate memory management
- Easy debugging and maintenance