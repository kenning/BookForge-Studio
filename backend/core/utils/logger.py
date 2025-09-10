import logging
import os
from pathlib import Path
from typing import Optional

# Get the log file path
BASE_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent
)  # Points to project root
LOG_FILE_PATH = BASE_DIR / "logs" / "backend_logs.txt"

# Ensure logs directory exists
LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)


def setup_logging(
    log_level: str = "INFO", log_file: Optional[str] = None
) -> logging.Logger:
    """
    Set up logging configuration with both file and console handlers.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional custom log file path

    Returns:
        Configured logger instance
    """
    if log_file:
        file_path = Path(log_file)
    else:
        file_path = LOG_FILE_PATH

    # Clear any existing handlers to avoid duplicates
    logging.getLogger().handlers.clear()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(levelname)s - %(asctime)s - %(name)s - %(message)s",
        datefmt="%H:%M:%S",  # Only show hours:minutes:seconds
        handlers=[
            logging.FileHandler(file_path, encoding="utf-8"),
            logging.StreamHandler(),  # Console output
        ],
    )

    return logging.getLogger(__name__)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given name."""
    return logging.getLogger(name)


# Convenience functions for common logging patterns
def log_api_request(endpoint: str, method: str = "GET", params: dict = None):
    """Log API request details."""
    logger = get_logger("api")
    params_str = f" with params: {params}" if params else ""
    logger.info(f"{method} {endpoint}{params_str}")


def log_step_execution(step_name: str, status: str = "started", details: str = ""):
    """Log step execution progress."""
    logger = get_logger("steps")
    message = f"Step '{step_name}' {status}"
    if details:
        message += f" - {details}"
    logger.info(message)


def log_file_operation(operation: str, file_path: str, success: bool = True):
    """Log file operations."""
    logger = get_logger("files")
    status = "completed" if success else "failed"
    logger.info(f"File {operation} {status}: {file_path}")


def log_error_with_context(error: Exception, context: str = ""):
    """Log errors with additional context."""
    logger = get_logger("error")
    context_str = f" ({context})" if context else ""
    logger.error(f"Error{context_str}: {type(error).__name__}: {str(error)}")


# Quick logging functions (can import these directly)
def info(message: str, logger_name: str = "app"):
    get_logger(logger_name).info(message)


def error(message: str, logger_name: str = "app"):
    get_logger(logger_name).error(message)


def warning(message: str, logger_name: str = "app"):
    get_logger(logger_name).warning(message)


def debug(message: str, logger_name: str = "app"):
    get_logger(logger_name).debug(message)
