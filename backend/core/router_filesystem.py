import os
import json
from pathlib import Path
from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

# Import thread pool utility
from backend.core.utils.file_utils import concatenate_audio_files
from backend.core.utils.threading import run_in_thread_pool

# Import shared configuration
from backend.core.config import DIRECTORY_MAPPINGS, ACTORS_DIR, OUTPUT_DIR

# Import logging utilities
from backend.core.utils.logger import (
    get_logger,
    log_api_request,
    log_file_operation,
    log_error_with_context,
)

logger = get_logger(__name__)

# Import shared utilities
from backend.core.utils.file_utils import (
    resolve_file_path,
    validate_file_path,
    read_text_file,
    read_json_file,
    write_json_file,
    save_generic_json_file,
    get_directory_path,
    write_dropped_file,
)

# Import shared data types
from backend.core.data_types.filesystem_types import FileInfo, DirectoryInfo
from backend.core.data_types.script_and_text_types import (
    ActorData,
    Script,
    VoiceModeData,
)


class FileListResponse(BaseModel):
    directory_structure: DirectoryInfo
    flat_files: List[FileInfo]
    total_files: int


class TextContentResponse(BaseModel):
    filename: str
    content: str
    size: int


# Create router for filesystem endpoints
router = APIRouter(prefix="/api/files", tags=["filesystem"])


# Generic save request model
class GenericSaveRequest(BaseModel):
    directory_type: str
    filename: str
    content: dict


class GenericSaveResponse(BaseModel):
    filename: str
    directory_type: str
    message: str
    saved_path: str


class SaveScriptRequest(BaseModel):
    directory_type: str
    filename: str
    script: Script


class ScriptResponse(BaseModel):
    filename: str
    script: Script


class ExportTimelineRequest(BaseModel):
    script: Script
    output_subfolder: str


class ExportTimelineResponse(BaseModel):
    message: str
    output_file_path: str


class UploadFileResponse(BaseModel):
    filename: str
    original_filename: str
    file_path: str
    file_info: FileInfo


def _scan_directory_items(directory: Path):
    """Helper function to scan directory items in thread pool"""
    return list(directory.iterdir())


def _save_audio_file(audio_data, output_path: str):
    """Helper function to save audio data to file"""
    try:
        import soundfile as sf

        sf.write(output_path, audio_data, 44100)
        logger.info(f"Saved audio file: {output_path}")
    except ImportError:
        logger.error("soundfile library not available")
        raise
    except Exception as e:
        logger.error(f"Error saving audio file: {e}")
        raise


def _get_file_info(item: Path, base_path: Path, directory_type: str):
    """Helper function to get file info in thread pool"""
    try:
        item_relative_path = item.relative_to(base_path)
        extension = item.suffix.lower()
        maybe_actor_data = None
        maybe_voice_mode_data = None

        # Determine file type classification
        if extension in [".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"]:
            file_type = "audio"
        elif extension in [".txt", ".md", ".csv"]:
            file_type = "text"
        elif extension == ".json":
            # Try to determine file type by checking the "type" field in JSON
            try:
                with open(item, "r", encoding="utf-8") as f:
                    content = json.load(f)
                # Check if it has a "type" field to determine file type
                if isinstance(content, dict) and "file_type" in content:
                    json_type = content["file_type"]
                    if json_type == "actor":
                        file_type = "actor"
                        try:
                            actor_data_obj = ActorData.model_validate(
                                content["actor_data"]
                            )
                            maybe_actor_data = actor_data_obj.model_dump()
                        except Exception as e:
                            logger.error(f"Failed to parse actor data: {e}")
                            logger.error(f"Content was: {content}")
                            # Set a default ActorData if parsing fails
                            actor_data_obj = ActorData()
                            maybe_actor_data = actor_data_obj.model_dump()
                    elif json_type == "script":
                        file_type = "script"
                    elif json_type == "voice_mode":
                        file_type = "voice_mode"
                        try:
                            voice_mode_data_obj = VoiceModeData.model_validate(
                                content["voice_mode_data"]
                            )
                            maybe_voice_mode_data = voice_mode_data_obj.model_dump()
                        except Exception as e:
                            logger.error(f"Failed to parse voice mode data: {e}")
                            logger.error(f"Content was: {content}")
                            # Set a default VoiceModeData if parsing fails
                            voice_mode_data_obj = VoiceModeData()
                            maybe_voice_mode_data = voice_mode_data_obj.model_dump()
                    else:
                        file_type = "text"  # Default for other JSON types
                else:
                    file_type = "text"  # Default JSON files to text if no type field
            except (json.JSONDecodeError, Exception):
                file_type = "text"  # If we can't parse, treat as text
        else:
            file_type = "other"

        file_info = FileInfo(
            name=item.name,
            type="file",
            path=f"{directory_type}/{str(item_relative_path)}",
            size=item.stat().st_size,
            extension=extension,
            file_type=file_type,
            actor_data=maybe_actor_data,
            voice_mode_data=maybe_voice_mode_data,
        )
        return file_info
    except Exception as e:
        logger.error(f"Error getting file info: {e}")
        # Return None for failed files so they can be skipped
        return None


