"""
URL Utilities for File Path Encoding

Utilities for safely encoding file paths in URLs to avoid issues with
slashes and special characters in URL path parameters.
"""

from base64 import b64decode, b64encode
import os
import urllib.parse


def encode_filepath_for_url(file_path: str) -> str:
    if not file_path:
        return ""

    return b64encode(file_path.encode("utf-8")).decode("utf-8")


def decode_filepath_from_url(encoded_path: str) -> str:
    if not encoded_path:
        return ""

    try:
        return b64decode(encoded_path).decode("utf-8")
        # return urllib.parse.unquote(encoded_path)
    except Exception as e:
        raise ValueError(f"Invalid encoded file path: {encoded_path}") from e


def add_file_prefix(file_path: str) -> str:
    if os.environ.get("TESTING", "false").lower() == "true":
        # Test files are kept in the testing directory to keep them out of the way.
        return file_path
    return f"files/{file_path}"
