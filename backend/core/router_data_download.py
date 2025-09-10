"""
Data Download Router

Provides API endpoints for downloading external datasets and models.
Supports downloading from Hugging Face Hub and other sources.
"""

import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from huggingface_hub import snapshot_download

# Import shared configuration
from backend.core.config import PROJECT_ROOT, INPUT_DIR

# Import logging utilities
from backend.core.utils.logger import (
    get_logger,
    log_api_request,
    log_error_with_context,
)

logger = get_logger(__name__)


class DownloadRequest(BaseModel):
    """Base model for download requests"""

    force_download: Optional[bool] = False
    resume_download: Optional[bool] = True


class DownloadResponse(BaseModel):
    """Response model for download operations"""

    status: str
    message: str
    download_path: str
    size_info: Optional[str] = None


router = APIRouter(prefix="/api/data_download", tags=["data_download"])


def download_huggingface_repo(
    repo_id: str,
    local_dir: Path,
    force_download: bool = False,
    resume_download: bool = True,
    repo_type: str = "model",
    allow_patterns: Optional[list] = None,
):
    """
    Download a Hugging Face repository to a local directory (synchronous version).
    For background downloads, use execute_download_background instead.

    Args:
        repo_id: The Hugging Face repository ID (e.g., "kyutai/tts-voices")
        local_dir: Local directory path to download to
        force_download: Whether to force redownload even if files exist
        resume_download: Whether to resume partial downloads
        repo_type: Type of repository ("model" or "dataset")
        allow_patterns: List of patterns to filter which files to download (e.g., ["vctk/*"])

    Returns:
        str: Path to the downloaded directory
    """
    try:
        # Ensure the parent directory exists
        local_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Starting download of {repo_type} {repo_id} to {local_dir}")
        if allow_patterns:
            logger.info(f"Filtering download with patterns: {allow_patterns}")

        # Download the repository
        downloaded_path = snapshot_download(
            repo_id=repo_id,
            repo_type=repo_type,
            local_dir=str(local_dir),
            force_download=force_download,
            resume_download=resume_download,
            local_dir_use_symlinks=False,  # Use actual files instead of symlinks
            allow_patterns=allow_patterns,
        )

        logger.info(
            f"Successfully downloaded {repo_type} {repo_id} to {downloaded_path}"
        )
        return downloaded_path

    except Exception as e:
        log_error_with_context(e, f"downloading Hugging Face {repo_type} {repo_id}")
        raise e


anita_dir = INPUT_DIR / "csv" / "ANITA"
sampler_dir = INPUT_DIR / "sampler"


@router.post("/sampler_dataset", response_model=DownloadResponse)
async def download_sampler_dataset(request: DownloadRequest):
    """
    Download the tts-voices-sampler dataset from Hugging Face.

    Downloads the "nick-mccormick/tts-voices-sampler" dataset to files/input/sampler/.

    Args:
        request: Download configuration options

    Returns:
        Download status and information
    """
    log_api_request(
        "/api/data_download/sampler_dataset",
        "POST",
        {
            "force_download": request.force_download,
            "resume_download": request.resume_download,
        },
    )

    repo_id = "nick-mccormick/tts-voices-sampler"

    try:
        # Check if already downloaded (unless force download is requested)
        if (
            sampler_dir.exists()
            and list(sampler_dir.iterdir())
            and not request.force_download
        ):
            logger.info(f"Sampler dataset already exists at {sampler_dir}")

            # Get directory size info
            total_size = sum(
                f.stat().st_size for f in sampler_dir.rglob("*") if f.is_file()
            )
            size_mb = total_size / (1024 * 1024)

            return DownloadResponse(
                status="already_exists",
                message=f"Sampler dataset already downloaded at {sampler_dir}",
                download_path=str(sampler_dir),
                size_info=f"{size_mb:.1f} MB",
            )

        # Perform the download
        logger.info(f"Downloading {repo_id} to {sampler_dir}")

        downloaded_path = download_huggingface_repo(
            repo_id=repo_id,
            local_dir=sampler_dir,
            force_download=request.force_download,
            resume_download=request.resume_download,
            repo_type="dataset",
            allow_patterns=["sampler_voices_dataset_metadata.csv", "data.zip"],
        )

        # Unzip the data.zip file
        import zipfile

        zip_path = sampler_dir / "data.zip"
        if zip_path.exists():
            logger.info(f"Extracting {zip_path} to {sampler_dir}")
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(sampler_dir)
            # Remove the zip file after extraction
            zip_path.unlink()
            logger.info("Extraction completed and zip file removed")

        # Get final size info
        total_size = sum(
            f.stat().st_size for f in sampler_dir.rglob("*") if f.is_file()
        )
        size_mb = total_size / (1024 * 1024)
        file_count = len(list(sampler_dir.rglob("*")))

        logger.info(f"Download completed: {file_count} files, {size_mb:.1f} MB")

        return DownloadResponse(
            status="success",
            message=f"Successfully downloaded sampler dataset to {sampler_dir}",
            download_path=str(sampler_dir),
            size_info=f"{file_count} files, {size_mb:.1f} MB",
        )

    except Exception as e:
        log_error_with_context(e, f"downloading sampler dataset to {sampler_dir}")
        raise HTTPException(
            status_code=500, detail=f"Failed to download sampler dataset: {str(e)}"
        )


