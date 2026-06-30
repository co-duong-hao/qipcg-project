from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


BASELINES = ["genetic_algorithm", "positional_prior_random", "uniform_random"]
QI_METHOD = "quantum_inspired"
METRICS = [
    "completed",
    "time_seconds_completed",
    "moves",
    "failures",
    "restarts",
    "difficulty_rating",
    "fun_rating",
    "overall_rating",
]


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={col: col.strip().lower().replace(" ", "_").replace("-", "_") for col in df.columns})


def require_columns(df: pd.DataFrame, columns: list[str], label: str) -> None:
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise SystemExit(f"{label} is missing columns: {missing}")


def cliffs_delta(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) == 0 or len(b) == 0:
        return float("nan")
    greater = 0
    less = 0
    for x in a:
        greater += int(np.sum(x > b))
        less += int(np.sum(x < b))
    return (greater - less) / float(len(a) * len(b))


def paired_permutation_pvalue(a: np.ndarray, b: np.ndarray, permutations: int, seed: int) -> tuple[float, float]:
    diffs = a - b
    if len(diffs) == 0:
        return float("nan"), float("nan")
    observed = float(np.mean(diffs))
    if np.allclose(diffs, 0):
        return observed, 1.0
    rng = np.random.default_rng(seed)
    count = 0
    abs_observed = abs(observed)
    for _ in range(permutations):
        signs = rng.choice(np.array([-1.0, 1.0]), size=len(diffs))
        if abs(float(np.mean(diffs * signs))) >= abs_observed - 1e-12:
            count += 1
    return observed, (count + 1) / float(permutations + 1)


def holm_adjust(p_values: list[float]) -> list[float]:
    valid = sorted([(i, p) for i, p in enumerate(p_values) if not pd.isna(p)], key=lambda item: item[1])
    adjusted = [float("nan")] * len(p_values)
    running = 0.0
    m = len(valid)
    for rank, (idx, p) in enumerate(valid):
        value = min(1.0, (m - rank) * p)
        running = max(running, value)
        adjusted[idx] = running
    return adjusted


def clean_responses(responses: pd.DataFrame, answer_key: pd.DataFrame) -> pd.DataFrame:
    responses = normalize_columns(responses)
    answer_key = normalize_columns(answer_key)
    require_columns(responses, ["participant_id", "stimulus_id"], "responses")
    require_columns(answer_key, ["stimulus_id", "dataset", "method"], "answer_key")
    numeric_cols = ["completed", "time_seconds", "moves", "failures", "restarts", "timed_out", "difficulty_rating", "fun_rating", "overall_rating"]
    require_columns(responses, numeric_cols, "responses")
    for col in numeric_cols:
        responses[col] = pd.to_numeric(responses[col], errors="coerce")
    merged = responses.merge(answer_key[["stimulus_id", "dataset", "method"]], on="stimulus_id", how="left", validate="many_to_one")
    missing = int(merged["method"].isna().sum())
    if missing:
        raise SystemExit(f"{missing} response rows have stimulus IDs not found in answer_key")
    for col in ["difficulty_rating", "fun_rating", "overall_rating"]:
        bad = merged[col].notna() & ~merged[col].between(1, 5)
        if bad.any():
            raise SystemExit(f"Column {col} contains ratings outside 1--5")
    merged["time_seconds_completed"] = merged["time_seconds"].where(merged["completed"] == 1, np.nan)
    return merged


def summarize(cleaned: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (dataset, method), group in cleaned.groupby(["dataset", "method"]):
        item = {
            "dataset": dataset,
            "method": method,
            "n_trials": int(len(group)),
            "n_participants": int(group["participant_id"].nunique()),
        }
        for metric in METRICS:
            values = group[metric].dropna().astype(float)
            item[f"{metric}_mean"] = float(values.mean()) if len(values) else float("nan")
            item[f"{metric}_std"] = float(values.std(ddof=1)) if len(values) > 1 else 0.0
        rows.append(item)
    return pd.DataFrame(rows).sort_values(["dataset", "method"])


def pairwise_tests(cleaned: pd.DataFrame, permutations: int, seed: int) -> pd.DataFrame:
    participant_means = cleaned.groupby(["participant_id", "dataset", "method"], as_index=False)[METRICS].mean(numeric_only=True)
    rows = []
    test_index = 0
    for dataset in sorted(participant_means["dataset"].unique()):
        dataset_rows = participant_means[participant_means["dataset"] == dataset]
        for metric in METRICS:
            pivot = dataset_rows.pivot(index="participant_id", columns="method", values=metric)
            for baseline in BASELINES:
                if QI_METHOD not in pivot.columns or baseline not in pivot.columns:
                    continue
                paired = pivot[[QI_METHOD, baseline]].dropna()
                if paired.empty:
                    continue
                q = paired[QI_METHOD].to_numpy(dtype=float)
                b = paired[baseline].to_numpy(dtype=float)
                mean_diff, p_raw = paired_permutation_pvalue(q, b, permutations, seed + test_index * 1009)
                rows.append(
                    {
                        "dataset": dataset,
                        "metric": metric,
                        "method_a": QI_METHOD,
                        "method_b": baseline,
                        "n_pairs": int(len(paired)),
                        "mean_a": float(np.mean(q)),
                        "mean_b": float(np.mean(b)),
                        "mean_diff_a_minus_b": mean_diff,
                        "p_value": p_raw,
                        "cliffs_delta": cliffs_delta(q, b),
                    }
                )
                test_index += 1
    result = pd.DataFrame(rows)
    if not result.empty:
        result["p_value_holm"] = holm_adjust(result["p_value"].tolist())
        result["significant_holm_0_05"] = result["p_value_holm"] <= 0.05
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze blinded playtest responses.")
    parser.add_argument("--responses", type=Path, required=True)
    parser.add_argument("--answer-key", type=Path, default=Path("human_study/study_pack_seed2026/answer_key_private.csv"))
    parser.add_argument("--out-dir", type=Path, default=Path("human_study_playtest/results_seed2026"))
    parser.add_argument("--permutations", type=int, default=9999)
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()

    responses = pd.read_csv(args.responses)
    answer_key = pd.read_csv(args.answer_key)
    cleaned = clean_responses(responses, answer_key)
    summary = summarize(cleaned)
    tests = pairwise_tests(cleaned, args.permutations, args.seed)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    cleaned.to_csv(args.out_dir / "playtest_cleaned_responses.csv", index=False)
    summary.to_csv(args.out_dir / "playtest_summary.csv", index=False)
    tests.to_csv(args.out_dir / "playtest_pairwise_tests.csv", index=False)
    print(f"participants={cleaned['participant_id'].nunique()} responses={len(cleaned)} out_dir={args.out_dir}")


if __name__ == "__main__":
    main()
