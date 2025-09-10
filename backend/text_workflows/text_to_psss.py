"""
Text Workflow: Text to BookForge Studio Script

This workflow converts text in "Speaker: Text" format into a Script object.
"""

import re
import asyncio
from typing import Dict, Any, Optional

from backend.core.data_types.script_and_text_types import (
    Script,
    ScriptHistoryGrid,
    ScriptHistoryGridRow,
    ScriptHistoryGridCell,
)
from backend.text_workflows.websocket_utils import (
    send_text_workflow_progress,
    send_text_workflow_complete,
    send_text_workflow_error,
)


async def process(text: str, execution_id: Optional[str] = None) -> Script:
    """
    Process text in "Speaker: Text" format and convert it to a Script object.

    Args:
        text: Input text with lines in "Speaker: Text" format
        execution_id: Optional execution ID for websocket tracking

    Returns:
        Script object with the converted data
    """
    workflow_name = "text_to_psss"

    try:
        # Send initial progress
        await send_text_workflow_progress(
            0, 2, "Starting text parsing", workflow_name, execution_id
        )

        # Split text into lines and process each line
        lines = text.strip().split("\n")
        rows = []
        speakers = set()

        await send_text_workflow_progress(
            1, 2, f"Processing {len(lines)} lines", workflow_name, execution_id
        )

        for line in lines:
            line = line.strip()
            if not line:
                continue  # Skip empty lines

            # Try to split on the first colon to separate speaker and text
            if ":" in line:
                parts = line.split(":", 1)
                if len(parts) == 2:
                    speaker = parts[0].strip()
                    text_content = parts[1].strip()

                    if text_content:  # Only process if there's actual text content
                        # Create a script history grid cell
                        cell = ScriptHistoryGridCell(
                            texts=[text_content],
                            speakers=[speaker],
                            generated_filepath="",
                        )

                        # Create a script history grid row
                        grid_row = ScriptHistoryGridRow(current_index=0, cells=[cell])

                        rows.append(grid_row)
                        speakers.add(speaker)
                    continue

            # If no colon found or parsing failed, treat as narrative/no speaker
            # Use "Narrator" as default speaker for lines without clear speaker attribution
            cell = ScriptHistoryGridCell(
                texts=[line], speakers=["Narrator"], generated_filepath=""
            )

            grid_row = ScriptHistoryGridRow(current_index=0, cells=[cell])

            rows.append(grid_row)
            speakers.add("Narrator")

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

        await send_text_workflow_progress(
            2,
            2,
            f"Text parsing complete. Found {len(speakers)} speakers",
            workflow_name,
            execution_id,
        )

        return script

    except Exception as e:
        # Send error
        await send_text_workflow_error(str(e), workflow_name, execution_id)
        raise
