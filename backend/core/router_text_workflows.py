"""
Text Workflows Router

Provides API endpoints for each individual text workflow.
Each workflow gets its own dedicated endpoint with proper typing and websocket support.
"""

import uuid
import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional

# Import individual workflow functions (sync versions)
from backend.text_workflows.csv_to_psss import process as csv_to_psss_process
from backend.text_workflows.text_to_psss import process as text_to_psss_process
from backend.text_workflows.text_to_llm_api import (
    process_sync as text_to_llm_api_process,
)

# Import logging utilities
from backend.core.utils.logger import (
    get_logger,
    log_api_request,
    log_error_with_context,
)
from backend.text_workflows.websocket_utils import (
    send_text_workflow_complete,
    send_text_workflow_error,
)

logger = get_logger(__name__)


# Request models for individual workflows
class CsvToPsssRequest(BaseModel):
    """Request model for CSV to PSSS workflow"""

    filepath: str


class TextToPsssRequest(BaseModel):
    """Request model for Text to PSSS workflow"""

    text: str


class TextToLlmApiRequest(BaseModel):
    """Request model for Text to LLM API workflow"""

    filepath: Optional[str] = None
    text: Optional[str] = None
    api_key: str


class TextToScriptViaOllamaRequest(BaseModel):
    filepath: Optional[str] = None
    text: Optional[str] = None
    ollama_url: Optional[str] = None
    model_name: Optional[str] = None


# Background execution request model
class TextWorkflowExecutionRequest(BaseModel):
    """Request model for background text workflow execution"""

    workflow_name: str
    parameters: dict


# Response models
class ExecutionResponse(BaseModel):
    """Response model for workflow execution confirmation"""

    execution_id: str
    message: str


router = APIRouter(prefix="/api/text-workflows", tags=["text-workflows"])


@router.post("/csv-to-psss", response_model=ExecutionResponse)
async def csv_to_psss(request: CsvToPsssRequest):
    """
    Convert CSV file with Text,Speaker columns into a Script object.
    Results delivered via WebSocket.
    """
    execution_id = str(uuid.uuid4())
    log_api_request(
        "/api/text-workflows/csv-to-psss",
        "POST",
        {"filepath": request.filepath, "execution_id": execution_id},
    )

    # Start background execution
    asyncio.create_task(
        _execute_text_workflow_background(
            "csv_to_psss",
            {"filepath": request.filepath},
            execution_id,
        )
    )

    return ExecutionResponse(
        execution_id=execution_id,
        message="CSV to PSSS workflow started. Results will be delivered via WebSocket.",
    )


@router.post("/text-to-psss", response_model=ExecutionResponse)
async def text_to_psss(request: TextToPsssRequest):
    """
    Convert text in 'Speaker: Text' format into a Script object.
    Results delivered via WebSocket.
    """
    execution_id = str(uuid.uuid4())
    log_api_request(
        "/api/text-workflows/text-to-psss", "POST", {"execution_id": execution_id}
    )

    # Start background execution
    asyncio.create_task(
        _execute_text_workflow_background(
            "text_to_psss",
            {"text": request.text},
            execution_id,
        )
    )

    return ExecutionResponse(
        execution_id=execution_id,
        message="Text to PSSS workflow started. Results will be delivered via WebSocket.",
    )


@router.post("/text-to-llm-api", response_model=ExecutionResponse)
async def text_to_llm_api(request: TextToLlmApiRequest):
    """
    Process text file using Gemini LLM API to create Script objects.
    Results delivered via WebSocket.
    """
    execution_id = str(uuid.uuid4())
    log_api_request(
        "/api/text-workflows/text-to-llm-api",
        "POST",
        {
            "filepath": request.filepath,
            "text": request.text,
            "execution_id": execution_id,
        },
    )

    # Start background execution
    asyncio.create_task(
        _execute_text_workflow_background(
            "text_to_llm_api",
            {
                "filepath": request.filepath,
                "text": request.text,
                "api_key": request.api_key,
            },
            execution_id,
        )
    )

    return ExecutionResponse(
        execution_id=execution_id,
        message="Text to LLM API workflow started. Results will be delivered via WebSocket.",
    )


