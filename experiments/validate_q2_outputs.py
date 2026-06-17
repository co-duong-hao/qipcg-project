from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "experiments" / "output_fisat_main"
PAPER = ROOT / "paper" / "q2_next.tex"
FIGURES = ROOT / "paper" / "q2_figures"


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
    parser.add_argument("--skip-paper", action="store_true")
    return parser.parse_args()


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

    if not args.skip_paper:
        require(PAPER.exists(), f"Missing paper: {PAPER}")
        tex = PAPER.read_text(encoding="utf-8")
        figure_names = re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", tex)
        require(figure_names, "No figures found in q2_next.tex")
        require(all(name.lower().endswith(".pdf") for name in figure_names), "Paper figures should use vector PDF files")
        missing = [name for name in figure_names if not (FIGURES / name).exists()]
        require(not missing, f"Missing paper figures: {missing}")

    print("Experiment validation passed")
    print(f"detail_rows={len(detail)} generated={generated} reference={reference}")
    print(f"summary_rows={len(summary)} statistical_tests={len(tests)} p_value_nan=0")
    print(f"output_dir={out_dir}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Experiment validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
