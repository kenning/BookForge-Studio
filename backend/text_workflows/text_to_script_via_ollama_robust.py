"""
Wrapper module for the robust Ollama text-to-script workflow.

This provides a simple interface that can be called from the API router.
"""

from typing import Optional
import asyncio
from backend.core.data_types.script_and_text_types import Script
from backend.text_workflows.text_to_script_robust.workflow import (
    RobustTextToScriptWorkflow,
)
from backend.text_workflows.websocket_utils import (
    send_text_workflow_progress,
    send_text_workflow_error,
)


async def process(
    text: Optional[str] = None,
    filepath: Optional[str] = None,
    ollama_url: Optional[str] = None,
    model_name: Optional[str] = None,
    execution_id: Optional[str] = None,
) -> Script:
    """
    Process text using the robust Ollama workflow.

    Args:
        text: Direct text input
        filepath: Path to text file (mutually exclusive with text)
        ollama_url: Ollama server URL
        model_name: Model name to use
        execution_id: Optional execution ID for websocket tracking

    Returns:
        Script object
    """
    workflow_name = "text_to_script_via_ollama"

    try:
        # Send initial progress
        await send_text_workflow_progress(
            0, 1, "Starting Ollama workflow", workflow_name, execution_id
        )

        # Read file if filepath provided
        if filepath and not text:
            from backend.core.utils.file_utils import (
                read_text_file,
                resolve_file_path,
                validate_file_path,
            )

            target_dir, clean_filename = resolve_file_path(
                filepath, default_directory_type="input"
            )
            file_path = target_dir / clean_filename
            resolved_file_path = validate_file_path(file_path, target_dir)
            text = read_text_file(resolved_file_path)

        if not text:
            raise ValueError("Either text or filepath must be provided")

        # Create and run workflow
        workflow = RobustTextToScriptWorkflow(
            ollama_url=ollama_url,
            model_name=model_name,
            execution_id=execution_id,
        )

        script = await workflow.process(text)

        return script

    except Exception as e:
        # Send error
        await send_text_workflow_error(str(e), workflow_name, execution_id)
        raise


def process_sync(*args, **kwargs) -> Script:
    """Synchronous wrapper for the async process function."""

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're already in an async context
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(lambda: asyncio.run(process(*args, **kwargs)))
                return future.result()
        else:
            # We're not in an async context
            return asyncio.run(process(*args, **kwargs))
    except Exception as e:
        # Run the error reporting in a new loop if needed
        try:
            asyncio.run(
                send_text_workflow_error(
                    str(e), "text_to_script_via_ollama", kwargs.get("execution_id")
                )
            )
        except:
            pass  # Don't let websocket errors break the main error
        raise
