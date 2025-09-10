from typing import List, Dict, Optional, Literal, Any
from pydantic import BaseModel


class BetweenLineElement(BaseModel):
    """Element that appears between script lines in the grid"""

    # Add basic structure - can be extended based on actual usage
    content: str
    element_type: str


class ScriptHistoryGridCell(BaseModel):
    """A single cell in the script history grid"""

    hide: bool = False
    height: int = 1

    # texts, speakers, and actors are all:
    # 1 element if single line
    # 0 if hide=true
    # and multiple if this is a multiple-speaker item (following cells will be hide=true)
    texts: List[str] = []
    speakers: List[str] = []
    actors: List[str] = []  # filepath strings
    voice_mode: str = ""  # filepath string
    generated_filepath: str  # filepath string
    waveform_data: List[float] = []


class ScriptHistoryGridRow(BaseModel):
    """A single row in the script history grid"""

    current_index: int
    cells: List[ScriptHistoryGridCell]


class ScriptHistoryGrid(BaseModel):
    """Grid structure for script history tracking"""

    grid: List[ScriptHistoryGridRow]
    between_lines_elements: List[BetweenLineElement]


class Script(BaseModel):
    """A script with history grid and speaker mappings"""

    type: Literal["script"]
    title: str = ""
    history_grid: ScriptHistoryGrid
    speaker_to_actor_map: Dict[str, str]  # speaker name -> actor filepath
    speaker_to_voice_mode_map: Dict[str, str]  # speaker name -> voice mode filepath


class Step(BaseModel):
    name: str
    display_name: str
    description: str
    input_type: str
    output_type: str
    category: str
    step_type: Literal[
        "start_step", "pre_generation_step", "generation_step", "post_generation_step"
    ]
    version: str
    parameters: Dict[str, Any]
    model_requirement: Optional[str] = None
    # NOTE: "multi_speaker" is for the frontend and is often not set. In fact, this whole class is
    # kind of just for the frontend...
    multi_speaker: bool = False


class VoiceModeData(BaseModel):
    """Data for a voice mode"""

    model_config = {"extra": "ignore"}  # Ignore extra fields in JSON

    type: Literal["voice_mode"] = "voice_mode"
    steps: List[Step] = []


class ActorData(BaseModel):
    """Data for an actor"""

    model_config = {"extra": "ignore"}  # Ignore extra fields in JSON

    type: Literal["actor"] = "actor"
    clip_path: Optional[str] = ""
    clip_transcription: Optional[str] = ""
    notes: Optional[str] = ""
    is_favorite: Optional[bool] = False
