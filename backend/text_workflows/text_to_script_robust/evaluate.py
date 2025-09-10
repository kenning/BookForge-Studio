"""
Evaluation script for comparing workflow output against ground truth CSV.

Usage:
    python evaluate.py predicted.csv ground_truth.csv
"""

import csv
import sys
import difflib
from pathlib import Path
from typing import Dict, List, Tuple
import argparse


def normalize_speaker_name(name: str) -> str:
    """Normalize speaker names for comparison."""
    return name.strip().lower().replace("'", "").replace('"', '')


def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    return text.strip().lower()


def load_csv_data(file_path: str) -> List[Tuple[str, str]]:
    """Load CSV data as list of (text, speaker) tuples."""
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)  # Skip header
        for row in reader:
            if len(row) >= 2:
                text, speaker = row[0], row[1]
                data.append((text.strip(), speaker.strip()))
    return data


def calculate_exact_match_accuracy(predicted: List[Tuple[str, str]], 
                                 ground_truth: List[Tuple[str, str]]) -> float:
    """Calculate exact match accuracy between predicted and ground truth."""
    if len(predicted) != len(ground_truth):
        print(f"WARNING: Different number of rows - Predicted: {len(predicted)}, Ground Truth: {len(ground_truth)}")
        return 0.0
    
    correct = 0
    total = len(predicted)
    
    for i, ((pred_text, pred_speaker), (gt_text, gt_speaker)) in enumerate(zip(predicted, ground_truth)):
        text_match = normalize_text(pred_text) == normalize_text(gt_text)
        speaker_match = normalize_speaker_name(pred_speaker) == normalize_speaker_name(gt_speaker)
        
        if text_match and speaker_match:
            correct += 1
        else:
            print(f"Row {i+1} mismatch:")
            if not text_match:
                print(f"  Text: '{pred_text}' != '{gt_text}'")
            if not speaker_match:
                print(f"  Speaker: '{pred_speaker}' != '{gt_speaker}'")
    
    return (correct / total) * 100 if total > 0 else 0.0


def calculate_speaker_accuracy(predicted: List[Tuple[str, str]], 
                             ground_truth: List[Tuple[str, str]]) -> float:
    """Calculate speaker-only accuracy (ignoring text differences)."""
    if len(predicted) != len(ground_truth):
        return 0.0
    
    correct = 0
    total = len(predicted)
    
    for (_, pred_speaker), (_, gt_speaker) in zip(predicted, ground_truth):
        if normalize_speaker_name(pred_speaker) == normalize_speaker_name(gt_speaker):
            correct += 1
    
    return (correct / total) * 100 if total > 0 else 0.0


def calculate_text_similarity(predicted: List[Tuple[str, str]], 
                            ground_truth: List[Tuple[str, str]]) -> float:
    """Calculate overall text similarity."""
    pred_text = " ".join([text for text, _ in predicted])
    gt_text = " ".join([text for text, _ in ground_truth])
    
    similarity = difflib.SequenceMatcher(None, 
                                       normalize_text(pred_text), 
                                       normalize_text(gt_text)).ratio()
    return similarity * 100


