"""
Models Router

Provides API endpoints for discovering available models and their default workflow configurations.
"""

import importlib
from pathlib import Path
from typing import Dict, List, Any, Optional
import asyncio
import aiohttp

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Import logging utilities
from backend.core.utils.logger import (
    get_logger,
    log_api_request,
    log_error_with_context,
)
from backend.core.utils.model_ports_config import MODEL_SERVICE_PORTS

logger = get_logger(__name__)


class ModelWorkflow(BaseModel):
    name: str
    steps: List[str]


class ModelMetadata(BaseModel):
    model_name: str
    voice_clone_tips: List[str]
    workflows: List[ModelWorkflow]


class ModelsResponse(BaseModel):
    """Response model for available models and their workflows"""

    models: List[ModelMetadata]


class ServiceStatus(BaseModel):
    """Status information for a single microservice"""

    service_name: str
    port: int
    is_running: bool
    health_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class ServicesStatusResponse(BaseModel):
    """Response model for microservices status"""

    services: List[ServiceStatus]


router = APIRouter(prefix="/api/models", tags=["models"])

# Global storage for loaded model workflows
loaded_model_metadatas: Dict[str, ModelMetadata] = {}


def tryToList(data: Any, key: str) -> List[Any]:
    maybelist = data.get(key)
    if not isinstance(maybelist, list):
        raise Exception(f"Model {data} metadata {key} is not a list")
    return maybelist


def tryToGetDict(data: Any, key: str) -> Dict[str, Any]:
    maybedict = data.get(key)
    if not isinstance(maybedict, dict):
        raise Exception(f"Model {data} metadata {key} is not a dictionary")
    return maybedict


def discover_model_workflows():
    """
    Dynamically discover model workflows from backend/models/*/setup.py files.
    This function scans the backend/models directory,
    importing all setup.py files and extracting their provide_default_workflows functions.
    """
    global loaded_model_metadatas
    loaded_model_metadatas = {}

    # Get the path to the backend directory
    current_file = Path(__file__)
    backend_dir = current_file.parent.parent

    # Add models directory
    models_dir = backend_dir / "models"
    if not models_dir.exists():
        logger.warning(f"Models directory not found: {models_dir}")
        return

    logger.info(f"Loading model workflows from: {models_dir}")

    # Iterate through all model directories
    for model_dir in models_dir.iterdir():
        if not model_dir.is_dir():
            continue

        setup_file = model_dir / "setup.py"
        if not setup_file.exists():
            logger.info(f"No setup.py found for model: {model_dir.name}")
            continue

        try:
            # Import the setup module dynamically
            module_name = f"backend.models.{model_dir.name}.setup"
            logger.info(f"Importing model setup module: {module_name}")

            setup_module = importlib.import_module(module_name)

            if not hasattr(setup_module, "provide_model_metadata"):
                raise Exception(
                    f"Model {model_dir.name} setup.py missing 'provide_model_metadata'"
                )
            model_metadata_func = getattr(setup_module, "provide_model_metadata")
            if not callable(model_metadata_func):
                raise Exception(
                    f"Model {model_dir.name} provide_model_metadata is not callable"
                )

            model_metadata = model_metadata_func()
            if not isinstance(model_metadata, dict):
                raise Exception(
                    f"Model {model_dir.name} provide_model_metadata returned non-dict"
                )

            voice_clone_tips = tryToList(model_metadata, "voice_clone_tips")

            all_workflows = tryToList(model_metadata, "default_workflows")
            workflows = []
            for workflow in all_workflows:
                if "name" not in workflow or "steps" not in workflow:
                    raise Exception(
                        f"Model {model_dir.name} metadata missing required fields"
                    )

                workflow_name = workflow.get("name", "")
                if workflow_name == "":
                    raise Exception(
                        f"Model {model_dir.name} metadata missing required field 'name'"
                    )

                workflow_steps = tryToList(workflow, "steps")
                workflows.append(
                    ModelWorkflow(name=workflow_name, steps=workflow_steps)
                )

            model_name = model_metadata["name"]
            # Create ModelMetadata object
            model_metadata = ModelMetadata(
                model_name=model_metadata["name"],
                workflows=[w.model_dump() for w in workflows],
                voice_clone_tips=voice_clone_tips,
            )

            # Check for name conflicts and warn
            if model_name in loaded_model_metadatas:
                raise Exception(f"Model workflow '{model_name}' already exists.")

            loaded_model_metadatas[model_name] = model_metadata
            logger.info(f"Loaded model metadata: {model_name}")

        except Exception as e:
            log_error_with_context(e, f"loading model workflow {model_dir.name}")
            continue


# Load model workflows when the module is imported
discover_model_workflows()


async def check_service_health(service_name: str, port: int) -> ServiceStatus:
    """Check the health of a single microservice via /v1/models endpoint"""
    url = f"http://localhost:{port}/v1/models"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    models_data = await response.json()
                    return ServiceStatus(
                        service_name=service_name,
                        port=port,
                        is_running=True,
                        health_data=models_data,
                    )
                else:
                    return ServiceStatus(
                        service_name=service_name,
                        port=port,
                        is_running=False,
                        error_message=f"HTTP {response.status}",
                    )
    except Exception as e:
        return ServiceStatus(
            service_name=service_name, port=port, is_running=False, error_message=str(e)
        )


@router.get("/", response_model=ModelsResponse)
async def get_models():
    """
    Get a list of all available models and their default workflow configurations.

    Returns:
        ModelsResponse containing list of model workflows
    """
    log_api_request("/api/models/", "GET")

    models_list = list(loaded_model_metadatas.values())

    logger.info(f"Returning {len(models_list)} available model workflows")
    return ModelsResponse(models=models_list)


@router.get("/status", response_model=ServicesStatusResponse)
async def get_services_status():
    """
    Get the health status of all microservices.

    Returns:
        ServicesStatusResponse containing health information for each service
    """
    log_api_request("/api/models/status", "GET")

    # Create health check tasks for all services
    health_check_tasks = [
        check_service_health(service_name, port)
        for service_name, port in MODEL_SERVICE_PORTS.items()
    ]

    # Execute all health checks concurrently
    service_statuses = await asyncio.gather(*health_check_tasks)

    return ServicesStatusResponse(services=service_statuses)
