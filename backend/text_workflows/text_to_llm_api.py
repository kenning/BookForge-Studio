"""
Text Workflow: Text File to LLM API

This workflow reads a text file and sends it to an OpenAI-compatible API with a custom prompt.
"""

import json
import os
import asyncio
import requests
from pathlib import Path
from typing import Dict, Any, Optional

if __name__ == "__main__":
    from dotenv import load_dotenv
    import sys

    load_dotenv()

    sys.path.append(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )


from backend.core.utils.file_utils import resolve_file_path, validate_file_path
from backend.core.data_types.script_and_text_types import Script
from backend.text_workflows.csv_to_psss import csv_content_to_script
from backend.text_workflows.websocket_utils import (
    send_text_workflow_progress,
    send_text_workflow_complete,
    send_text_workflow_error,
)

API_URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
API_KEY = os.getenv("GEMINI_API_KEY")


async def process(
    filepath: str = None,
    text: str = None,
    api_key: str = None,
    execution_id: Optional[str] = None,
) -> Script:
    workflow_name = "text_to_llm_api"

    try:
        # Send initial progress
        await send_text_workflow_progress(
            0, 4, "Starting LLM API workflow", workflow_name, execution_id
        )

        final_api_key = api_key or API_KEY
        if final_api_key is None:
            raise ValueError("API key is required")

        # Check if we have either a file or text input
        if not filepath and not text:
            raise ValueError("Either filepath or text must be provided")

        await send_text_workflow_progress(
            1, 4, "Reading input text", workflow_name, execution_id
        )

        # Get file content from either file or direct text input
        if filepath:
            target_dir, clean_filename = resolve_file_path(
                filepath, default_directory_type="input"
            )

            # Construct the full file path
            file_path = target_dir / clean_filename

            # Validate file path and existence
            resolved_file_path = validate_file_path(file_path, target_dir)

            # Read the text file
            with open(resolved_file_path, "r", encoding="utf-8") as file:
                file_content = file.read().strip()
        else:
            file_content = text.strip()

        # Load the shared prompt template
        prompt_template_path = Path(__file__).parent / "llm_prompt_template.txt"
        with open(prompt_template_path, "r", encoding="utf-8") as f:
            prompt_template = f.read()

        # Format the prompt with file content
        full_prompt = prompt_template.format(file_content=file_content)

        await send_text_workflow_progress(
            2, 4, "Sending request to LLM API", workflow_name, execution_id
        )

        # Prepare the request payload
        payload = {
            "model": "gemini-2.5-pro",
            "reasoning_effort": "high",
            "messages": [{"role": "user", "content": full_prompt}],
        }

        # Headers
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {final_api_key}",
        }

        # Make the API request
        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()

        # Parse the response
        response_data = response.json()

        await send_text_workflow_progress(
            3, 4, "Processing LLM response", workflow_name, execution_id
        )

        # Extract the content from the response
        if "choices" in response_data and len(response_data["choices"]) > 0:
            csv_content = response_data["choices"][0]["message"]["content"]

            # Convert CSV content to Script object
            script = csv_content_to_script(csv_content)

            await send_text_workflow_progress(
                4, 4, "LLM API workflow complete", workflow_name, execution_id
            )

            return script
        else:
            raise ValueError("Error: No response content found")

    except Exception as e:
        # Send error
        await send_text_workflow_error(str(e), workflow_name, execution_id)
        raise


def process_sync(
    filepath: str = None,
    text: str = None,
    api_key: str = None,
    execution_id: Optional[str] = None,
) -> Script:
    """Synchronous wrapper for the async process function."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're already in an async context
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    lambda: asyncio.run(process(filepath, text, api_key, execution_id))
                )
                return future.result()
        else:
            # We're not in an async context
            return asyncio.run(process(filepath, text, api_key, execution_id))
    except Exception as e:
        # Run the error reporting in a new loop if needed
        try:
            asyncio.run(
                send_text_workflow_error(str(e), "text_to_llm_api", execution_id)
            )
        except:
            pass  # Don't let websocket errors break the main error
        raise


# WORKFLOW_METADATA = {
#     "name": "text_to_llm_api",
#     "display_name": "Text File to LLM API",
#     "description": "Attempts to transcribe text with an OpenAI-compatible API. Just uses Gemini for now.",
#     "input_type": "text_filepath",
#     "output_type": "script",
#     "category": "text-workflows",
#     "version": "1.0.0",
#     "parameters": {
#         "filepath": {
#             "type": "string",
#             "description": "Path to the text file (can include directory type prefix like 'input/documents/file.txt')",
#             "required": True,
#         },
#         "api_key": {
#             "type": "string",
#             "description": "API key for the OpenAI-compatible service",
#             "required": True,
#         },
#         "csv_name": {
#             "type": "string",
#             "description": "Name for the output CSV file (without .csv extension)",
#             "required": True,
#         },
#     },
# }

if __name__ == "__main__":
    result = process(filepath="wuthering-heights-chapter-1.txt")
    print(result)
