from backend.core.setup.setup_utils import (
    create_actor_files_from_sampler_dataset,
    create_script_from_anita_dataset,
)
from backend.core.utils.logger import get_logger

from backend.core.router_data_download import (
    DownloadRequest,
    download_sampler_dataset,
    download_anita_dataset,
    check_sampler_dataset_status,
    check_anita_dataset_status,
)

logger = get_logger(__name__)


async def setup_process():
    sampler_dataset_status = await check_sampler_dataset_status()
    if not sampler_dataset_status.status == "downloaded":
        logger.info("Downloading sampler dataset for starter project")
        await download_sampler_dataset(
            DownloadRequest(
                force_download=False,
                resume_download=True,
            )
        )
        # Create actor files from the CSV
        create_actor_files_from_sampler_dataset()

    anita_dataset_status = await check_anita_dataset_status()
    if not anita_dataset_status.status == "downloaded":
        logger.info("Downloading ANITA dataset for starter project")
        await download_anita_dataset(
            DownloadRequest(
                force_download=True,
                resume_download=True,
            )
        )
        await create_script_from_anita_dataset()
