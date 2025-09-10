"""
Sentence chunking utility for splitting long annotated text into manageable chunks.

This module provides functionality to split text while preserving speaker information
and ensuring sentences are not broken in the middle of chunks.
"""

import re
from typing import List, Dict, Any


def split_into_sentences(text: str) -> List[str]:
    """
    Split text into sentences using basic sentence boundary detection.

    Args:
        text: The input text to split

    Returns:
        List of sentences
    """
    # Basic sentence splitting on periods, exclamation marks, and question marks
    # followed by whitespace or end of string
    sentences = re.split(r"[.!?]+(?:\s+|$)", text.strip())

    # Filter out empty sentences and add back punctuation
    result = []
    for i, sentence in enumerate(sentences):
        sentence = sentence.strip()
        if sentence:
            # Find the original punctuation by looking at what comes after this sentence
            original_pos = text.find(sentence)
            if original_pos != -1:
                end_pos = original_pos + len(sentence)
                # Look for punctuation after the sentence
                punctuation = ""
                while end_pos < len(text) and text[end_pos] in ".!?":
                    punctuation += text[end_pos]
                    end_pos += 1

                if punctuation:
                    sentence += punctuation

            result.append(sentence)

    return result


def count_words(text: str) -> int:
    """
    Count words in a text string.

    Args:
        text: The input text

    Returns:
        Number of words
    """
    return len(text.split())


def chunk_sentences(
    texts: List[str],
    voice_clones: List[str],
    voice_transcriptions: List[str],
    approximate_min_chunk_length: int,
) -> List[Dict[str, Any]]:
    """
    Chunk annotated text into manageable pieces while preserving speaker information.

    Args:
        texts: List of text strings (each may contain multiple sentences)
        voice_clones: List of voice clone file paths corresponding to each text
        voice_transcriptions: List of transcription strings corresponding to each text
        approximate_min_chunk_length: Minimum word count per chunk

    Returns:
        List of chunk dictionaries, each containing texts, voice_clones, and voice_transcriptions
    """
    if len(texts) != len(voice_clones) or len(texts) != len(voice_transcriptions):
        raise ValueError("All input lists must have the same length")

    if not texts:
        return []

    # Step 1: Create mini-chunks (one per sentence)
    mini_chunks = []

    for i, text in enumerate(texts):
        sentences = split_into_sentences(text)
        for sentence in sentences:
            mini_chunks.append(
                {
                    "text": sentence,
                    "voice_clone": voice_clones[i],
                    "voice_transcription": voice_transcriptions[i],
                }
            )

    if not mini_chunks:
        return []

    # Step 2: Combine mini-chunks into normal-sized chunks
    chunks = []
    current_chunk = {"texts": [], "voice_clones": [], "voice_transcriptions": []}
    current_word_count = 0
    current_speaker_info = None

    for mini_chunk in mini_chunks:
        sentence = mini_chunk["text"]
        voice_clone = mini_chunk["voice_clone"]
        voice_transcription = mini_chunk["voice_transcription"]
        sentence_word_count = count_words(sentence)

        speaker_info = (voice_clone, voice_transcription)

        # Check if this sentence alone exceeds the minimum chunk length
        if sentence_word_count >= approximate_min_chunk_length:
            # End current chunk if it has content
            if current_chunk["texts"]:
                chunks.append(current_chunk)
                current_chunk = {
                    "texts": [],
                    "voice_clones": [],
                    "voice_transcriptions": [],
                }
                current_word_count = 0
                current_speaker_info = None

            # Create a chunk just for this sentence
            chunks.append(
                {
                    "texts": [sentence],
                    "voice_clones": [voice_clone],
                    "voice_transcriptions": [voice_transcription],
                }
            )
            continue

        # Check if adding this sentence would exceed the limit
        if (
            current_word_count + sentence_word_count >= approximate_min_chunk_length
            and current_chunk["texts"]
        ):
            # Same speaker - combine into existing text entry
            if speaker_info == current_speaker_info:
                current_chunk["texts"][-1] += " " + sentence
            else:
                # Different speaker - add as new entry
                current_chunk["texts"].append(sentence)
                current_chunk["voice_clones"].append(voice_clone)
                current_chunk["voice_transcriptions"].append(voice_transcription)

            # End this chunk
            chunks.append(current_chunk)
            current_chunk = {
                "texts": [],
                "voice_clones": [],
                "voice_transcriptions": [],
            }
            current_word_count = 0
            current_speaker_info = None
            continue

        # Add sentence to current chunk
        if speaker_info == current_speaker_info and current_chunk["texts"]:
            # Same speaker - combine with previous text
            current_chunk["texts"][-1] += " " + sentence
            current_word_count += sentence_word_count
        else:
            # Different speaker or first sentence - add as new entry
            current_chunk["texts"].append(sentence)
            current_chunk["voice_clones"].append(voice_clone)
            current_chunk["voice_transcriptions"].append(voice_transcription)
            current_word_count += sentence_word_count
            current_speaker_info = speaker_info

    # Add any remaining content as a final chunk
    if current_chunk["texts"]:
        chunks.append(current_chunk)

    return chunks
