from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "experiments" / "output_reproduction_seed30"
PAPER = ROOT / "paper" / "main.tex"
FIGURES = ROOT / "paper" / "figures"

STANDARD_MAIN_CONFIG = {
    "datasets": ["zelda", "loderunner"],
    "rooms_per_method": 500,
    "seeds": 30,
    "seed_start": 42,
    "split_seed": 2026,
    "train_ratio": 0.8,
    "target_difficulty": 0.5,
    "methods": [
        "uniform_random",
        "dataset_prior_random",
        "positional_prior_random",
        "quantum_inspired",
        "genetic_algorithm",
        "simulated_annealing",
    ],
    "k": 24,
    "quantum_population": 8,
    "quantum_iterations": 3,
    "quantum_eta": 0.18,
    "quantum_min_prob": 0.005,
    "quantum_prior_anchor": 0.05,
    "novelty_weight": 0.0,
    "ga_population": 8,
    "ga_generations": 2,
    "mutation_rate": 0.03,
    "sa_steps": 23,
    "stat_permutations": 9999,
}

STANDARD_ABLATION_CONFIG = {
    "ablation_rooms_per_cell": 200,
    "k_values": [8, 16, 24, 32, 64],
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate generated experiment outputs and paper assets.")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--expected-generated", type=int)
    parser.add_argument("--expected-reference", type=int)
    parser.add_argument("--expected-ablation-rows", type=int)
    parser.add_argument("--expected-ablation-cell-n", type=int)
    parser.add_argument("--expected-budget-sweep-rows", type=int)
    parser.add_argument("--expected-novelty-sweep-rows", type=int)
    parser.add_argument("--expected-sweep-cell-n", type=int)
    parser.add_argument(
        "--expect-standard-config",
        action="store_true",
        help="Check run_config_main.json and run_config_ablation.json against the standard reproduction configuration.",
    )
    parser.add_argument("--skip-paper", action="store_true")
    return parser.parse_args()


