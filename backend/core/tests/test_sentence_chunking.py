"""
Test sentence chunking functionality
"""

import os
import sys
import pytest
from pathlib import Path

# Add the backend directory to the path so we can import modules
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from backend.core.utils.sentence_chunking import (
    chunk_sentences,
    split_into_sentences,
    count_words,
)


class TestSentenceChunking:
    """Test class for sentence chunking functionality"""

    def test_split_into_sentences(self):
        """Test basic sentence splitting functionality"""
        text = "Hey! Hi. Listen, are you okay?"
        sentences = split_into_sentences(text)
        expected = ["Hey!", "Hi.", "Listen, are you okay?"]
        assert sentences == expected

    def test_count_words(self):
        """Test word counting functionality"""
        assert count_words("Hey!") == 1
        assert count_words("Listen, are you okay?") == 4
        assert count_words("") == 0
        assert count_words("   ") == 0

    def test_empty_inputs(self):
        """Test handling of empty inputs"""
        result = chunk_sentences([], [], [], approximate_min_chunk_length=20)
        assert result == []

    def test_mismatched_input_lengths(self):
        """Test error handling for mismatched input lengths"""
        with pytest.raises(ValueError):
            chunk_sentences(
                ["text"], [], ["transcription"], approximate_min_chunk_length=20
            )

    def test_example_chunking(self):
        """Test the main example from the specification"""
        texts = [
            "Hey!",
            "Hi.",
            "Listen, are you okay?",
            "Things have been hard. For instance, blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah, blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah. blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah blah.",
            "Wow! That's a lot!",
            "Yeah, I know.",
            "Wow! Crazy!",
            "Yes, it is. It's really crazy. You know? I can't stop thinking about it.",
        ]

        voice_clones = [
            "Patricia.wav",
            "Fred.wav",
            "Patricia.wav",
            "Fred.wav",
            "Patricia.wav",
            "Fred.wav",
            "Patricia.wav",
            "Fred.wav",
        ]

        voice_transcriptions = [
            "<Patricia voice transcription text>",
            "<Fred voice transcription text>",
            "<Patricia voice transcription text>",
            "<Fred voice transcription text>",
            "<Patricia voice transcription text>",
            "<Fred voice transcription text>",
            "<Patricia voice transcription text>",
            "<Fred voice transcription text>",
        ]

        result = chunk_sentences(
            texts, voice_clones, voice_transcriptions, approximate_min_chunk_length=20
        )

        # Should have 4 chunks as per the example
        assert len(result) == 4

        # Check first chunk
        chunk1 = result[0]
        assert len(chunk1["texts"]) == 4
        assert chunk1["texts"][0] == "Hey!"
        assert chunk1["texts"][1] == "Hi."
        assert chunk1["texts"][2] == "Listen, are you okay?"
        assert chunk1["texts"][3] == "Things have been hard."
        assert chunk1["voice_clones"] == [
            "Patricia.wav",
            "Fred.wav",
            "Patricia.wav",
            "Fred.wav",
        ]
        assert chunk1["voice_transcriptions"] == [
            "<Patricia voice transcription text>",
            "<Fred voice transcription text>",
            "<Patricia voice transcription text>",
            "<Fred voice transcription text>",
        ]

        # Check second chunk (long sentence chunk)
        chunk2 = result[1]
        assert len(chunk2["texts"]) == 1
        assert chunk2["texts"][0].startswith("For instance, blah blah blah")
        assert chunk2["texts"][0].endswith("blah blah blah blah blah.")
        assert chunk2["voice_clones"] == ["Fred.wav"]
        assert chunk2["voice_transcriptions"] == ["<Fred voice transcription text>"]

        # Check third chunk
        chunk3 = result[2]
        assert len(chunk3["texts"]) == 2
        assert chunk3["texts"][0].startswith("blah blah blah")
        assert chunk3["texts"][1] == "Wow! That's a lot!"
        assert chunk3["voice_clones"] == ["Fred.wav", "Patricia.wav"]
        assert chunk3["voice_transcriptions"] == [
            "<Fred voice transcription text>",
            "<Patricia voice transcription text>",
        ]

        # Check fourth chunk
        chunk4 = result[3]
        assert len(chunk4["texts"]) == 3
        assert chunk4["texts"][0] == "Yeah, I know."
        assert chunk4["texts"][1] == "Wow! Crazy!"
        assert (
            chunk4["texts"][2]
            == "Yes, it is. It's really crazy. You know? I can't stop thinking about it."
        )
        assert chunk4["voice_clones"] == ["Fred.wav", "Patricia.wav", "Fred.wav"]
        assert chunk4["voice_transcriptions"] == [
            "<Fred voice transcription text>",
            "<Patricia voice transcription text>",
            "<Fred voice transcription text>",
        ]

    def test_same_speaker_combining(self):
        """Test that consecutive texts from the same speaker are combined properly"""
        texts = [
            "First sentence.",
            "Second sentence.",
            "Third sentence.",
        ]

        voice_clones = [
            "Speaker1.wav",
            "Speaker1.wav",
            "Speaker1.wav",
        ]

        voice_transcriptions = [
            "Speaker1 transcription",
            "Speaker1 transcription",
            "Speaker1 transcription",
        ]

        result = chunk_sentences(
            texts, voice_clones, voice_transcriptions, approximate_min_chunk_length=5
        )

        # Should combine all into one chunk with one combined text
        assert len(result) == 1
        chunk = result[0]
        assert len(chunk["texts"]) == 1
        assert chunk["texts"][0] == "First sentence. Second sentence. Third sentence."
        assert chunk["voice_clones"] == ["Speaker1.wav"]
        assert chunk["voice_transcriptions"] == ["Speaker1 transcription"]

    def test_long_single_sentence(self):
        """Test handling of a single very long sentence"""
        long_sentence = " ".join(["word"] * 30) + "."  # 30-word sentence

        texts = [
            "Short sentence.",
            long_sentence,
            "Another short.",
        ]

        voice_clones = ["A.wav", "B.wav", "C.wav"]
        voice_transcriptions = ["A trans", "B trans", "C trans"]

        result = chunk_sentences(
            texts, voice_clones, voice_transcriptions, approximate_min_chunk_length=20
        )

        # Should have 3 chunks: first short, long sentence alone, last short
        assert len(result) == 3

        # First chunk
        assert result[0]["texts"] == ["Short sentence."]

        # Second chunk (long sentence alone)
        assert len(result[1]["texts"]) == 1
        assert result[1]["texts"][0] == long_sentence
        assert result[1]["voice_clones"] == ["B.wav"]

        # Third chunk
        assert result[2]["texts"] == ["Another short."]

    def test_multiple_sentences_in_one_text(self):
        """Test handling of multiple sentences within a single text input"""
        texts = [
            "Hello there! How are you? I'm doing well.",
        ]

        voice_clones = ["Speaker.wav"]
        voice_transcriptions = ["Speaker transcription"]

        result = chunk_sentences(
            texts, voice_clones, voice_transcriptions, approximate_min_chunk_length=5
        )

        # The algorithm splits sentences and creates chunks based on word count
        # "Hello there! How are you?" = 5 words (meets min chunk length)
        # "I'm doing well." = 3 words (goes into next chunk)
        assert len(result) == 2

        # First chunk
        chunk1 = result[0]
        assert len(chunk1["texts"]) == 1
        assert chunk1["texts"][0] == "Hello there! How are you?"
        assert chunk1["voice_clones"] == ["Speaker.wav"]
        assert chunk1["voice_transcriptions"] == ["Speaker transcription"]

        # Second chunk
        chunk2 = result[1]
        assert len(chunk2["texts"]) == 1
        assert chunk2["texts"][0] == "I'm doing well."
        assert chunk2["voice_clones"] == ["Speaker.wav"]
        assert chunk2["voice_transcriptions"] == ["Speaker transcription"]

    def test_zero_min_chunk_length(self):
        """Test that when the min chunk length is 0, all sentences are separate chunks"""
        texts = [
            "Hey. Hey you. Hey.",
        ]

        voice_clones = [
            "Speaker1.wav",
        ]

        voice_transcriptions = [
            "Speaker1 transcription",
        ]

        result = chunk_sentences(
            texts, voice_clones, voice_transcriptions, approximate_min_chunk_length=0
        )

        # Should have 3 chunks, one for each sentence
        assert len(result) == 3
        assert result[0]["texts"] == ["Hey."]
        assert result[0]["voice_clones"] == ["Speaker1.wav"]
        assert result[0]["voice_transcriptions"] == ["Speaker1 transcription"]
        assert result[1]["texts"] == ["Hey you."]
        assert result[1]["voice_clones"] == ["Speaker1.wav"]
        assert result[1]["voice_transcriptions"] == ["Speaker1 transcription"]
        assert result[2]["texts"] == ["Hey."]
        assert result[2]["voice_clones"] == ["Speaker1.wav"]
        assert result[2]["voice_transcriptions"] == ["Speaker1 transcription"]


if __name__ == "__main__":
    # Run tests directly if script is called
    pytest.main([__file__, "-v"])
