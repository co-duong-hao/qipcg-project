from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


METHODS = [
    "quantum_inspired",
    "genetic_algorithm",
    "positional_prior_random",
    "uniform_random",
]

METHOD_LEAK_TERMS = [
    "quantum_inspired",
    "qi evolving",
    "genetic_algorithm",
    "genetic algorithm",
    "positional_prior",
    "positional prior",
    "uniform_random",
    "uniform random",
]

RESPONSE_COLUMNS = [
    "participant_id",
    "stimulus_id",
    "completed",
    "time_seconds",
    "moves",
    "failures",
    "restarts",
    "timed_out",
    "difficulty_rating",
    "fun_rating",
    "overall_rating",
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"VALIDATION FAILED: {message}")


def read_csv(path: Path, label: str) -> pd.DataFrame:
    require(path.exists(), f"Missing {label}: {path}")
    return pd.read_csv(path)


def validate_no_public_method_leak(paths: list[Path]) -> None:
    for path in paths:
        require(path.exists(), f"Missing public file: {path}")
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        leaks = [term for term in METHOD_LEAK_TERMS if term in text]
        require(not leaks, f"Public file leaks method labels: {path} terms={leaks}")


def validate_pack(args: argparse.Namespace) -> None:
    source_pack = args.source_study_pack
    playtest_pack = args.playtest_pack
    manifest = read_csv(source_pack / "stimuli_manifest_blinded.csv", "blinded manifest")
    key = read_csv(source_pack / "answer_key_private.csv", "private answer key")
    required_manifest = {"stimulus_id", "display_order", "dataset", "dataset_label", "stimulus_file"}
    required_key = {"stimulus_id", "display_order", "dataset", "method"}
    require(required_manifest.issubset(manifest.columns), f"Blinded manifest missing columns: {required_manifest - set(manifest.columns)}")
    require(required_key.issubset(key.columns), f"Private key missing columns: {required_key - set(key.columns)}")
    require("method" not in manifest.columns, "Blinded manifest must not contain a method column")
    require(set(key["method"]) == set(METHODS), f"Private key methods should be {METHODS}, got {sorted(key['method'].unique())}")
    require(len(manifest) == args.expected_stimuli, f"Expected {args.expected_stimuli} stimuli, got {len(manifest)}")
    require(set(manifest["stimulus_id"]) == set(key["stimulus_id"]), "Private key and manifest stimulus IDs differ")
    counts = key.groupby(["dataset", "method"]).size()
    bad_counts = counts[counts != args.expected_per_cell]
    require(bad_counts.empty, f"Expected {args.expected_per_cell} stimuli per dataset-method cell, got {bad_counts.to_dict()}")

    public_files = [playtest_pack / "playtest_form.html", source_pack / "stimuli_manifest_blinded.csv"]
    public_files.extend(sorted((source_pack / "stimuli").glob("*.txt")))
    validate_no_public_method_leak(public_files)
    print(f"playtest_pack_ok stimuli={len(manifest)} html={playtest_pack / 'playtest_form.html'}")


def validate_responses(args: argparse.Namespace) -> None:
    if args.responses is None:
        return
    responses = read_csv(args.responses, "responses")
    key = read_csv(args.source_study_pack / "answer_key_private.csv", "private answer key")
    missing = set(RESPONSE_COLUMNS) - set(responses.columns)
    require(not missing, f"Responses missing columns: {sorted(missing)}")
    require(set(responses["stimulus_id"]).issubset(set(key["stimulus_id"])), "Responses contain unknown stimulus IDs")
    participant_count = int(responses["participant_id"].nunique())
    require(participant_count >= args.min_participants, f"Need at least {args.min_participants} participants, got {participant_count}")
    expected_ids = set(key["stimulus_id"])
    for participant_id, group in responses.groupby("participant_id"):
        ids = set(group["stimulus_id"])
        missing_ids = expected_ids - ids
        duplicate_count = int(group["stimulus_id"].duplicated().sum())
        require(not missing_ids, f"Participant {participant_id} is missing stimuli: {sorted(missing_ids)}")
        require(duplicate_count == 0, f"Participant {participant_id} has duplicate stimulus rows")

    for col in ["completed", "timed_out"]:
        numeric = pd.to_numeric(responses[col], errors="coerce")
        require(numeric.notna().all(), f"{col} contains non-numeric values")
        require(numeric.isin([0, 1]).all(), f"{col} must contain only 0/1")
    for col in ["time_seconds", "moves", "failures", "restarts"]:
        numeric = pd.to_numeric(responses[col], errors="coerce")
        require(numeric.notna().all(), f"{col} contains non-numeric values")
        require((numeric >= 0).all(), f"{col} contains negative values")
    for col in ["difficulty_rating", "fun_rating", "overall_rating"]:
        numeric = pd.to_numeric(responses[col], errors="coerce")
        require(numeric.notna().all(), f"{col} contains non-numeric values")
        require(numeric.between(1, 5).all(), f"{col} contains values outside 1--5")
    print(f"playtest_responses_ok participants={participant_count} rows={len(responses)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate blinded playtest files and optional response CSV.")
    parser.add_argument("--source-study-pack", type=Path, default=Path("human_study/study_pack_seed2026"))
    parser.add_argument("--playtest-pack", type=Path, default=Path("human_study_playtest/playtest_pack_seed2026"))
    parser.add_argument("--responses", type=Path)
    parser.add_argument("--expected-stimuli", type=int, default=24)
    parser.add_argument("--expected-per-cell", type=int, default=3)
    parser.add_argument("--min-participants", type=int, default=1)
    args = parser.parse_args()

    validate_pack(args)
    validate_responses(args)


if __name__ == "__main__":
    main()
