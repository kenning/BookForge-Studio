import os
import json
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

from fastapi import HTTPException

# Import shared configuration
from backend.core.config import (
    DIRECTORY_MAPPINGS,
)


def flatten_extend(matrix):
    flat_list = []
    for row in matrix:
        flat_list.extend(row)
    return flat_list


def get_directory_path(directory_type: str) -> Path:
    """
    Get the directory path for a given directory type.

    Args:
        directory_type: The type of directory ('actors', 'voice_modes', 'projects', 'output')

    Returns:
        Path: The directory path

    Raises:
        HTTPException: If directory type is invalid
    """
    if directory_type not in DIRECTORY_MAPPINGS:
        valid_types = ", ".join(DIRECTORY_MAPPINGS.keys())
        raise HTTPException(
            status_code=400,
            detail=f"Invalid directory type '{directory_type}'. Must be one of: {valid_types}",
        )

    return DIRECTORY_MAPPINGS[directory_type]


def resolve_file_path(
    filename: str, default_directory_type: str = "actors"
) -> Tuple[Path, str]:
    """
    Resolve a filename with directory prefix to the actual file path.

    Args:
        filename: The filename with optional directory type prefix (e.g., 'actors/file.json')
        default_directory_type: Default directory type when no prefix is found

    Returns:
        tuple: (target_directory_path, cleaned_filename)

    Raises:
        HTTPException: If filename is invalid or directory type is invalid
    """
    if ".." in filename:
        raise HTTPException(
            status_code=400,
            detail="Invalid filename - path traversal not allowed.",
        )

    # Check for directory type prefix
    for dir_type in DIRECTORY_MAPPINGS.keys():
        prefix = f"{dir_type}/"
        if filename.startswith(prefix):
            return get_directory_path(dir_type), filename[len(prefix) :]

    # No prefix found, use default directory type
    return get_directory_path(default_directory_type), filename


def validate_file_path(file_path: Path, target_dir: Path) -> Path:
    """
    Validate that a file path is within the target directory and exists.

    Args:
        file_path: The file path to validate
        target_dir: The target directory that should contain the file

    Returns:
        Path: The resolved file path

    Raises:
        HTTPException: If file is not found or access is denied
    """
    try:
        resolved_file_path = file_path.resolve()
        resolved_target_dir = target_dir.resolve()

        # Check if the file path is within the target directory
        if not str(resolved_file_path).startswith(str(resolved_target_dir)):
            raise HTTPException(
                status_code=404, detail="File not found or access denied."
            )

        # Check if file exists
        if not resolved_file_path.is_file():
            raise HTTPException(status_code=404, detail="File not found.")

        return resolved_file_path

    except HTTPException:
        raise
    except Exception as e:
        print("error", e)
        raise HTTPException(status_code=404, detail="File not found or access denied.")


