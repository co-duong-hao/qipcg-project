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

RATING_COLUMNS = ["playability", "style", "novelty", "overall"]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"VALIDATION FAILED: {message}")


def read_csv(path: Path, label: str) -> pd.DataFrame:
    require(path.exists(), f"Missing {label}: {path}")
    return pd.read_csv(path)


def validate_public_no_method_leak(study_pack: Path) -> None:
    public_files = [
        study_pack / "stimuli_manifest_blinded.csv",
        study_pack / "survey_questions.md",
        study_pack / "README_FOR_FORM_BUILDER.md",
    ]
    html_form = study_pack / "survey_form.html"
    if html_form.exists():
        public_files.append(html_form)
    public_files.extend(sorted((study_pack / "stimuli").glob("*.txt")))
    for path in public_files:
        require(path.exists(), f"Missing public file: {path}")
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        leaks = [term for term in METHOD_LEAK_TERMS if term in text]
        require(not leaks, f"Public file leaks method labels: {path} terms={leaks}")


def validate_study_pack(args: argparse.Namespace) -> None:
    study_pack = args.study_pack
    manifest = read_csv(study_pack / "stimuli_manifest_blinded.csv", "blinded manifest")
    key = read_csv(study_pack / "answer_key_private.csv", "private answer key")

    required_manifest = {"stimulus_id", "display_order", "dataset", "dataset_label", "stimulus_file"}
    required_key = {"stimulus_id", "display_order", "dataset", "method"}
    require(required_manifest.issubset(manifest.columns), f"Blinded manifest missing columns: {required_manifest - set(manifest.columns)}")
    require(required_key.issubset(key.columns), f"Private key missing columns: {required_key - set(key.columns)}")
    require("method" not in manifest.columns, "Blinded manifest must not contain a method column")
    require(len(manifest) == args.expected_stimuli, f"Expected {args.expected_stimuli} stimuli, got {len(manifest)}")
    require(len(key) == len(manifest), "Private key and blinded manifest row counts differ")
    require(set(manifest["stimulus_id"]) == set(key["stimulus_id"]), "Private key and manifest stimulus IDs differ")
    require(manifest["stimulus_id"].is_unique, "Stimulus IDs must be unique in manifest")
    require(key["stimulus_id"].is_unique, "Stimulus IDs must be unique in private key")
    require(set(key["method"]) == set(METHODS), f"Private key methods should be {METHODS}, got {sorted(key['method'].unique())}")

    expected_per_cell = args.expected_per_cell
    counts = key.groupby(["dataset", "method"]).size()
    bad_counts = counts[counts != expected_per_cell]
    require(bad_counts.empty, f"Expected {expected_per_cell} stimuli per dataset-method cell, got {bad_counts.to_dict()}")

    for row in manifest.itertuples(index=False):
        stimulus_path = study_pack / str(row.stimulus_file)
        require(stimulus_path.exists(), f"Missing stimulus file: {stimulus_path}")
        text = stimulus_path.read_text(encoding="utf-8", errors="ignore")
        require(str(row.stimulus_id) in text, f"Stimulus file does not contain its stimulus ID: {stimulus_path}")

    validate_public_no_method_leak(study_pack)
    print(f"study_pack_ok stimuli={len(manifest)} datasets={sorted(key['dataset'].unique())}")


def validate_responses(args: argparse.Namespace) -> None:
    if args.responses is None:
        return
    responses = read_csv(args.responses, "responses")
    key = read_csv(args.study_pack / "answer_key_private.csv", "private answer key")
    required = {"participant_id", "stimulus_id", *RATING_COLUMNS}
    require(required.issubset(responses.columns), f"Responses missing columns: {required - set(responses.columns)}")
    require(set(responses["stimulus_id"]).issubset(set(key["stimulus_id"])), "Responses contain unknown stimulus IDs")

    participant_count = int(responses["participant_id"].nunique())
    require(participant_count >= args.min_participants, f"Need at least {args.min_participants} participants, got {participant_count}")
    require(participant_count <= args.max_participants, f"Expected at most {args.max_participants} participants, got {participant_count}")

    expected_ids = set(key["stimulus_id"])
    for participant_id, group in responses.groupby("participant_id"):
        ids = set(group["stimulus_id"])
        missing = expected_ids - ids
        duplicate_count = int(group["stimulus_id"].duplicated().sum())
        require(not missing, f"Participant {participant_id} is missing stimuli: {sorted(missing)}")
        require(duplicate_count == 0, f"Participant {participant_id} has duplicate stimulus ratings")

    for col in RATING_COLUMNS:
        numeric = pd.to_numeric(responses[col], errors="coerce")
        require(numeric.notna().all(), f"Response column {col} contains non-numeric values")
        require(numeric.between(1, 5).all(), f"Response column {col} contains values outside 1--5")
    print(f"responses_ok participants={participant_count} rows={len(responses)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a blinded mini human-study pack and optional response CSV.")
    parser.add_argument("--study-pack", type=Path, default=Path("human_study/study_pack_seed2026"))
    parser.add_argument("--responses", type=Path)
    parser.add_argument("--expected-stimuli", type=int, default=24)
    parser.add_argument("--expected-per-cell", type=int, default=3)
    parser.add_argument("--min-participants", type=int, default=15)
    parser.add_argument("--max-participants", type=int, default=20)
    args = parser.parse_args()

    validate_study_pack(args)
    validate_responses(args)


if __name__ == "__main__":
    main()
