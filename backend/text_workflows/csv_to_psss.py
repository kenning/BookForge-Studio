"""
Text Workflow: CSV to BookForge Studio Script

This workflow converts a CSV file with Text,Speaker columns into a Script object.
"""

import csv
import asyncio
from io import StringIO
from pathlib import Path
from typing import Dict, Any, Optional

from backend.core.data_types.script_and_text_types import (
    Script,
    ScriptHistoryGrid,
    ScriptHistoryGridRow,
    ScriptHistoryGridCell,
)
from backend.core.utils.file_utils import resolve_file_path, validate_file_path
from backend.text_workflows.websocket_utils import (
    send_text_workflow_progress,
    send_text_workflow_complete,
    send_text_workflow_error,
)


def csv_content_to_script(
    csv_content: str,
) -> Script:
    rows = []
    speakers = set()

    # Use standard CSV dialect instead of auto-detection to avoid issues with complex content
    print("parsing...")
    print(csv_content[:100])

    # Parse CSV string content
    reader = csv.DictReader(StringIO(csv_content))

    # Ensure required columns exist
    if "Text" not in reader.fieldnames or "Speaker" not in reader.fieldnames:
        raise ValueError(
            "CSV must contain 'Text' and 'Speaker' columns, but got:",
            reader.fieldnames,
        )

    for row in reader:
        text = row["Text"].strip()
        speaker = row["Speaker"].strip()

        if text:  # Skip empty text rows
            # Create a script history grid cell
            cell = ScriptHistoryGridCell(
                texts=[text], speakers=[speaker], generated_filepath=""
            )

            # Create a script history grid row
            grid_row = ScriptHistoryGridRow(current_index=0, cells=[cell])

            rows.append(grid_row)
            speakers.add(speaker)

    # Create the script history grid
    history_grid = ScriptHistoryGrid(grid=rows, between_lines_elements=[])

    # Create speaker to actor mapping (all speakers map to empty string initially)
    speaker_to_actor_map = {speaker: "" for speaker in speakers}
    speaker_to_voice_mode_map = {speaker: "" for speaker in speakers}

    # Create and return the Script object
    script = Script(
        type="script",
        history_grid=history_grid,
        speaker_to_actor_map=speaker_to_actor_map,
        speaker_to_voice_mode_map=speaker_to_voice_mode_map,
    )
    return script


async def process(filepath: str, execution_id: Optional[str] = None) -> Script:
    """
    Process a CSV file and convert it to a Script object.

    Args:
        filepath: Path to the CSV file (can include directory type prefix)
        execution_id: Optional execution ID for websocket tracking

    Returns:
        Script object with the converted data
    """
    workflow_name = "csv_to_psss"

    try:
        # Send initial progress
        await send_text_workflow_progress(
            0, 2, "Starting CSV processing", workflow_name, execution_id
        )

        # Resolve file path using the same logic as filesystem router
        target_dir, clean_filename = resolve_file_path(
            filepath, default_directory_type="input"
        )

        # Construct the full file path
        file_path = target_dir / clean_filename

        # Validate file path and existence
        resolved_file_path = validate_file_path(file_path, target_dir)

        await send_text_workflow_progress(
            1, 2, f"Reading CSV file: {clean_filename}", workflow_name, execution_id
        )

        with open(resolved_file_path, "r", encoding="utf-8") as csvfile:
            csv_content = csvfile.read()
            script = csv_content_to_script(csv_content)

        await send_text_workflow_progress(
            2, 2, "CSV processing complete", workflow_name, execution_id
        )

        return script

    except Exception as e:
        # Send error
        await send_text_workflow_error(str(e), workflow_name, execution_id)
        raise
