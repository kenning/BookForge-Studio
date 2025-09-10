from typing import List, Optional, Literal
from pydantic import BaseModel
from core.data_types.script_and_text_types import ActorData, VoiceModeData


class FileInfo(BaseModel):
    """File information structure matching frontend FileInfo type"""

    path: str  # Note: path is a unique id because no two files can have identical full paths
    name: str
    type: Literal["file"]
    size: Optional[int] = 0
    extension: Optional[str] = ""
    file_type: Literal["audio", "text", "actor", "script", "voice_mode", "other"]
    actor_data: Optional[ActorData] = None
    voice_mode_data: Optional[VoiceModeData] = None


class DirectoryInfo(BaseModel):
    """Directory information structure matching frontend DirectoryInfo type"""

    name: str
    type: Literal["directory"]
    path: str
    files: List[FileInfo]
    directories: List["DirectoryInfo"]
    error: Optional[str] = None


# Enable forward references for recursive DirectoryInfo
DirectoryInfo.model_rebuild()