def load_json(path: Path) -> dict:
    require(path.exists(), f"Missing config file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def require_config_values(actual: dict, expected: dict, name: str) -> None:
    for key, expected_value in expected.items():
        require(key in actual, f"{name} missing config key: {key}")
        require(
            actual[key] == expected_value,
            f"{name} config mismatch for {key}: expected {expected_value!r}, got {actual[key]!r}",
        )


def main() -> int:
    args = parse_args()
    out_dir = args.out_dir if args.out_dir.is_absolute() else ROOT / args.out_dir
    require(out_dir.exists(), f"Missing output directory: {out_dir}")

    detail = pd.read_csv(out_dir / "combined_results_detailed.csv")
    summary = pd.read_csv(out_dir / "combined_results_summary.csv")
    tests = pd.read_csv(out_dir / "combined_statistical_tests.csv")

    require(set(detail["dataset"].unique()).issubset({"zelda", "loderunner"}), "Unexpected dataset name")
    require(detail.isna().sum().sum() == 0, "Detailed results contain NaN values")
    require(summary.isna().sum().sum() == 0, "Summary results contain NaN values")
    require(tests["p_value"].isna().sum() == 0, "Statistical tests contain NaN p-values")
    require("p_value_holm" in tests.columns, "Missing Holm-adjusted p-value column")
    require("significant_holm_0_05" in tests.columns, "Missing Holm significance column")
    require("fitness_evaluations" in detail.columns, "Missing fitness_evaluations in detailed results")
    require("fitness_evaluations_mean" in summary.columns, "Missing fitness_evaluations in summary")

    generated = int((detail["is_reference"] == 0).sum())
    reference = int((detail["is_reference"] == 1).sum())
    if args.expected_generated is not None:
        require(generated == args.expected_generated, f"Expected {args.expected_generated} generated rows, got {generated}")
    if args.expected_reference is not None:
        require(reference == args.expected_reference, f"Expected {args.expected_reference} held-out reference rows, got {reference}")

    ablation_detail_path = out_dir / "combined_ablation_detailed.csv"
    ablation_summary_path = out_dir / "combined_ablation_summary.csv"
    if args.expected_ablation_rows is not None or args.expected_ablation_cell_n is not None:
        require(ablation_detail_path.exists(), f"Missing ablation detail file: {ablation_detail_path}")
        require(ablation_summary_path.exists(), f"Missing ablation summary file: {ablation_summary_path}")
    if ablation_detail_path.exists() and ablation_summary_path.exists():
        ablation_detail = pd.read_csv(ablation_detail_path)
        ablation_summary = pd.read_csv(ablation_summary_path)
        require(ablation_detail.isna().sum().sum() == 0, "Ablation results contain NaN values")
        require("fitness_evaluations" in ablation_detail.columns, "Missing ablation fitness_evaluations")
        require("fitness_evaluations_mean" in ablation_summary.columns, "Missing ablation fitness_evaluations summary")
        if args.expected_ablation_rows is not None:
            require(
                len(ablation_detail) == args.expected_ablation_rows,
                f"Expected {args.expected_ablation_rows} ablation rows, got {len(ablation_detail)}",
            )
        if args.expected_ablation_cell_n is not None:
            require(
                set(ablation_summary["n"].unique()) == {args.expected_ablation_cell_n},
                f"Ablation cell n should be exactly {args.expected_ablation_cell_n}",
            )

    budget_detail_path = out_dir / "combined_budget_sweep_detailed.csv"
    budget_summary_path = out_dir / "combined_budget_sweep_summary.csv"
    if args.expected_budget_sweep_rows is not None:
        require(budget_detail_path.exists(), f"Missing budget sweep detail file: {budget_detail_path}")
        require(budget_summary_path.exists(), f"Missing budget sweep summary file: {budget_summary_path}")
    if budget_detail_path.exists() and budget_summary_path.exists():
        budget_detail = pd.read_csv(budget_detail_path)
        budget_summary = pd.read_csv(budget_summary_path)
        require(budget_detail.isna().sum().sum() == 0, "Budget sweep contains NaN values")
        require(budget_summary.isna().sum().sum() == 0, "Budget sweep summary contains NaN values")
        require(set(budget_detail["method"].unique()) == {"quantum_inspired", "genetic_algorithm", "simulated_annealing"}, "Budget sweep should only contain QI, GA, and SA")
        require((budget_detail["fitness_evaluations"] == budget_detail["fitness_budget"]).all(), "Budget sweep fitness_evaluations must match fitness_budget")
        if args.expected_budget_sweep_rows is not None:
            require(
                len(budget_detail) == args.expected_budget_sweep_rows,
                f"Expected {args.expected_budget_sweep_rows} budget sweep rows, got {len(budget_detail)}",
            )
        if args.expected_sweep_cell_n is not None:
            require(
                set(budget_summary[budget_summary["seed"].astype(str) != "ALL"]["n"].unique()) == {args.expected_sweep_cell_n},
                f"Budget sweep seed-level n should be exactly {args.expected_sweep_cell_n}",
            )

    novelty_detail_path = out_dir / "combined_novelty_sweep_detailed.csv"
    novelty_summary_path = out_dir / "combined_novelty_sweep_summary.csv"
    if args.expected_novelty_sweep_rows is not None:
        require(novelty_detail_path.exists(), f"Missing novelty sweep detail file: {novelty_detail_path}")
        require(novelty_summary_path.exists(), f"Missing novelty sweep summary file: {novelty_summary_path}")
    if novelty_detail_path.exists() and novelty_summary_path.exists():
        novelty_detail = pd.read_csv(novelty_detail_path)
        novelty_summary = pd.read_csv(novelty_summary_path)
        require(novelty_detail.isna().sum().sum() == 0, "Novelty sweep contains NaN values")
        require(novelty_summary.isna().sum().sum() == 0, "Novelty sweep summary contains NaN values")
        require(set(novelty_detail["method"].unique()) == {"quantum_inspired", "genetic_algorithm", "simulated_annealing"}, "Novelty sweep should only contain QI, GA, and SA")
        require((novelty_detail["fitness_evaluations"] == novelty_detail["fitness_budget"]).all(), "Novelty sweep fitness_evaluations must match fitness_budget")
        if args.expected_novelty_sweep_rows is not None:
            require(
                len(novelty_detail) == args.expected_novelty_sweep_rows,
                f"Expected {args.expected_novelty_sweep_rows} novelty sweep rows, got {len(novelty_detail)}",
            )
        if args.expected_sweep_cell_n is not None:
            require(
                set(novelty_summary[novelty_summary["seed"].astype(str) != "ALL"]["n"].unique()) == {args.expected_sweep_cell_n},
                f"Novelty sweep seed-level n should be exactly {args.expected_sweep_cell_n}",
            )

    if args.expect_standard_config:
        run_config_main = load_json(out_dir / "run_config_main.json")
        run_config_ablation = load_json(out_dir / "run_config_ablation.json")
        require_config_values(run_config_main, STANDARD_MAIN_CONFIG, "run_config_main.json")
        require_config_values(run_config_ablation, STANDARD_ABLATION_CONFIG, "run_config_ablation.json")

    if not args.skip_paper:
        require(PAPER.exists(), f"Missing paper: {PAPER}")
        tex = PAPER.read_text(encoding="utf-8")
        figure_names = re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", tex)
        require(figure_names, "No figures found in paper/main.tex")
        require(all(name.lower().endswith(".pdf") for name in figure_names), "Paper figures should use vector PDF files")
        missing = [name for name in figure_names if not (FIGURES / name).exists()]
        require(not missing, f"Missing paper figures: {missing}")

    print("Experiment validation passed")
    print(f"detail_rows={len(detail)} generated={generated} reference={reference}")
    print(f"summary_rows={len(summary)} statistical_tests={len(tests)} p_value_nan=0")
    if args.expect_standard_config:
        print("standard_config=passed")
    print("note=generation_time metrics are machine-dependent and should not be compared byte-for-byte across computers")
    print(f"output_dir={out_dir}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Experiment validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
