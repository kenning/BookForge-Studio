import os

from backend.core.utils.logger import get_logger

logger = get_logger(__name__)


# File path resolution
def resolve_file_path(file_path: str, project_root: str) -> str:
    print(f"Resolving file path, starting with  : {file_path}")
    """
    Resolve file paths relative to project root.
    Services run from models/model_name/ but files are at project root.
    """
    if os.path.isabs(file_path):
        return file_path

    # Get project root (two directories up from service)
    resolved_path = os.path.join(project_root, file_path)

    logger.debug(f"Resolved {file_path} -> {resolved_path}")
    return resolved_path
