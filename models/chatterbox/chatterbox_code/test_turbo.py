#!/usr/bin/env python3
"""
Test script to reproduce the Float/Double error in Chatterbox Turbo.
This will help identify the exact line number where the error occurs.
"""

import sys
import os
import traceback

# Add the parent directory to the path so we can import tts_turbo
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import torch

def test_chatterbox_turbo():
    """Test the ChatterboxTurboTTS generate function."""
    print("=" * 80)
    print("Testing Chatterbox Turbo TTS")
    print("=" * 80)
    
    try:
        from tts_turbo import ChatterboxTurboTTS
        
        # Determine device
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"\nUsing device: {device}")
        
        # Load model
        print("\nLoading Chatterbox Turbo model...")
        model = ChatterboxTurboTTS.from_pretrained(device)
        print("✓ Model loaded successfully")
        
        # Test text
        test_text = "Hello, this is a test of the Chatterbox turbo model."
        
        # You'll need to provide a valid audio prompt path
        # Replace this with an actual audio file path on your system
        audio_prompt_path = None  # Set to None to use built-in voice if available
        
        print(f"\nGenerating audio for text: '{test_text}'")
        print("Parameters:")
        print("  - repetition_penalty: 1.2")
        print("  - min_p: 0.00")
        print("  - top_p: 0.95")
        print("  - temperature: 0.8")
        print("  - exaggeration: 0.0")
        print("  - cfg_weight: 0.0")
        print("  - top_k: 1000")
        print("  - norm_loudness: True")
        
        # Call generate with basic parameters
        wav = model.generate(
            text=test_text,
            repetition_penalty=1.2,
            min_p=0.00,
            top_p=0.95,
            audio_prompt_path=audio_prompt_path,
            exaggeration=0.0,
            cfg_weight=0.0,
            temperature=0.8,
            top_k=1000,
            norm_loudness=True,
        )
        
        print(f"\n✓ Generation successful!")
        print(f"Output shape: {wav.shape}")
        print(f"Output dtype: {wav.dtype}")
        
    except Exception as e:
        print("\n" + "=" * 80)
        print("ERROR OCCURRED:")
        print("=" * 80)
        print(f"\nError type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        print("\nFull traceback:")
        print("-" * 80)
        traceback.print_exc()
        print("-" * 80)
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = test_chatterbox_turbo()
    sys.exit(exit_code)