async def scan_directory_recursive(
    directory: Path, base_path: Path, directory_type: str = ""
) -> DirectoryInfo:
    """
    Recursively scan a directory and return a structured representation.

    Args:
        directory: The directory to scan
        base_path: The base directory path for calculating relative paths
        directory_type: The type of directory to prefix paths with

    Returns:
        DirectoryInfo containing the directory structure with files and subdirectories
    """
    relative_path = directory.relative_to(base_path)
    files: List[FileInfo] = []
    directories: List[DirectoryInfo] = []

    try:
        # Get all items in the directory using thread pool
        items = await run_in_thread_pool(_scan_directory_items, directory)

        # Sort for consistent ordering
        items = sorted(items, key=lambda x: (x.is_file(), x.name.lower()))

        for item in items:
            # Skip hidden files and directories
            if item.name.startswith("."):
                continue

            if item.is_file():
                # Get file info using thread pool
                file_info = await run_in_thread_pool(
                    _get_file_info, item, base_path, directory_type
                )
                if file_info:  # Only add if we successfully got file info
                    files.append(file_info)

            elif item.is_dir():
                # Recursively scan subdirectory
                subdir_info = await scan_directory_recursive(
                    item, base_path, directory_type
                )
                directories.append(subdir_info)

    except PermissionError:
        # Handle permission errors gracefully
        return DirectoryInfo(
            name=directory.name,
            type="directory",
            path=(
                f"{directory_type}/{str(relative_path)}"
                if str(relative_path) != "."
                else directory_type
            ),
            files=files,
            directories=directories,
            error="Permission denied",
        )
    except Exception as e:
        logger.error(f"Error scanning directory {directory}: {e}")
        return DirectoryInfo(
            name=directory.name,
            type="directory",
            path=(
                f"{directory_type}/{str(relative_path)}"
                if str(relative_path) != "."
                else directory_type
            ),
            files=files,
            directories=directories,
            error=str(e),
        )

    return DirectoryInfo(
        name=directory.name,
        type="directory",
        path=(
            f"{directory_type}/{str(relative_path)}"
            if str(relative_path) != "."
            else directory_type
        ),
        files=files,
        directories=directories,
    )


@router.get("/list", response_model=FileListResponse)
async def list_files(directory_type: str = "actors"):
    """Lists files in the specified directory type with recursive directory structure."""
    log_api_request(f"/api/files/list", "GET", {"directory_type": directory_type})

    try:
        target_dir = get_directory_path(directory_type)
    except HTTPException:
        raise

    try:
        # Scan the directory recursively
        directory_structure: DirectoryInfo = await scan_directory_recursive(
            target_dir, target_dir, directory_type
        )

        # Also provide a flat list of files for backward compatibility
        flat_files: List[FileInfo] = []

        def collect_files_recursive(dir_info: DirectoryInfo):
            """Helper function to collect all files in a flat list"""
            for file_info in dir_info.files:
                flat_files.append(file_info)

            for subdir in dir_info.directories:
                collect_files_recursive(subdir)

        collect_files_recursive(directory_structure)

        logger.info(
            f"Successfully listed {len(flat_files)} files in {directory_type} directory"
        )

        return FileListResponse(
            directory_structure=directory_structure.model_dump(),
            flat_files=[file.model_dump() for file in flat_files],
            total_files=len(flat_files),
        )

    except Exception as e:
        log_error_with_context(e, f"listing files in {directory_type} directory")
        raise HTTPException(status_code=500, detail=f"Failed to list files: {e}")


@router.get("/serve/{filename:path}")
async def serve_file(filename: str):
    log_api_request(f"/api/files/serve/{filename}", "GET")

    # Resolve file path and perform security checks
    target_dir, clean_filename = resolve_file_path(
        filename, default_directory_type="output"
    )

    # Construct the full file path
    file_path = target_dir / clean_filename

    # Validate file path and existence
    resolved_file_path = validate_file_path(file_path, target_dir)

    # Extract just the filename for the response filename header
    response_filename = Path(clean_filename).name

    log_file_operation("serve", str(resolved_file_path), success=True)

    return FileResponse(
        path=str(resolved_file_path), filename=response_filename
    )  # filename helps browser suggest download name


