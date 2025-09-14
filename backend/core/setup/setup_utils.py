from pathlib import Path
import pandas as pd
from backend.core.router_text_workflows import (
    _execute_text_workflow_background,
)

from backend.core.data_types.filesystem_types import FileInfo
from backend.core.data_types.script_and_text_types import ActorData, VoiceModeData
from backend.core.utils.logger import get_logger
from backend.core.router_filesystem import save_generic_json_file

logger = get_logger(__name__)


def create_actor_files_from_sampler_dataset():
    """Create actor files from the sampler dataset CSV"""
    sampler_dir = Path("files/input/sampler")
    csv_path = sampler_dir / "sampler_voices_dataset_metadata.csv"

    try:
        # Load the CSV file
        df = pd.read_csv(csv_path)

        for _, row in df.iterrows():
            person = row["Person"]
            readable_name = row["Readable name"]
            filepath = row["Filepath"]
            transcription = row["Transcription"]
            clip_notes = row["Clip notes"]
            dataset = row["Dataset"]
            license_info = row["License"]
            dataset_notes = row["Dataset notes"]

            # Create the notes section as specified
            notes = f"{clip_notes}\n\n-- \n{dataset}\n{license_info}\n{dataset_notes}"

            # Create the clip path (remove files/ prefix)
            clip_path = f"input/sampler/{filepath}"

            # Create the actor data
            actor_data = ActorData(
                type="actor",
                clip_path=clip_path,
                clip_transcription=transcription,
                notes=notes,
            )

            # Create the actor file structure
            actor_file = FileInfo(
                path=f"{readable_name}.json",
                name=f"{readable_name}.json",
                type="file",
                file_type="actor",
                actor_data=actor_data.model_dump(),
                voice_mode_data=None,
            )

            # Save to files/actors/sampler/{dataset}/{readable_name}.json
            save_generic_json_file(
                "actors",
                f"{readable_name}.json",
                actor_file.model_dump(),
                subdirectory=f"sampler/{dataset}",
            )

        logger.info(f"Created {len(df)} actor files from sampler dataset")

    except Exception as e:
        logger.error(f"Error creating actor files from sampler dataset: {e}")
    finally:
        logger.info("Done creating actor files from sampler dataset")


async def create_script_from_anita_dataset():
    # Read all files from files/input/csv/ANITA/
    anita_dir_wuthering_heights = Path("files/input/csv/ANITA/wuthering_heights")
    base_path = Path("files/input")

    try:
        for file in anita_dir_wuthering_heights.glob("*.csv"):
            # Normally would be like 'files/input/csv/ANITA/wuthering_heights',
            # remove first 2 folders
            relative_path = (anita_dir_wuthering_heights / file.name).relative_to(
                base_path
            )
            no_file_slash = str(relative_path)

            response = await _execute_text_workflow_background(
                "csv_to_psss", {"filepath": no_file_slash}, "0"
            )

            save_generic_json_file(
                "scripts",
                "wuthering_heights_" + file.stem[-3:] + ".json",
                response["script"],
                subdirectory="wuthering_heights",
            )
    except Exception as e:
        logger.error("Error creating script from ANITA dataset: ", e)
    finally:
        logger.info(
            "Done creating starter project of Wuthering Heights from ANITA dataset"
        )


if __name__ == "__main__":
    create_actor_files_from_sampler_dataset()
