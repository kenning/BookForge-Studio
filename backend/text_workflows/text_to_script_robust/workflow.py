"""
Robust Text-to-Script Workflow using Ollama with Paris-style windowing strategy.

This workflow processes fiction text and outputs a CSV with Text,Speaker columns.
Uses a multi-step approach with validation and error correction.
"""

import datetime
import json
import re
import csv
import asyncio
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import difflib
from backend.core.data_types.script_and_text_types import Script
from backend.core.utils.file_utils import save_generic_json_file
from langchain_ollama import ChatOllama
from langchain.schema import HumanMessage, SystemMessage
from backend.text_workflows.csv_to_psss import csv_content_to_script
from backend.text_workflows.websocket_utils import send_text_workflow_progress
from backend.core.config import SCRIPTS_DIR
import os

# Configuration
# Trying a much higher window. Previously 1024.
WINDOW_SIZE_WORDS = 2048
STRIDE_WORDS = WINDOW_SIZE_WORDS // 4
# Character identification windowing (separate from speaker attribution)
CHARACTER_WINDOW_SIZE_WORDS = 2048
CHARACTER_STRIDE_WORDS = 1024
MAX_RETRIES = 5
DIALOGUE_SEPARATOR = "|SEP|"


async def log_progress(
    message: str,
    level: str = "INFO",
    step_num: int = 0,
    est_total_steps: int = None,
    workflow_name: str = "text_to_script_via_ollama",
    execution_id: Optional[str] = None,
):
    """Generic logging function with websocket support."""
    print(f"[{step_num}/{est_total_steps}] [{level}] {message}")

    # Send websocket progress update via callback if provided
    try:
        await send_text_workflow_progress(
            step_num=step_num or 0,
            total_steps=est_total_steps or 1,
            message=f"[{level}] {message}",
            workflow_name=workflow_name,
            execution_id=execution_id,
        )
    except Exception as e:
        # Don't let websocket errors break the workflow
        print(f"Warning: Failed to send websocket progress: {e}")


def load_prompt_template(filename: str) -> str:
    """Load a prompt template from file."""
    prompt_path = Path(__file__).parent / filename
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read().strip()


def clean_text_for_comparison(text: str) -> str:
    """Remove separator tokens for text comparison."""
    return text.replace(DIALOGUE_SEPARATOR, "")


def calculate_text_similarity(
    text1: str, text2: str, just_letters: bool = False
) -> float:
    """Calculate similarity percentage between two texts."""
    text1_clean = clean_text_for_comparison(text1.strip()).replace(
        DIALOGUE_SEPARATOR, ""
    )
    text2_clean = clean_text_for_comparison(text2.strip()).replace(
        DIALOGUE_SEPARATOR, ""
    )

    if just_letters:
        text1_clean = "".join(c for c in text1_clean if c.isalpha())
        text2_clean = "".join(c for c in text2_clean if c.isalpha())

    # Use difflib to calculate similarity
    similarity = difflib.SequenceMatcher(None, text1_clean, text2_clean).ratio()
    return similarity * 100


async def validate_text_integrity(
    original: str,
    processed: str,
    min_similarity: float = 98.0,
) -> bool:
    """Validate that processed text matches original with minimum similarity."""
    similarity = calculate_text_similarity(original, processed)
    await log_progress(f"Text similarity: {similarity:.2f}%")

    if similarity < min_similarity:
        await log_progress(
            f"WARNING: Text similarity {similarity:.2f}% below threshold {min_similarity}%"
            + "\n"
            + "original: "
            + original[:100]
            + "\n"
            + "processed: "
            + processed[:100],
            "WARNING",
        )
        return False
    return True


def split_into_word_windows(
    text: str, window_size: int, stride: int
) -> List[Tuple[str, int, int]]:
    """Split text into overlapping word-based windows."""
    words = text.split()
    windows = []

    start_idx = 0
    while start_idx < len(words):
        end_idx = min(start_idx + window_size, len(words))
        window_text = " ".join(words[start_idx:end_idx])
        windows.append((window_text, start_idx, end_idx))

        if end_idx >= len(words):
            break
        start_idx += stride

    return windows


