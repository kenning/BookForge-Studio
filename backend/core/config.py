from pathlib import Path

# --- Configuration for File Directories ---
# Use absolute paths or paths relative to this config file
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent  # Points to project root

# Define the new modular directory structure
INPUT_DIR = PROJECT_ROOT / "files" / "input"
ACTORS_DIR = PROJECT_ROOT / "files" / "actors"
VOICE_MODES_DIR = PROJECT_ROOT / "files" / "voice_modes"
SCRIPTS_DIR = PROJECT_ROOT / "files" / "scripts"
OUTPUT_DIR = PROJECT_ROOT / "files" / "output"

# Directory type mappings for easy access
DIRECTORY_MAPPINGS = {
    "input": INPUT_DIR,
    "actors": ACTORS_DIR,
    "voice_modes": VOICE_MODES_DIR,
    "scripts": SCRIPTS_DIR,
    "output": OUTPUT_DIR,
    "root": PROJECT_ROOT,
}

# Ensure all directories exist
for dir_path in DIRECTORY_MAPPINGS.values():
    dir_path.mkdir(parents=True, exist_ok=True)