@router.get("/status/sampler_dataset", response_model=DownloadResponse)
async def check_sampler_dataset_status():
    """
    Check the download status of sampler dataset.

    Returns information about whether the dataset is downloaded and its size.

    Returns:
        Status information about the dataset
    """
    log_api_request("/api/data_download/status/sampler_dataset", "GET")

    if not sampler_dir.exists() or not list(sampler_dir.iterdir()):
        return DownloadResponse(
            status="not_downloaded",
            message="Sampler dataset not downloaded",
            download_path=str(sampler_dir),
            size_info="0 files, 0 MB",
        )

    # Get directory info
    total_size = sum(f.stat().st_size for f in sampler_dir.rglob("*") if f.is_file())
    size_mb = total_size / (1024 * 1024)
    file_count = len(list(sampler_dir.rglob("*")))

    return DownloadResponse(
        status="downloaded",
        message=f"Sampler dataset is available at {sampler_dir}",
        download_path=str(sampler_dir),
        size_info=f"{file_count} files, {size_mb:.1f} MB",
    )


@router.post("/anita_dataset", response_model=DownloadResponse)
async def download_anita_dataset(request: DownloadRequest):
    """
    Download the ANITA dataset from Hugging Face.

    Downloads the "nick-mccormick/ANITA" dataset to files/input/csv/ANITA/.

    Args:
        request: Download configuration options

    Returns:
        Download status and information
    """
    log_api_request(
        "/api/data_download/anita_dataset",
        "POST",
        {
            "force_download": request.force_download,
            "resume_download": request.resume_download,
        },
    )

    repo_id = "nick-mccormick/ANITA"

    try:
        # Check if already downloaded (unless force download is requested)
        if (
            anita_dir.exists()
            and list(anita_dir.iterdir())
            and not request.force_download
        ):
            logger.info(f"ANITA dataset already exists at {anita_dir}")

            # Get directory size info
            total_size = sum(
                f.stat().st_size for f in anita_dir.rglob("*") if f.is_file()
            )
            size_mb = total_size / (1024 * 1024)

            return DownloadResponse(
                status="already_exists",
                message=f"ANITA dataset already downloaded at {anita_dir}",
                download_path=str(anita_dir),
                size_info=f"{size_mb:.1f} MB",
            )

        # Perform the download
        logger.info(f"Downloading {repo_id} to {anita_dir}")

        downloaded_path = download_huggingface_repo(
            repo_id=repo_id,
            local_dir=anita_dir,
            force_download=request.force_download,
            resume_download=request.resume_download,
            repo_type="dataset",
            allow_patterns=["ANITA.zip"],
        )

        # Unzip the ANITA.zip file
        import zipfile

        zip_path = anita_dir / "ANITA.zip"
        if zip_path.exists():
            logger.info(f"Extracting {zip_path} to {anita_dir}")
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(anita_dir)
            # Remove the zip file after extraction
            zip_path.unlink()
            logger.info("Extraction completed and zip file removed")

        # Get final size info
        total_size = sum(f.stat().st_size for f in anita_dir.rglob("*") if f.is_file())
        size_mb = total_size / (1024 * 1024)
        file_count = len(list(anita_dir.rglob("*")))

        logger.info(f"Download completed: {file_count} files, {size_mb:.1f} MB")

        return DownloadResponse(
            status="success",
            message=f"Successfully downloaded ANITA dataset to {anita_dir}",
            download_path=str(anita_dir),
            size_info=f"{file_count} files, {size_mb:.1f} MB",
        )

    except Exception as e:
        log_error_with_context(e, f"downloading ANITA dataset to {anita_dir}")
        raise HTTPException(
            status_code=500, detail=f"Failed to download ANITA dataset: {str(e)}"
        )


@router.get("/status/anita_dataset", response_model=DownloadResponse)
async def check_anita_dataset_status():
    """
    Check the download status of ANITA dataset.

    Returns information about whether the dataset is downloaded and its size.

    Returns:
        Status information about the dataset
    """
    log_api_request("/api/data_download/status/anita_dataset", "GET")

    if not anita_dir.exists() or not list(anita_dir.iterdir()):
        return DownloadResponse(
            status="not_downloaded",
            message="ANITA dataset not downloaded",
            download_path=str(anita_dir),
            size_info="0 files, 0 MB",
        )

    # Get directory info
    total_size = sum(f.stat().st_size for f in anita_dir.rglob("*") if f.is_file())
    size_mb = total_size / (1024 * 1024)
    file_count = len(list(anita_dir.rglob("*")))

    return DownloadResponse(
        status="downloaded",
        message=f"ANITA dataset is available at {anita_dir}",
        download_path=str(anita_dir),
        size_info=f"{file_count} files, {size_mb:.1f} MB",
    )