@router.get("/textcontent/{filename:path}", response_model=TextContentResponse)
async def get_file_text_content(filename: str):
    """Gets the text content of a file from any directory."""
    log_api_request(f"/api/files/textcontent/{filename}", "GET")

    # Resolve file path with default to actors directory
    target_dir, clean_filename = resolve_file_path(
        filename, default_directory_type="actors"
    )

    # Handle both simple filenames and full paths
    file_path = target_dir / clean_filename

    # Validate file path and existence
    resolved_file_path = validate_file_path(file_path, target_dir)

    # Read the file content in thread pool to avoid blocking
    content = await run_in_thread_pool(read_text_file, resolved_file_path)

    log_file_operation("read_text", str(resolved_file_path), success=True)
    logger.info(f"Read {len(content)} characters from {clean_filename}")

    return TextContentResponse(
        filename=clean_filename,
        content=content,
        size=len(content.encode("utf-8")),
    )


@router.post("/save", response_model=GenericSaveResponse)
async def save_generic_file(request: GenericSaveRequest):
    """Saves generic JSON content to a file in the specified directory type."""
    log_api_request(
        "/api/files/save",
        "POST",
        {"directory_type": request.directory_type, "filename": request.filename},
    )

    try:
        # Save file in thread pool to avoid blocking
        resolved_file_path = await run_in_thread_pool(
            save_generic_json_file,
            request.directory_type,
            request.filename,
            request.content,
        )

        log_file_operation("save", str(resolved_file_path), success=True)
        logger.info(
            f"Successfully saved {request.filename} to {request.directory_type} directory"
        )

        return GenericSaveResponse(
            filename=request.filename,
            directory_type=request.directory_type,
            message=f"Successfully saved {request.filename} to {request.directory_type}",
            saved_path=str(resolved_file_path),
        )
    except HTTPException:
        raise
    except Exception as e:
        log_error_with_context(
            e, f"saving {request.filename} to {request.directory_type}"
        )
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")


@router.post("/save-script", response_model=GenericSaveResponse)
async def save_script(request: SaveScriptRequest):
    """Saves a script to a JSON file in the specified directory type."""
    log_api_request(
        "/api/files/save-script",
        "POST",
        {"directory_type": request.directory_type, "filename": request.filename},
    )

    try:
        # Convert the script to dict for the generic save function
        script_dict = request.script.model_dump()

        # Save file in thread pool to avoid blocking
        resolved_file_path = await run_in_thread_pool(
            save_generic_json_file,
            request.directory_type,
            request.filename,
            script_dict,
        )

        log_file_operation("save_script", str(resolved_file_path), success=True)
        logger.info(
            f"Successfully saved script {request.filename} to {request.directory_type} directory"
        )

        return GenericSaveResponse(
            filename=request.filename,
            directory_type=request.directory_type,
            message=f"Successfully saved script {request.filename} to {request.directory_type}",
            saved_path=str(resolved_file_path),
        )
    except HTTPException:
        raise
    except Exception as e:
        log_error_with_context(
            e, f"saving script {request.filename} to {request.directory_type}"
        )
        raise HTTPException(status_code=500, detail=f"Failed to save script: {e}")


@router.get("/load-script/{filename:path}", response_model=ScriptResponse)
async def load_script(filename: str):
    """Loads a script from a JSON file."""
    log_api_request(f"/api/files/load-script/{filename}", "GET")

    try:
        # Resolve file path with default to projects directory (where scripts would likely be stored)
        target_dir, clean_filename = resolve_file_path(
            filename, default_directory_type="scripts"
        )

        # Handle both simple filenames and full paths
        file_path = target_dir / clean_filename

        # Validate file path and existence
        resolved_file_path = validate_file_path(file_path, target_dir)

        # Read the JSON content in thread pool to avoid blocking
        content = await run_in_thread_pool(read_json_file, resolved_file_path)

        # Parse as Script object
        script = Script(**content)

        log_file_operation("load_script", str(resolved_file_path), success=True)
        logger.info(f"Successfully loaded script {clean_filename}")

        return ScriptResponse(filename=clean_filename, script=script)
    except HTTPException:
        raise
    except Exception as e:
        log_error_with_context(e, f"loading script {filename}")
        raise HTTPException(status_code=500, detail=f"Failed to load script: {e}")


