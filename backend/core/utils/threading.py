import asyncio
from backend.core.utils.logger import get_logger

logger = get_logger(__name__)


async def run_in_thread_pool(func, *args, **kwargs):
    """
    Run a blocking function in a thread pool to avoid blocking the event loop.
    Centralizes thread pool management and error handling.

    Args:
        func: The blocking function to run
        *args: Arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function

    Returns:
        The result of the function call
    """
    loop = asyncio.get_event_loop()
    try:
        if kwargs:
            # If we have kwargs, wrap the function call
            return await loop.run_in_executor(None, lambda: func(*args, **kwargs))
        else:
            # Direct function call with args only
            return await loop.run_in_executor(None, func, *args)
    except Exception as e:
        logger.error(f"Error in thread pool execution: {e}")
        raise