def analyze_speaker_distribution(data: List[Tuple[str, str]], title: str) -> Dict[str, int]:
    """Analyze speaker distribution in the data."""
    speaker_counts = {}
    for _, speaker in data:
        norm_speaker = normalize_speaker_name(speaker)
        speaker_counts[norm_speaker] = speaker_counts.get(norm_speaker, 0) + 1
    
    print(f"\n{title} Speaker Distribution:")
    for speaker, count in sorted(speaker_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {speaker}: {count}")
    
    return speaker_counts


def find_speaker_mapping_errors(predicted: List[Tuple[str, str]], 
                               ground_truth: List[Tuple[str, str]]) -> Dict[str, Dict[str, int]]:
    """Find common speaker mapping errors."""
    mapping_errors = {}
    
    if len(predicted) != len(ground_truth):
        return mapping_errors
    
    for (_, pred_speaker), (_, gt_speaker) in zip(predicted, ground_truth):
        pred_norm = normalize_speaker_name(pred_speaker)
        gt_norm = normalize_speaker_name(gt_speaker)
        
        if pred_norm != gt_norm:
            if gt_norm not in mapping_errors:
                mapping_errors[gt_norm] = {}
            mapping_errors[gt_norm][pred_norm] = mapping_errors[gt_norm].get(pred_norm, 0) + 1
    
    return mapping_errors


def evaluate_csvs(predicted_file: str, ground_truth_file: str) -> Dict[str, float]:
    """Main evaluation function."""
    print(f"Evaluating: {predicted_file} vs {ground_truth_file}")
    print("=" * 50)
    
    # Load data
    try:
        predicted_data = load_csv_data(predicted_file)
        ground_truth_data = load_csv_data(ground_truth_file)
    except Exception as e:
        print(f"Error loading CSV files: {e}")
        return {}
    
    print(f"Predicted rows: {len(predicted_data)}")
    print(f"Ground truth rows: {len(ground_truth_data)}")
    
    # Calculate metrics
    exact_match_acc = calculate_exact_match_accuracy(predicted_data, ground_truth_data)
    speaker_acc = calculate_speaker_accuracy(predicted_data, ground_truth_data)
    text_similarity = calculate_text_similarity(predicted_data, ground_truth_data)
    
    # Results
    results = {
        "exact_match_accuracy": exact_match_acc,
        "speaker_accuracy": speaker_acc,
        "text_similarity": text_similarity
    }
    
    print(f"\nEvaluation Results:")
    print(f"  Exact Match Accuracy: {exact_match_acc:.2f}%")
    print(f"  Speaker-Only Accuracy: {speaker_acc:.2f}%")
    print(f"  Text Similarity: {text_similarity:.2f}%")
    
    # Analyze speaker distributions
    pred_speakers = analyze_speaker_distribution(predicted_data, "Predicted")
    gt_speakers = analyze_speaker_distribution(ground_truth_data, "Ground Truth")
    
    # Find common mapping errors
    mapping_errors = find_speaker_mapping_errors(predicted_data, ground_truth_data)
    if mapping_errors:
        print(f"\nCommon Speaker Mapping Errors:")
        for true_speaker, error_map in mapping_errors.items():
            for predicted_speaker, count in sorted(error_map.items(), key=lambda x: x[1], reverse=True):
                print(f"  '{true_speaker}' -> '{predicted_speaker}': {count} times")
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Evaluate text-to-script workflow output")
    parser.add_argument("predicted", help="Path to predicted CSV file")
    parser.add_argument("ground_truth", help="Path to ground truth CSV file")
    parser.add_argument("--threshold", type=float, default=80.0, 
                       help="Minimum accuracy threshold for success (default: 80.0)")
    
    args = parser.parse_args()
    
    # Resolve file paths
    predicted_path = Path(args.predicted)
    ground_truth_path = Path(args.ground_truth)
    
    if not predicted_path.exists():
        print(f"Error: Predicted file not found: {predicted_path}")
        sys.exit(1)
    
    if not ground_truth_path.exists():
        print(f"Error: Ground truth file not found: {ground_truth_path}")
        sys.exit(1)
    
    # Run evaluation
    results = evaluate_csvs(str(predicted_path), str(ground_truth_path))
    
    if results:
        # Check if evaluation passed threshold
        speaker_accuracy = results.get("speaker_accuracy", 0.0)
        if speaker_accuracy >= args.threshold:
            print(f"\n✅ EVALUATION PASSED: {speaker_accuracy:.2f}% >= {args.threshold}%")
            sys.exit(0)
        else:
            print(f"\n❌ EVALUATION FAILED: {speaker_accuracy:.2f}% < {args.threshold}%")
            sys.exit(1)
    else:
        print("\n❌ EVALUATION ERROR")
        sys.exit(1)


if __name__ == "__main__":
    main()