@router.post("/upload", response_model=UploadFileResponse)
async def upload_file(file: UploadFile = File(...)):
    """Upload a file from desktop drag and drop to input/dropped_files directory."""
    log_api_request(
        "/api/files/upload",
        "POST",
        {"filename": file.filename, "content_type": file.content_type},
    )

    # Validate file type
    allowed_extensions = {
        ".txt",
        ".md",
        ".csv",
        ".wav",
        ".mp3",
        ".m4a",
        ".aac",
        ".ogg",
        ".flac",
    }
    file_ext = Path(file.filename).suffix.lower() if file.filename else ""

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{file_ext}'. Allowed types: {', '.join(allowed_extensions)}",
        )

    try:
        # Read file data
        file_data = await file.read()

        # Write file using utility function
        saved_path = await run_in_thread_pool(
            write_dropped_file, file_data, file.filename
        )

        # Create FileInfo for the uploaded file
        relative_path = f"input/dropped_files/{saved_path.name}"

        # Determine file type
        if file_ext in [".wav", ".mp3", ".m4a", ".aac", ".ogg", ".flac"]:
            file_type = "audio"
        elif file_ext in [".txt", ".csv"]:
            file_type = "text"
        else:
            file_type = "other"

        file_info = FileInfo(
            name=saved_path.name,
            type="file",
            path=relative_path,
            size=len(file_data),
            extension=file_ext,
            file_type=file_type,
            actor_data=None,
            voice_mode_data=None,
        )

        log_file_operation("upload", str(saved_path), success=True)
        logger.info(f"Successfully uploaded {file.filename} as {saved_path.name}")

        return UploadFileResponse(
            filename=saved_path.name,
            original_filename=file.filename,
            file_path=relative_path,
            file_info=file_info,
        )

    except HTTPException:
        raise
    except Exception as e:
        log_error_with_context(e, f"uploading file {file.filename}")
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {e}")


@router.post("/export-timeline", response_model=ExportTimelineResponse)
async def export_timeline(request: ExportTimelineRequest):
    """Exports the current timeline by concatenating all active audio clips."""
    log_api_request(
        "/api/files/export-timeline",
        "POST",
        {"output_subfolder": request.output_subfolder},
    )

    try:
        # Import websocket manager for progress updates
        from backend.core.router_websocket import SimpleWebSocketManager

        # Send export start event
        await SimpleWebSocketManager._broadcast(
            {
                "type": "export-start",
                "timestamp": datetime.now().isoformat(),
            }
        )

        # Collect active audio files from script
        audio_files = []
        for row_index, row in enumerate(request.script.history_grid.grid):
            current_cell = row.cells[row.current_index]
            if current_cell.generated_filepath and not current_cell.hide:
                audio_files.append(current_cell.generated_filepath)

        if not audio_files:
            raise HTTPException(
                status_code=400, detail="No audio files found to export"
            )

        logger.info(f"Found {len(audio_files)} audio files to concatenate")

        # Send progress update
        await SimpleWebSocketManager._broadcast(
            {
                "type": "export-progress",
                "progress_percentage": 25,
                "step_name": f"Loading {len(audio_files)} audio files...",
                "timestamp": datetime.now().isoformat(),
            }
        )

        # Concatenate audio files using existing utility
        concatenated_audio = await run_in_thread_pool(
            concatenate_audio_files, audio_files, file_root="output"
        )

        if concatenated_audio is None:
            raise HTTPException(
                status_code=500, detail="Failed to concatenate audio files"
            )

        # Send progress update
        await SimpleWebSocketManager._broadcast(
            {
                "type": "export-progress",
                "progress_percentage": 75,
                "step_name": "Saving concatenated audio...",
                "timestamp": datetime.now().isoformat(),
            }
        )

        # Save concatenated audio
        output_dir = get_directory_path("output") / request.output_subfolder
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / "output.wav"

        # Use soundfile to save the concatenated audio
        await run_in_thread_pool(_save_audio_file, concatenated_audio, str(output_file))

        # Construct relative path for response
        relative_output_path = f"output/{request.output_subfolder}/output.wav"

        log_file_operation("export_timeline", str(output_file), success=True)
        logger.info(f"Successfully exported timeline to {relative_output_path}")

        # Send completion event
        await SimpleWebSocketManager._broadcast(
            {
                "type": "export-complete",
                "output_file_path": relative_output_path,
                "timestamp": datetime.now().isoformat(),
            }
        )

        return ExportTimelineResponse(
            message=f"Successfully exported timeline to {relative_output_path}",
            output_file_path=relative_output_path,
        )

    except HTTPException:
        # Send error event for HTTP exceptions
        await SimpleWebSocketManager._broadcast(
            {
                "type": "export-error",
                "error": "Failed to export timeline",
                "timestamp": datetime.now().isoformat(),
            }
        )
        raise
    except Exception as e:
        log_error_with_context(e, "exporting timeline")

        # Send error event
        await SimpleWebSocketManager._broadcast(
            {
                "type": "export-error",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }
        )

        raise HTTPException(status_code=500, detail=f"Failed to export timeline: {e}")