def read_text_file(file_path: Path) -> str:
    """
    Read text content from a file.

    Args:
        file_path: Path to the file to read

    Returns:
        str: The file content

    Raises:
        HTTPException: If file cannot be read or is not a valid text file
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return content
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="File is not a valid text file or contains non-UTF-8 characters.",
        )
    except Exception as e:
        print("error", e)
        raise HTTPException(status_code=500, detail=f"Failed to read file: {e}")


def read_json_file(file_path: Path) -> dict:
    """
    Read and parse JSON content from a file.

    Args:
        file_path: Path to the JSON file to read

    Returns:
        dict: The parsed JSON data

    Raises:
        HTTPException: If file cannot be read or contains invalid JSON
    """
    try:
        content = read_text_file(file_path)
        return json.loads(content)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON format: {e}")
    except HTTPException:
        raise
    except Exception as e:
        print("error", e)
        raise HTTPException(status_code=500, detail=f"Failed to read JSON file: {e}")


def write_json_file(file_path: Path, data: dict, target_dir: Path) -> Path:
    """
    Write data to a JSON file with validation.

    Args:
        file_path: Path where to write the file
        data: Data to write as JSON
        target_dir: Target directory for security validation

    Returns:
        Path: The resolved file path where data was written

    Raises:
        HTTPException: If file cannot be written or path is invalid
    """
    try:
        resolved_file_path = file_path.resolve()
        resolved_target_dir = target_dir.resolve()

        # Check if the file path is within the target directory
        if not str(resolved_file_path).startswith(str(resolved_target_dir)):
            raise HTTPException(status_code=400, detail="Invalid file path.")

        with open(resolved_file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return resolved_file_path

    except HTTPException:
        raise
    except Exception as e:
        print("error", e)
        raise HTTPException(status_code=500, detail=f"Failed to write file: {e}")


def write_text_file(file_path: Path, content: str, target_dir: Path) -> Path:
    """
    Write text content to a file with validation.

    Args:
        file_path: Path where to write the file
        content: Text content to write
        target_dir: Target directory for security validation

    Returns:
        Path: The resolved file path where content was written

    Raises:
        HTTPException: If file cannot be written or path is invalid
    """
    try:
        resolved_file_path = file_path.resolve()
        resolved_target_dir = target_dir.resolve()

        # Check if the file path is within the target directory
        if not str(resolved_file_path).startswith(str(resolved_target_dir)):
            raise HTTPException(status_code=400, detail="Invalid file path.")

        with open(resolved_file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return resolved_file_path

    except HTTPException:
        raise
    except Exception as e:
        print("error", e)
        raise HTTPException(status_code=500, detail=f"Failed to write file: {e}")


def save_generic_json_file(
    directory_type: str, filename: str, data: Dict[str, Any], subdirectory: str = ""
) -> Path:
    """
    Save a generic JSON file to a specific directory type.

    Args:
        directory_type: The directory type where to save the file
        filename: The filename (will have .json added if missing)
        data: The data to save as JSON

    Returns:
        Path: The resolved file path where data was written

    Raises:
        HTTPException: If directory type is invalid or file cannot be written
    """
    # Ensure filename has .json extension
    if not filename.endswith(".json"):
        filename += ".json"

    # Get target directory
    target_dir = get_directory_path(directory_type)

    # Create file path
    file_path = target_dir / subdirectory / filename
    if not file_path.parent.exists():
        file_path.parent.mkdir(parents=True, exist_ok=True)

    # Write the file
    return write_json_file(file_path, data, target_dir)


def write_dropped_file(file_data: bytes, filename: str) -> Path:
    """
    Write dropped file data to the input/dropped_files directory with timestamp naming.

    Args:
        file_data: The raw file data bytes
        filename: The original filename

    Returns:
        Path: The resolved file path where data was written

    Raises:
        HTTPException: If file cannot be written
    """
    from datetime import datetime

    # Get the input directory and create dropped_files subdirectory
    target_dir = get_directory_path("input")
    dropped_files_dir = target_dir / "dropped_files"
    dropped_files_dir.mkdir(parents=True, exist_ok=True)

    # Generate timestamp-based filename to avoid collisions
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name, ext = os.path.splitext(filename)
    timestamped_filename = f"{name}_{timestamp}{ext}"

    file_path = dropped_files_dir / timestamped_filename

    try:
        with open(file_path, "wb") as f:
            f.write(file_data)
        return file_path
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to write dropped file: {e}"
        )


try:
    import librosa
    import soundfile as sf
    import numpy as np
    from urllib.parse import unquote
    from backend.core.utils.file_utils import resolve_file_path

    AUDIO_LIBS_AVAILABLE = True
except ImportError as e:
    print(f"Error importing audio dependencies: {e}")
    AUDIO_LIBS_AVAILABLE = False


def concatenate_audio_files(
    audio_paths: List[str],
    file_root: str = "root",
    target_sr: int = 44100,
) -> Optional[np.ndarray]:
    """Concatenate multiple audio files into a single audio array."""
    if not AUDIO_LIBS_AVAILABLE:
        print("Audio processing libraries not available for concatenation")
        return None

    if not audio_paths:
        return None

    concatenated_audio = []

    for audio_path in audio_paths:
        try:
            # Decode URL-encoded filepath
            decoded_path = unquote(audio_path)

            # Resolve path relative to project root
            dir, filename = resolve_file_path(decoded_path, file_root)

            # Load audio with librosa
            audio, sr = librosa.load(dir / filename, sr=target_sr)
            concatenated_audio.append(audio)
        except Exception as e:
            print(f"Could not load audio file {audio_path}: {e}")
            continue

    if not concatenated_audio:
        return None

    # Concatenate all audio arrays
    return np.concatenate(concatenated_audio)