@router.post("/text-to-script-via-ollama", response_model=ExecutionResponse)
async def text_to_script_via_ollama(request: TextToScriptViaOllamaRequest):
    """
    Process text using local Ollama LLM to create a Script object.
    Results delivered via WebSocket.
    """
    execution_id = str(uuid.uuid4())
    log_api_request(
        "/api/text-workflows/text-to-script-via-ollama",
        "POST",
        {
            "text": request.text,
            "filepath": request.filepath,
            "ollama_url": request.ollama_url,
            "model_name": request.model_name,
            "execution_id": execution_id,
        },
    )

    # Start background execution
    asyncio.create_task(
        _execute_text_workflow_background(
            "text_to_script_via_ollama",
            {
                "text": request.text,
                "filepath": request.filepath,
                "ollama_url": request.ollama_url,
                "model_name": request.model_name,
            },
            execution_id,
        )
    )

    return ExecutionResponse(
        execution_id=execution_id,
        message="Text to Script via Ollama workflow started. Results will be delivered via WebSocket.",
    )


async def _execute_text_workflow_background(
    workflow_name: str, parameters: dict, execution_id: str
):
    """Execute text workflow in background and send results via WebSocket"""

    try:
        # Route to appropriate workflow
        if workflow_name == "csv_to_psss":
            filepath = parameters.get("filepath")
            if not filepath:
                raise ValueError("filepath parameter required for csv_to_psss workflow")

            script = await csv_to_psss_process(filepath, execution_id)
            result = {"script": script.model_dump()}

        elif workflow_name == "text_to_psss":
            text = parameters.get("text")
            if not text:
                raise ValueError("text parameter required for text_to_psss workflow")

            script = await text_to_psss_process(text, execution_id)
            result = {"script": script.model_dump()}

        elif workflow_name == "text_to_llm_api":
            filepath = parameters.get("filepath")
            text = parameters.get("text")
            api_key = parameters.get("api_key")

            if not filepath and not text:
                raise ValueError(
                    "Either filepath or text parameter required for text_to_llm_api workflow"
                )
            if not api_key:
                raise ValueError(
                    "api_key parameter required for text_to_llm_api workflow"
                )

            script = text_to_llm_api_process(
                filepath=filepath, text=text, api_key=api_key, execution_id=execution_id
            )
            result = {"script": script.model_dump()}

        elif workflow_name == "text_to_script_via_ollama":
            filepath = parameters.get("filepath")
            text = parameters.get("text")
            ollama_url = parameters.get("ollama_url")
            model_name = parameters.get("model_name")

            if not filepath and not text:
                raise ValueError(
                    "Either filepath or text parameter required for text_to_script_via_ollama workflow"
                )

            # Import the async version directly
            from backend.text_workflows.text_to_script_via_ollama_robust import (
                process as text_to_script_via_ollama_process_async,
            )

            script = await text_to_script_via_ollama_process_async(
                text=text,
                filepath=filepath,
                ollama_url=ollama_url,
                model_name=model_name,
                execution_id=execution_id,
            )
            result = {"script": script.model_dump()}

        else:
            raise ValueError(f"Unknown workflow: {workflow_name}")

        # Send completion via WebSocket
        await send_text_workflow_complete(result, workflow_name, execution_id)

        logger.info(
            f"Text workflow {workflow_name} completed successfully (execution_id: {execution_id})"
        )

        return result

    except Exception as e:
        # Send error via WebSocket
        await send_text_workflow_error(str(e), workflow_name, execution_id)

        log_error_with_context(
            e, f"executing text workflow {workflow_name} (execution_id: {execution_id})"
        )
        logger.error(
            f"Text workflow {workflow_name} failed (execution_id: {execution_id}): {str(e)}"
        )