def annotate_dialogue_with_ids(text_with_separators: str) -> Tuple[str, Dict[int, str]]:
    """Convert separated text to ID-annotated format for processing.
    Only dialogue segments get quote IDs, narrative segments remain unmarked."""
    segments = text_with_separators.split(DIALOGUE_SEPARATOR)
    annotated_parts = []
    dialogue_map = {}
    quote_id = 1

    for segment in segments:
        segment = segment.strip()
        if not segment:
            continue

        # Check if this looks like dialogue (contains quotes)
        if '"' in segment or "”" in segment or "“" in segment:
            # This is dialogue - assign quote ID
            dialogue_map[quote_id] = segment
            annotated_parts.append(f"|{quote_id}|{segment}|{quote_id}|")
            quote_id += 1
        else:
            # This is narrative text - no quote ID, just add as-is
            annotated_parts.append(segment)

    return " ".join(annotated_parts), dialogue_map


def extract_quotes_from_window(window_text: str) -> List[int]:
    """Extract quote IDs present in a window."""
    quote_pattern = re.compile(r"\|(\d+)\|")
    return [int(match.group(1)) for match in quote_pattern.finditer(window_text)]


class RobustTextToScriptWorkflow:
    def __init__(
        self,
        ollama_url: str = "http://127.0.0.1:11434",
        model_name: str = None,
        execution_id: Optional[str] = None,
    ):
        if not ollama_url:
            ollama_url = "http://127.0.0.1:11434"

        self.ollama_url = ollama_url
        self.model_name = model_name
        self.execution_id = execution_id
        self.llm = None
        self.character_list = []  # Never include Narrator
        self.running_predictions = {}
        self.previous_response_content = (
            None  # Store raw JSON string like Paris approach
        )

    async def _log_progress(
        self,
        message: str,
        level: str = "INFO",
        step_num: int = 0,
        est_total_steps: int = None,
    ):
        """Helper method to call log_progress with this workflow's execution_id."""
        await log_progress(
            message,
            level,
            step_num,
            est_total_steps,
            workflow_name="text_to_script_via_ollama",
            execution_id=self.execution_id,
        )

    async def _init_llm(self):
        """Initialize the Ollama LLM connection."""
        if self.llm is None:
            try:
                if not self.model_name:
                    # Auto-detect available model
                    import requests

                    response = requests.get(f"{self.ollama_url}/v1/models")
                    response.raise_for_status()
                    self.model_name = response.json()["data"][0]["id"]
                    await self._log_progress(f"Auto-detected model: {self.model_name}")

                self.llm = ChatOllama(
                    base_url=self.ollama_url,
                    model=self.model_name,
                    temperature=0.3,
                    num_predict=4800,  # Output limit for separator tokens
                    keep_alive=-1,  # Keep model loaded indefinitely
                )
                await self._log_progress(
                    f"Initialized Ollama LLM with model: {self.model_name}"
                )
            except Exception as e:
                await self._log_progress(f"Failed to initialize LLM: {str(e)}", "ERROR")
                raise

    async def step2_separate_dialogue(self, text: str, est_total_steps: int) -> str:
        """Step 2: Separate dialogue and narrative with regex-based approach."""
        await self._log_progress(
            "Step 2: Separating dialogue and narrative using regex patterns",
            step_num=2,
            est_total_steps=est_total_steps,
        )

        # Apply regex patterns to insert separators
        result = text

        # 1. Non-directional quote preceded by space: " -> |SEP|"
        result = re.sub(r' "', f' {DIALOGUE_SEPARATOR}"', result)
        result = re.sub(r'\n"', f'\n{DIALOGUE_SEPARATOR}"', result)

        # 2. Non-directional quote followed by space: " -> "|SEP|
        result = re.sub(r'" ', f'"{DIALOGUE_SEPARATOR} ', result)
        result = re.sub(r'"\n', f'"{DIALOGUE_SEPARATOR}\n', result)
        result = re.sub(r'",', f'"{DIALOGUE_SEPARATOR},', result)
        result = re.sub(r'"\.', f'"{DIALOGUE_SEPARATOR}.', result)
        result = re.sub(r'"\?', f'"{DIALOGUE_SEPARATOR}?', result)

        if result[0] == '"':
            result = DIALOGUE_SEPARATOR + result
        if result[-1] == '"':
            result = result + DIALOGUE_SEPARATOR

        # 3. Directional end quote: " -> "|SEP|
        result = re.sub(r"”", f"”{DIALOGUE_SEPARATOR}", result)

        # 4. Directional start quote: " -> |SEP|"
        result = re.sub(r"“", f"{DIALOGUE_SEPARATOR}“", result)

        await self._log_progress(
            f"Regex separation completed. Added {result.count(DIALOGUE_SEPARATOR)} separator tokens",
            step_num=2,
            est_total_steps=est_total_steps,
        )
        return result

    async def step1_identify_characters(
        self, text: str, est_total_steps: int
    ) -> List[str]:
        """Step 1: Identify all speaking characters in the text using sliding windows."""
        await self._log_progress(
            "Step 1: Identifying characters in text using windowing",
            step_num=1,
            est_total_steps=est_total_steps,
        )

        await self._init_llm()
        prompt_template = load_prompt_template(
            "step1_character_identification_prompt.txt"
        )

        # Split text into windows
        words = text.split()
        word_count = len(words)

        # Calculate number of windows using the provided formula
        import math

        total_windows = (
            max(
                1,
                math.ceil(
                    (word_count - CHARACTER_WINDOW_SIZE_WORDS) / CHARACTER_STRIDE_WORDS
                )
                + 1,
            )
            if word_count > CHARACTER_WINDOW_SIZE_WORDS
            else 1
        )

        await self._log_progress(
            f"Processing {total_windows} windows for character identification",
            step_num=1,
            est_total_steps=est_total_steps,
        )

        # Process each window
        start_idx = 0
        window_num = 0

        while start_idx < word_count:
            window_num += 1
            end_idx = min(start_idx + CHARACTER_WINDOW_SIZE_WORDS, word_count)
            window_text = " ".join(words[start_idx:end_idx])

            await self._log_progress(
                f"Processing character window {window_num}/{total_windows} (words {start_idx}-{end_idx})",
                step_num=1,
                est_total_steps=est_total_steps,
            )

            # Format existing characters for prompt
            existing_chars_str = (
                ", ".join(self.character_list) if self.character_list else "None"
            )

            prompt = prompt_template.format(
                existing_characters=existing_chars_str, text=window_text
            )
            print(prompt)

            for attempt in range(MAX_RETRIES):
                try:
                    messages = [HumanMessage(content=prompt)]
                    response = self.llm.invoke(messages)

                    # Clean JSON response
                    cleaned_response = response.content.strip()
                    cleaned_response = cleaned_response.replace("```json", "").replace(
                        "```", ""
                    )
                    cleaned_response = cleaned_response.strip()

                    response_data = json.loads(cleaned_response)
                    new_characters = response_data.get("new_characters", [])

                    # Add new characters to our list
                    added_count = 0
                    for char in new_characters:
                        if char not in self.character_list:
                            self.character_list.append(char)
                            added_count += 1

                    await self._log_progress(
                        f"Window {window_num}/{total_windows}: Found {len(new_characters)} characters, added {added_count} new",
                        step_num=1,
                        est_total_steps=est_total_steps,
                    )
                    break

                except (json.JSONDecodeError, KeyError) as e:
                    await self._log_progress(
                        f"Window {window_num}, attempt {attempt + 1} failed: {str(e)}",
                        "WARNING",
                    )
                    if attempt == MAX_RETRIES - 1:
                        await self._log_progress(
                            f"Window {window_num} failed after all retries, skipping",
                            "WARNING",
                        )
                except Exception as e:
                    await self._log_progress(
                        f"Window {window_num}, attempt {attempt + 1} error: {str(e)}",
                        "WARNING",
                    )
                    if attempt == MAX_RETRIES - 1:
                        await self._log_progress(
                            f"Window {window_num} failed after all retries, skipping",
                            "WARNING",
                        )

            # Move to next window
            if end_idx >= word_count:
                break
            start_idx += CHARACTER_STRIDE_WORDS

        await self._log_progress(
            f"Character identification complete. Total characters found: {self.character_list}",
            step_num=1,
            est_total_steps=est_total_steps,
        )
        return self.character_list

    # Intentionally commented out - LLM-based windowed separation approach
    # def _step2_windowed_separation(self, text: str) -> str:
    #     """Process large text in chunks for dialogue separation."""
    #     await self._log_progress("Using windowed approach for Step 1")

    #     # Split text into chunks by sentences to avoid breaking mid-dialogue
    #     sentences = text.split(". ")
    #     chunks = []
    #     current_chunk = ""

    #     for sentence in sentences:
    #         # Add sentence back with period (except last one)
    #         sentence_with_period = sentence + (
    #             ". " if sentence != sentences[-1] else ""
    #         )

    #         # Check if adding this sentence would exceed chunk limit
    #         if len(current_chunk + sentence_with_period) > 2400:
    #             if current_chunk:
    #                 chunks.append(current_chunk.strip())
    #             current_chunk = sentence_with_period
    #         else:
    #             current_chunk += sentence_with_period

    #     # Add final chunk
    #     if current_chunk:
    #         chunks.append(current_chunk.strip())

    #     await self._log_progress(f"Split text into {len(chunks)} chunks")

    #     # Process each chunk
    #     separated_chunks = []
    #     prompt_template = load_prompt_template("step1_dialogue_separation_prompt.txt")

    #     for i, chunk in enumerate(chunks):
    #         await self._log_progress(f"Processing chunk {i+1}/{len(chunks)} ({len(chunk)} chars)")

    #         prompt = prompt_template.format(
    #             text=chunk, dialogue_separator=DIALOGUE_SEPARATOR
    #         )

    #         for attempt in range(MAX_RETRIES):
    #             try:
    #                 messages = [HumanMessage(content=prompt)]
    #                 await self._log_progress(f"Chunk {i+1} prompt length: {len(prompt)} chars")
    #                 await self._log_progress(f"Chunk {i+1} text preview: {chunk[:100]}...")

    #                 # Debug the actual request being sent
    #                 await self._log_progress(f"Chunk {i+1} prompt preview: {prompt[:300]}...")

    #                 response = self.llm.invoke(messages)

    #                 # More detailed response debugging
    #                 await self._log_progress(f"Chunk {i+1} response type: {type(response)}")
    #                 await self._log_progress(f"Chunk {i+1} response object: {response}")

    #                 if hasattr(response, "content"):
    #                     content = response.content
    #                     await self._log_progress(f"Chunk {i+1} content type: {type(content)}")
    #                     await self._log_progress(
    #                         f"Chunk {i+1} content length: {len(content) if content else 'None'}"
    #                     )
    #                     await self._log_progress(
    #                         f"Chunk {i+1} raw content: '{content[:200] if content else 'None'}'"
    #                     )

    #                     separated_chunk = content.strip() if content else ""

    #                     if separated_chunk:
    #                         separated_chunks.append(separated_chunk)
    #                         break
    #                     else:
    #                         await self._log_progress(
    #                             f"Empty response for chunk {i+1}, attempt {attempt+1}"
    #                         )
    #                 else:
    #                     await self._log_progress(f"Response object has no 'content' attribute")

    #             except Exception as e:
    #                 await self._log_progress(
    #                     f"Chunk {i+1}, attempt {attempt+1} failed: {str(e)}", "WARNING"
    #                 )
    #                 await self._log_progress(f"Exception type: {type(e)}")
    #                 import traceback

    #                 await self._log_progress(f"Full traceback: {traceback.format_exc()}")

    #         # If all attempts failed, skip this chunk for now
    #         if i >= len(separated_chunks):
    #             await self._log_progress(f"All attempts failed for chunk {i+1}, skipping", "ERROR")

    #     # Rejoin the chunks
    #     result = " ".join(separated_chunks)
    #     await self._log_progress("Step 1 windowed processing completed")
    #     return result

    async def step3_validate_text(
        self, original: str, processed: str, est_total_steps: int
    ) -> bool:
        """Step 3: Validate text integrity."""
        await self._log_progress(
            "Step 3: Validating text integrity",
            step_num=3,
            est_total_steps=est_total_steps,
        )
        return await validate_text_integrity(original, processed)

    async def step4_attribute_speakers(
        self, annotated_text: str, dialogue_map: Dict[int, str], est_total_steps: int
    ) -> Dict[int, str]:
        step_counter = 4

        """Step 4: Use Paris-style windowing to attribute speakers."""
        await self._log_progress(
            "Step 4: Starting speaker attribution with windowing strategy",
            step_num=step_counter,
            est_total_steps=est_total_steps,
        )

        windows = split_into_word_windows(
            annotated_text, WINDOW_SIZE_WORDS, STRIDE_WORDS
        )
        await self._log_progress(f"Created {len(windows)} overlapping windows")

        prompt_template = load_prompt_template("step3_speaker_attribution_prompt.txt")

        for i, (window_text, start_idx, end_idx) in enumerate(windows):
            await self._log_progress(
                f"Processing window {i + 1}/{len(windows)}",
                step_num=step_counter + i,
                est_total_steps=est_total_steps,
            )

            quote_ids_in_window = extract_quotes_from_window(window_text)
            if not quote_ids_in_window:
                await self._log_progress(
                    f"No quotes found in window {i + 1}, skipping",
                    step_num=step_counter + i,
                    est_total_steps=est_total_steps,
                )
                continue

            # Prepare context - Paris-style overlapping approach
            character_list_str = (
                ", ".join(self.character_list)
                if self.character_list
                else "No characters identified"
            )

            # Find overlapping predictions from previous window (Paris approach)
            overlapping_predictions = {}
            if self.previous_response_content:
                try:
                    parsed_previous_response = json.loads(
                        self.previous_response_content
                    )
                    for qid_str, speaker in parsed_previous_response.items():
                        try:
                            qid = int(
                                qid_str
                            )  # Convert string key to int for comparison
                            if (
                                qid in quote_ids_in_window
                            ):  # Check if this quote ID is also in current window
                                overlapping_predictions[qid_str] = (
                                    speaker  # Keep as string key for JSON
                                )
                        except ValueError:
                            pass  # Skip non-integer QIDs from previous response
                except json.JSONDecodeError:
                    await self._log_progress(
                        f"Warning: Could not decode previous response for overlap analysis: {self.previous_response_content[:100]}...",
                        "WARNING",
                    )

            previous_context = (
                json.dumps(overlapping_predictions)
                if overlapping_predictions
                else "None"
            )

            prompt = prompt_template.format(
                character_list=character_list_str,
                previous_predictions=previous_context,
                text_window=window_text,
                # quote_ids=", ".join(map(str, quote_ids_in_window)),
                min_quote_id=min(quote_ids_in_window),
                max_quote_id=max(quote_ids_in_window),
            )

            print(prompt)

            # print("--------------------------------")
            # print(f"WINDOW PROMPT")
            # print(prompt)
            # print("--------------------------------")

            # Try to get valid response
            for attempt in range(MAX_RETRIES):
                try:
                    system_prompt = load_prompt_template(
                        "step3_speaker_attribution_system.txt"
                    )
                    messages = [
                        SystemMessage(content=system_prompt),
                        HumanMessage(content=prompt),
                    ]
                    response = self.llm.invoke(messages)
                    await self._log_progress(
                        f"Raw LLM response: {response.content[:200]}..."
                    )

                    # Clean JSON response - remove markdown code blocks
                    cleaned_response = response.content.strip()
                    cleaned_response = cleaned_response.replace("```json", "").replace(
                        "```", ""
                    )
                    cleaned_response = cleaned_response.strip()

                    response_data = json.loads(cleaned_response)

                    # Update predictions
                    predictions = response_data.get("predictions", {})
                    for qid_str, speaker in predictions.items():
                        # This will often error out -- we want it to error out
                        qid = int(qid_str)
                        if qid in dialogue_map:
                            self.running_predictions[qid] = speaker

                    # Store raw JSON content for next window's overlap analysis (Paris approach)
                    self.previous_response_content = json.dumps(predictions)
                    await self._log_progress(
                        f"Window {i + 1} processed successfully, found {len(predictions)} speakers",
                        step_num=step_counter + i,
                        est_total_steps=est_total_steps,
                    )
                    break

                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    await self._log_progress(
                        f"Window {i + 1}, attempt {attempt + 1} failed: {str(e)}",
                        "WARNING",
                        step_num=step_counter + i,
                        est_total_steps=est_total_steps,
                    )
                    if attempt == MAX_RETRIES - 1:
                        await self._log_progress(
                            f"Window {i + 1} failed after all retries, skipping",
                            "ERROR",
                            step_num=step_counter + i,
                            est_total_steps=est_total_steps,
                        )

        await self._log_progress(
            f"Step 4 completed. Total predictions: {len(self.running_predictions)}",
            step_num=step_counter + len(windows) - 1,
            est_total_steps=est_total_steps,
        )
        await self._log_progress(
            f"Discovered characters: {', '.join(self.character_list)}",
            step_num=step_counter + len(windows) - 1,
            est_total_steps=est_total_steps,
        )
        return self.running_predictions

    async def step5_generate_csv(
        self,
        dialogue_map: Dict[int, str],
        speaker_predictions: Dict[int, str],
        separated_text: str,
        est_total_steps: int,
        curr_step: int,
    ) -> str:
        """Step 5: Generate CSV output."""
        await self._log_progress(
            "Step 5: Generating CSV output",
            step_num=curr_step,
            est_total_steps=est_total_steps,
        )

        # Reconstruct the text with speakers
        csv_rows = []

        # Split the separated text back into segments
        # Now dialogue_map only contains actual dialogue, so we need to process the separated text directly
        segments = separated_text.split(DIALOGUE_SEPARATOR)

        dialogue_id = 1
        for segment in segments:
            segment = segment.strip()
            if not segment:
                continue

            # Check if this segment contains quote characters (dialogue)
            if '"' in segment or "”" in segment or "“" in segment:
                # This is dialogue - use LLM prediction
                speaker = speaker_predictions.get(dialogue_id, "Unknown")
                csv_rows.append([segment, speaker])
                dialogue_id += 1
            else:
                # This is narrative text - assign to Narrator
                csv_rows.append([segment, "Narrator"])

        # Convert to CSV string
        output = "Text,Speaker\n"
        for text, speaker in csv_rows:
            # Escape quotes in CSV
            text_escaped = text.replace('"', '""')
            speaker_escaped = speaker.replace('"', '""')
            output += f'"{text_escaped}","{speaker_escaped}"\n'

        await self._log_progress(
            f"Generated CSV with {len(csv_rows)} rows",
            step_num=curr_step,
            est_total_steps=est_total_steps,
        )
        return output

    async def step6_final_validation(
        self,
        original_text: str,
        csv_content: str,
        est_total_steps: int,
        curr_step: int,
        min_similarity: float = 98.0,
    ) -> bool:
        """Step 6: Final validation of CSV content."""
        await self._log_progress(
            "Step 6: Final validation",
            step_num=curr_step,
            est_total_steps=est_total_steps,
        )

        # Extract text from CSV for comparison using pandas
        import pandas as pd
        from io import StringIO

        df = pd.read_csv(StringIO(csv_content))
        csv_text_parts = df["Text"].tolist()
        reconstructed_text = " ".join(csv_text_parts)

        similarity = calculate_text_similarity(
            original_text, reconstructed_text, just_letters=True
        )

        if similarity >= min_similarity:
            await self._log_progress(
                f"Final validation passed: {similarity:.2f}% similarity",
                step_num=curr_step,
                est_total_steps=est_total_steps,
            )
            return True
        else:
            await self._log_progress(
                f"Final validation failed: {similarity:.2f}% similarity (required: {min_similarity}%)",
                "ERROR",
                step_num=curr_step,
                est_total_steps=est_total_steps,
            )
            return False

    async def process(self, text: str, output_file: Optional[str] = None) -> Script:
        """Main workflow processing function."""
        await self._log_progress("Starting robust text-to-script workflow")

        try:
            # Pre-run split into word windows just to estimate num steps
            est_num_windows = len(
                split_into_word_windows(text, WINDOW_SIZE_WORDS, STRIDE_WORDS)
            )
            est_total_steps = 3 + est_num_windows + 2 + 1  # Add 1 more just in case...

            # Step 1: Identify characters
            await self.step1_identify_characters(text, est_total_steps)

            # Step 2: Separate dialogue
            separated_text = await self.step2_separate_dialogue(text, est_total_steps)

            # print("--------------------------------")
            # print("SEPARATED TEXT")
            # print(separated_text[:1000])
            # print("--------------------------------")

            # Step 3: Validate text integrity
            if not await self.step3_validate_text(
                text, separated_text, est_total_steps
            ):
                raise ValueError("Text validation failed in step 3")

            # Prepare for windowing
            annotated_text, dialogue_map = annotate_dialogue_with_ids(separated_text)
            await self._log_progress(
                f"Prepared {len(dialogue_map)} dialogue segments for processing",
                step_num=3,
                est_total_steps=est_total_steps,
            )

            # print(annotated_text)

            # Step 4: Speaker attribution
            speaker_predictions = await self.step4_attribute_speakers(
                annotated_text, dialogue_map, est_total_steps
            )

            # Step 5: Generate CSV
            csv_content = await self.step5_generate_csv(
                dialogue_map,
                speaker_predictions,
                separated_text,
                est_total_steps,
                curr_step=5 + est_num_windows,
            )

            # Step 6: Final validation
            if not await self.step6_final_validation(
                text, csv_content, est_total_steps, curr_step=est_total_steps - 1
            ):
                await self._log_progress(
                    "Warning: Final validation failed, but proceeding with output",
                    "WARNING",
                    step_num=est_total_steps - 1,
                    est_total_steps=est_total_steps,
                )

            script = csv_content_to_script(csv_content)

            # Save output anyway to avoid losing it
            # if output_file:
            try:
                os.makedirs(SCRIPTS_DIR / "temp", exist_ok=True)
                filename = (
                    f"script_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                )
                save_generic_json_file(
                    directory_type="scripts",
                    subdirectory="temp",
                    filename=filename,
                    data=script.model_dump(mode="json"),
                )
                await self._log_progress(
                    f"Output saved to {SCRIPTS_DIR / 'temp' / filename}",
                    step_num=est_total_steps,
                    est_total_steps=est_total_steps,
                )
            except Exception as e:
                await self._log_progress(
                    f"Error saving output: {str(e)}",
                    "ERROR",
                    step_num=est_total_steps,
                    est_total_steps=est_total_steps,
                )

            await self._log_progress("Workflow completed successfully")
            return script

        except Exception as e:
            await self._log_progress(f"Workflow failed: {str(e)}", "ERROR")
            raise


def main():
    """Main function for standalone execution."""
    # Example usage

    with open("gg.txt", "r", encoding="utf-8") as f:
        sample_text = f.read()

    # sample_text = """
    # "Hello, my dear friend," said Alice, stepping into the garden.
    # The roses were blooming beautifully in the morning sun.
    # "Good morning, Alice," replied the Gardener, tipping his hat. "How lovely to see you today."
    # Alice smiled warmly and walked closer to examine the flowers.
    # "These roses are absolutely magnificent," she exclaimed. "How do you keep them so healthy?"
    # The old man chuckled and pointed to his watering can.
    # """

    workflow = RobustTextToScriptWorkflow()
    result = workflow.process(sample_text, output_file="sample_output.csv")
    print("\nGenerated CSV:")
    print(result)


if __name__ == "__main__":
    main()
