#!/bin/bash
set -e

export OLLAMA_KEEP_ALIVE=30m

apt install -y pciutils

# Create and activate virtual environment
python3 -m venv ollama_env
. ollama_env/bin/activate

# Check if ollama is already installed
if ! command -v ollama >/dev/null 2>&1; then
    echo "Installing Ollama..."
    
    # Install Python dependencies (if needed for client libraries)
    pip install --upgrade pip
    pip install ollama-python requests

    # Download and install Ollama
    curl -fsSL https://ollama.ai/install.sh | sh
else
    echo "Ollama is already installed, skipping installation steps"
fi

# Start Ollama service in background, binding to all interfaces
export OLLAMA_HOST=0.0.0.0:11434
nohup ollama serve > logs/ollama.log 2>&1 &

# Wait for service to start
sleep 5

TWENTYSEVEN='gemma3:27b'
TWELVE='gemma3:12b'
FOUR='gemma3:4b'
ONE='gemma3:1b' # Note: this model is very weak

# Default model
MODEL=$TWENTYSEVEN

# Parse command line arguments
while [ $# -gt 0 ]; do
    case $1 in
        --one)
            MODEL=$ONE
            shift
            ;;
        --four)
            MODEL=$FOUR
            shift
            ;;
        --twelve)
            MODEL=$TWELVE
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--one|--four|--twelve]"
            exit 1
            ;;
    esac
done

echo "Pulling model: $MODEL"

ollama pull $MODEL
# ollama pull llama3:8b
# ollama pull llama3:70b

# These models fail in 'step 1' of robust workflow due to padding issues (?)
# ollama pull deepseek-r1:32b
# ollama pull gpt-oss:20b 

echo "Ollama is running on http://$(hostname -I | awk '{print $1}'):11434"
echo "OpenAI-compatible endpoint: http://$(hostname -I | awk '{print $1}'):11434/v1"
echo "Log file: ollama.log"
echo "To stop: pkill ollama"
