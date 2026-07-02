from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


DEFAULT_METHODS = [
    "quantum_inspired",
    "genetic_algorithm",
    "positional_prior_random",
    "uniform_random",
]

METHOD_LABELS_PRIVATE = {
    "quantum_inspired": "QI evolving prior",
    "genetic_algorithm": "Genetic algorithm",
    "positional_prior_random": "Positional prior",
    "uniform_random": "Uniform random",
}

DATASET_LABELS = {
    "zelda": "The Legend of Zelda",
    "loderunner": "Lode Runner",
}

METRIC_COLUMNS = [
    "playability",
    "style_similarity",
    "novelty",
    "pattern_similarity_2x2",
    "difficulty_score",
    "target_difficulty_error",
]


def parse_list(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise SystemExit(f"Missing required columns: {missing}")


def clean_ascii(value: object) -> str:
    text = "" if pd.isna(value) else str(value)
    return text.replace("\\n", "\n").strip()


def choose_stimuli(
    df: pd.DataFrame,
    datasets: list[str],
    methods: list[str],
    per_cell: int,
    seed: int,
    playable_only: bool,
    playtest_ready: bool,
    quality_pool_multiplier: int,
) -> pd.DataFrame:
    require_columns(
        df,
        [
            "dataset",
            "method",
            "seed",
            "room_index",
            "is_reference",
            "ascii",
        ],
    )
    candidates = df[
        (df["dataset"].isin(datasets))
        & (df["method"].isin(methods))
        & (df["is_reference"].astype(int) == 0)
    ].copy()
    if playable_only or playtest_ready:
        require_columns(candidates, ["playability"])
        candidates = candidates[candidates["playability"].astype(float) >= 1.0]
    if playtest_ready:
        require_columns(candidates, ["difficulty_score", "style_similarity", "pattern_similarity_2x2"])

    rng = np.random.default_rng(seed)
    chosen: list[pd.DataFrame] = []
    for dataset in datasets:
        for method in methods:
            group = candidates[(candidates["dataset"] == dataset) & (candidates["method"] == method)].copy()
            if len(group) < per_cell:
                raise SystemExit(
                    f"Not enough stimuli for dataset={dataset}, method={method}: "
                    f"need {per_cell}, found {len(group)}"
                )
            if playtest_ready:
                difficulty_error = (
                    group["target_difficulty_error"].astype(float).fillna(0.0)
                    if "target_difficulty_error" in group.columns
                    else 0.0
                )
                group["selection_quality"] = (
                    group["playability"].astype(float)
                    + group["style_similarity"].astype(float)
                    + group["pattern_similarity_2x2"].astype(float)
                    - difficulty_error
                )
                pool_size = max(per_cell, min(len(group), per_cell * max(1, quality_pool_multiplier)))
                pool = group.sort_values("selection_quality", ascending=False).head(pool_size).copy()
                difficulties = pool["difficulty_score"].astype(float)
                quantiles = np.linspace(0.2, 0.8, per_cell)
                targets = [float(difficulties.quantile(q)) for q in quantiles]
                selected_indices = []
                available = set(pool.index)
                for target_diff in targets:
                    ranked = sorted(
                        available,
                        key=lambda idx: (
                            abs(float(pool.loc[idx, "difficulty_score"]) - target_diff),
                            -float(pool.loc[idx, "selection_quality"]),
                            float(rng.random()),
                        ),
                    )
                    picked = ranked[0]
                    selected_indices.append(picked)
                    available.remove(picked)
                chosen.append(pool.loc[selected_indices])
            else:
                positions = rng.choice(group.index.to_numpy(), size=per_cell, replace=False)
                chosen.append(candidates.loc[positions])

    selected = pd.concat(chosen, ignore_index=True)
    order = rng.permutation(len(selected))
    selected = selected.iloc[order].reset_index(drop=True)
    selected.insert(0, "stimulus_id", [f"S{i + 1:03d}" for i in range(len(selected))])
    selected.insert(1, "display_order", np.arange(1, len(selected) + 1))
    return selected


def write_stimuli_files(out_dir: Path, selected: pd.DataFrame) -> None:
    stimuli_dir = out_dir / "stimuli"
    stimuli_dir.mkdir(parents=True, exist_ok=True)
    for row in selected.to_dict(orient="records"):
        dataset_label = DATASET_LABELS.get(row["dataset"], row["dataset"])
        text = "\n".join(
            [
                f"Stimulus ID: {row['stimulus_id']}",
                f"Dataset: {dataset_label}",
                "",
                "Level grid:",
                clean_ascii(row["ascii"]),
                "",
            ]
        )
        (stimuli_dir / f"{row['stimulus_id']}.txt").write_text(text, encoding="utf-8")


def write_blinded_manifest(out_dir: Path, selected: pd.DataFrame) -> None:
    blinded = selected[["stimulus_id", "display_order", "dataset"]].copy()
    blinded["dataset_label"] = blinded["dataset"].map(lambda x: DATASET_LABELS.get(x, x))
    blinded["stimulus_file"] = blinded["stimulus_id"].map(lambda x: f"stimuli/{x}.txt")
    blinded.to_csv(out_dir / "stimuli_manifest_blinded.csv", index=False)


def write_private_key(out_dir: Path, selected: pd.DataFrame) -> None:
    cols = [
        "stimulus_id",
        "display_order",
        "dataset",
        "method",
        "seed",
        "room_index",
    ]
    cols += [col for col in METRIC_COLUMNS if col in selected.columns]
    key = selected[cols].copy()
    key["method_label"] = key["method"].map(lambda x: METHOD_LABELS_PRIVATE.get(x, x))
    key.to_csv(out_dir / "answer_key_private.csv", index=False)


def write_protocol(out_dir: Path, args: argparse.Namespace, selected: pd.DataFrame) -> None:
    cells = selected.groupby(["dataset", "method"]).size().reset_index(name="n")
    cell_lines = [
        f"- {DATASET_LABELS.get(row.dataset, row.dataset)} / "
        f"{METHOD_LABELS_PRIVATE.get(row.method, row.method)}: {int(row.n)} stimuli"
        for row in cells.itertuples(index=False)
    ]
    text = "\n".join(
        [
            "# Private Human Study Coordinator Notes",
            "",
            "## Purpose",
            "",
            "This pack supports a blinded goal-oriented playtest comparing generated levels across QI, GA, positional-prior, and uniform generators.",
            "",
            "## Participants",
            "",
            "Recruit 15--20 participants. If fewer than 15 responses are collected, report the study as pilot evidence only.",
            "",
            "## Design",
            "",
            f"- Randomization seed: {args.seed}",
            f"- Stimuli per dataset-method cell: {args.stimuli_per_cell}",
            f"- Total stimuli per participant: {len(selected)}",
            f"- Playable-only sampling: {bool(args.playable_only)}",
            f"- Playtest-ready selection: {bool(args.playtest_ready)}",
            "",
            "Cell counts:",
            "",
            *cell_lines,
            "",
            "## Blinding",
            "",
            "Share only `stimuli_manifest_blinded.csv`, `stimuli/`, and the generated playtest HTML with participants. Do not share this private notes file or `answer_key_private.csv` until all responses are collected.",
            "",
            "## Analysis",
            "",
            "After exporting responses as CSV, run `experiments/analyze_playtest_study.py` with the response CSV and `answer_key_private.csv`.",
            "",
        ]
    )
    (out_dir / "coordinator_notes_private.md").write_text(text, encoding="utf-8")


def write_public_pack_readme(out_dir: Path, selected: pd.DataFrame) -> None:
    datasets = sorted(DATASET_LABELS.get(x, x) for x in selected["dataset"].unique())
    text = "\n".join(
        [
            "# Blinded Playtest Pack",
            "",
            "This folder contains the public stimulus materials needed to build the participant-facing playtest.",
            "",
            "Do not ask for or inspect private method labels while building or running the playtest.",
            "",
            "## Files to Use",
            "",
            "- `stimuli_manifest_blinded.csv`: stimulus IDs, display order, dataset labels, and stimulus file paths.",
            "- `stimuli/`: one text-grid level per stimulus ID.",
            "",
            "## Playtest Setup",
            "",
            f"- Total stimuli: {len(selected)}",
            f"- Datasets: {', '.join(datasets)}",
            "- Build the HTML with `experiments/build_playtest_form.py`.",
            "- Keep stimulus order as given by `display_order` unless a later balanced randomization design is used.",
            "- Do not show generator names, automatic metrics, or method labels to participants.",
            "",
            "## Response Export",
            "",
            "The generated playtest exports responses with these columns:",
            "",
            "```text",
            "participant_id,stimulus_id,dataset_label,completed,time_seconds,moves,failures,restarts,timed_out,collected_count,required_collectibles,optimal_path_length,efficiency_ratio,timeout_seconds,difficulty_rating,fun_rating,overall_rating,comment",
            "```",
            "",
        ]
    )
    (out_dir / "README_FOR_PLAYTEST_BUILDER.md").write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a blinded human-study stimulus pack from generated PCG outputs.")
    parser.add_argument("--input-csv", type=Path, default=Path("experiments/output_reproduction_seed30/combined_results_detailed.csv"))
    parser.add_argument("--out-dir", type=Path, default=Path("human_study/study_pack_seed2026"))
    parser.add_argument("--datasets", default="zelda,loderunner")
    parser.add_argument("--methods", default=",".join(DEFAULT_METHODS))
    parser.add_argument("--stimuli-per-cell", type=int, default=3)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--playable-only", action="store_true", help="Sample only levels with automatic playability == 1.0. Off by default to preserve playability differences.")
    parser.add_argument("--playtest-ready", action="store_true", help="Select playable, higher-quality stimuli spread across difficulty for the goal-oriented playtest.")
    parser.add_argument("--quality-pool-multiplier", type=int, default=4, help="When --playtest-ready is used, keep this many candidates per selected stimulus before difficulty-spread sampling.")
    args = parser.parse_args()

    datasets = parse_list(args.datasets)
    methods = parse_list(args.methods)
    df = pd.read_csv(args.input_csv)
    selected = choose_stimuli(
        df,
        datasets,
        methods,
        args.stimuli_per_cell,
        args.seed,
        args.playable_only,
        args.playtest_ready,
        args.quality_pool_multiplier,
    )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_stimuli_files(args.out_dir, selected)
    write_blinded_manifest(args.out_dir, selected)
    write_private_key(args.out_dir, selected)
    write_protocol(args.out_dir, args, selected)
    write_public_pack_readme(args.out_dir, selected)

    config = {
        "input_csv": str(args.input_csv),
        "datasets": datasets,
        "methods": methods,
        "stimuli_per_cell": args.stimuli_per_cell,
        "seed": args.seed,
        "playable_only": bool(args.playable_only),
        "playtest_ready": bool(args.playtest_ready),
        "quality_pool_multiplier": int(args.quality_pool_multiplier),
        "stimuli_total": int(len(selected)),
    }
    (args.out_dir / "study_pack_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    print(f"wrote_stimuli={len(selected)} out_dir={args.out_dir}")


if __name__ == "__main__":
    main()
