from __future__ import annotations

import argparse
import math
import statistics
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape
from reportlab.pdfgen import canvas

import run_experiments as exp


DATASET_LABELS = {"zelda": "Zelda", "loderunner": "Lode Runner"}


def parse_float_list(raw: str) -> list[float]:
    return [float(x.strip()) for x in raw.split(",") if x.strip()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run target difficulty controllability sweep for QI-PCG.")
    parser.add_argument("--vglc-root", type=Path, default=Path("TheVGLC"))
    parser.add_argument("--datasets", default="zelda,loderunner")
    parser.add_argument("--out-dir", type=Path, default=Path("experiments") / "output_difficulty_sweep")
    parser.add_argument("--targets", default="0.2,0.3,0.4,0.5,0.6,0.7,0.8")
    parser.add_argument("--rooms-per-cell", type=int, default=100)
    parser.add_argument("--seeds", type=int, default=30)
    parser.add_argument("--seed-start", type=int, default=42)
    parser.add_argument("--split-seed", type=int, default=2026)
    parser.add_argument("--train-ratio", type=float, default=0.8)
    parser.add_argument("--fitness-budget", type=int, default=24)
    parser.add_argument("--quantum-population", type=int, default=8)
    parser.add_argument("--quantum-eta", type=float, default=0.75)
    parser.add_argument("--quantum-min-prob", type=float, default=0.02)
    parser.add_argument("--quantum-prior-anchor", type=float, default=0.10)
    parser.add_argument("--novelty-weight", type=float, default=0.0)
    parser.add_argument("--novelty-metric", choices=["ngram_js", "hamming"], default="ngram_js")
    return parser.parse_args()


def search_params(args: argparse.Namespace) -> dict:
    if args.fitness_budget % args.quantum_population != 0:
        raise ValueError("--fitness-budget must be divisible by --quantum-population")
    return {
        "k": args.fitness_budget,
        "ga_population": 8,
        "ga_generations": 2,
        "mutation_rate": 0.05,
        "sa_steps": args.fitness_budget - 1,
        "quantum_population": args.quantum_population,
        "quantum_iterations": args.fitness_budget // args.quantum_population,
        "quantum_eta": args.quantum_eta,
        "quantum_min_prob": args.quantum_min_prob,
        "quantum_prior_anchor": args.quantum_prior_anchor,
        "novelty_weight": args.novelty_weight,
    }


def run_dataset(spec: exp.DatasetSpec, args: argparse.Namespace, targets: list[float]) -> list[dict]:
    records, _meta = exp.load_dataset(spec)
    train, test = exp.split_records(records, args.train_ratio, args.split_seed)
    stats_data = exp.build_stats(train, test, spec, args.novelty_metric)
    params = search_params(args)
    rows: list[dict] = []
    for target in targets:
        print(f"dataset={spec.name} target={target:.1f}", flush=True)
        for seed in range(args.seed_start, args.seed_start + args.seeds):
            rng_seed = (
                seed * 1009
                + exp.METHOD_SEED_OFFSETS["quantum_inspired"]
                + exp.stable_offset(spec.name, "difficulty_target", target)
            )
            rng = np.random.default_rng(rng_seed)
            for idx in range(args.rooms_per_cell):
                start = time.perf_counter()
                failure = 0
                try:
                    grid = exp.quantum_inspired(rng, stats_data, target, params)
                except Exception:
                    failure = 1
                    h, w, _ = stats_data["positional_prior"].shape
                    grid = np.full((h, w), exp.CAT_TO_ID["wall"], dtype=np.int16)
                elapsed = time.perf_counter() - start
                metrics = exp.evaluate_grid(grid, stats_data, target)
                rows.append(
                    {
                        "dataset": spec.name,
                        "method": "quantum_inspired",
                        "seed": seed,
                        "room_index": idx,
                        "target_difficulty": target,
                        "fitness_budget": args.fitness_budget,
                        "novelty_weight": args.novelty_weight,
                        "generation_time": elapsed,
                        "fitness_evaluations": args.fitness_budget,
                        "failure_flag": failure,
                        **metrics,
                    }
                )
    return rows


def summarize(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    grouped: dict[tuple[str, str, float], list[dict]] = defaultdict(list)
    for row in rows:
        grouped[(row["dataset"], str(row["seed"]), float(row["target_difficulty"]))].append(row)
        grouped[(row["dataset"], "ALL", float(row["target_difficulty"]))].append(row)

    per_target: list[dict] = []
    for (dataset, seed, target), group in sorted(grouped.items()):
        difficulties = [float(r["difficulty_score"]) for r in group]
        errors = [abs(float(r["difficulty_score"]) - target) for r in group]
        per_target.append(
            {
                "dataset": dataset,
                "seed": seed,
                "target_difficulty": target,
                "n": len(group),
                "achieved_difficulty_mean": statistics.fmean(difficulties),
                "achieved_difficulty_std": statistics.pstdev(difficulties) if len(difficulties) > 1 else 0.0,
                "control_mae": statistics.fmean(errors),
                "playability_mean": statistics.fmean(float(r["playability"]) for r in group),
                "style_similarity_mean": statistics.fmean(float(r["style_similarity"]) for r in group),
                "pattern_similarity_2x2_mean": statistics.fmean(float(r["pattern_similarity_2x2"]) for r in group),
                "novelty_mean": statistics.fmean(float(r["novelty"]) for r in group),
            }
        )

    overall: list[dict] = []
    for dataset in sorted({row["dataset"] for row in rows}):
        all_rows = [row for row in rows if row["dataset"] == dataset]
        all_summary = [row for row in per_target if row["dataset"] == dataset and row["seed"] == "ALL"]
        achieved_by_target = [float(row["achieved_difficulty_mean"]) for row in sorted(all_summary, key=lambda r: float(r["target_difficulty"]))]
        targets = [float(row["target_difficulty"]) for row in sorted(all_summary, key=lambda r: float(r["target_difficulty"]))]
        diffs = np.diff(np.array(achieved_by_target, dtype=float))
        monotone_steps = int(np.sum(diffs >= -1e-9))
        corr = float(np.corrcoef(targets, achieved_by_target)[0, 1]) if len(targets) > 1 else float("nan")
        overall.append(
            {
                "dataset": dataset,
                "n": len(all_rows),
                "targets": ",".join(f"{t:.1f}" for t in targets),
                "overall_control_mae": statistics.fmean(abs(float(r["difficulty_score"]) - float(r["target_difficulty"])) for r in all_rows),
                "monotone_adjacent_steps": monotone_steps,
                "monotone_total_steps": max(0, len(targets) - 1),
                "is_monotone_non_decreasing": monotone_steps == max(0, len(targets) - 1),
                "target_achieved_correlation": corr,
                "achieved_min": min(achieved_by_target),
                "achieved_max": max(achieved_by_target),
                "achieved_range": max(achieved_by_target) - min(achieved_by_target),
            }
        )
    return per_target, overall


def draw_difficulty_chart(path: Path, summary: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(path), pagesize=landscape((560, 360)))
    width, height = landscape((560, 360))
    margin_l, margin_r, margin_t, margin_b = 70, 28, 42, 58
    gap = 38
    panel_w = (width - margin_l - margin_r - gap) / 2
    panel_h = height - margin_t - margin_b
    targets = sorted(summary["target_difficulty"].astype(float).unique())
    x_min, x_max = min(targets), max(targets)
    y_min, y_max = 0.0, 0.8
    colors_by_dataset = {"zelda": colors.HexColor("#0B5DB8"), "loderunner": colors.HexColor("#2CA02C")}
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(width / 2, height - 22, "Target vs. achieved difficulty")
    for idx, dataset in enumerate(["zelda", "loderunner"]):
        left = margin_l + idx * (panel_w + gap)
        bottom = margin_b
        right = left + panel_w
        top = bottom + panel_h
        panel = summary[(summary["dataset"] == dataset) & (summary["seed"].astype(str) == "ALL")].sort_values("target_difficulty")

        c.setStrokeColor(colors.black)
        c.setLineWidth(0.7)
        c.line(left, bottom, right, bottom)
        c.line(left, bottom, left, top)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString((left + right) / 2, top + 14, DATASET_LABELS[dataset])
        c.setFont("Helvetica", 7.5)
        for t in targets:
            x = left + (t - x_min) / (x_max - x_min) * panel_w
            c.setStrokeColor(colors.lightgrey)
            c.line(x, bottom, x, top)
            c.setStrokeColor(colors.black)
            c.line(x, bottom, x, bottom - 3)
            c.drawCentredString(x, bottom - 14, f"{t:.1f}")
        for y in [0.0, 0.2, 0.4, 0.6, 0.8]:
            yy = bottom + (y - y_min) / (y_max - y_min) * panel_h
            c.setStrokeColor(colors.lightgrey)
            c.line(left, yy, right, yy)
            c.setStrokeColor(colors.black)
            c.line(left - 3, yy, left, yy)
            c.drawRightString(left - 6, yy - 2.5, f"{y:.1f}")

        def px(x_val: float) -> float:
            return left + (x_val - x_min) / (x_max - x_min) * panel_w

        def py(y_val: float) -> float:
            return bottom + (y_val - y_min) / (y_max - y_min) * panel_h

        c.setStrokeColor(colors.grey)
        c.setDash(3, 3)
        c.line(px(x_min), py(x_min), px(x_max), py(x_max))
        c.setDash()

        pts = [(px(float(row["target_difficulty"])), py(float(row["achieved_difficulty_mean"]))) for _, row in panel.iterrows()]
        c.setStrokeColor(colors_by_dataset[dataset])
        c.setFillColor(colors_by_dataset[dataset])
        c.setLineWidth(1.6)
        for a, b in zip(pts, pts[1:]):
            c.line(a[0], a[1], b[0], b[1])
        for x, y in pts:
            c.circle(x, y, 3, stroke=1, fill=1)

        c.setFont("Helvetica", 8)
        c.setFillColor(colors.black)
        c.drawCentredString((left + right) / 2, 24, "Target difficulty")
        if idx == 0:
            c.saveState()
            c.translate(18, (bottom + top) / 2)
            c.rotate(90)
            c.drawCentredString(0, 0, "Achieved difficulty")
            c.restoreState()
    c.save()


def main() -> None:
    args = parse_args()
    targets = parse_float_list(args.targets)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    specs = exp.dataset_specs(args.vglc_root)
    selected = [name.strip() for name in args.datasets.split(",") if name.strip()]
    detail: list[dict] = []
    for name in selected:
        detail.extend(run_dataset(specs[name], args, targets))
    per_target, overall = summarize(detail)
    exp.write_csv(args.out_dir / "combined_difficulty_sweep_detailed.csv", detail, include_ascii=False)
    exp.write_csv(args.out_dir / "combined_difficulty_sweep_summary.csv", per_target, include_ascii=False)
    exp.write_csv(args.out_dir / "combined_difficulty_sweep_overall.csv", overall, include_ascii=False)
    exp.write_json(
        args.out_dir / "run_config_difficulty_sweep.json",
        {
            "datasets": selected,
            "targets": targets,
            "rooms_per_cell": args.rooms_per_cell,
            "seeds": args.seeds,
            "seed_start": args.seed_start,
            "fitness_budget": args.fitness_budget,
            "novelty_weight": args.novelty_weight,
            "novelty_metric": args.novelty_metric,
            "quantum_population": args.quantum_population,
            "quantum_eta": args.quantum_eta,
            "quantum_min_prob": args.quantum_min_prob,
            "quantum_prior_anchor": args.quantum_prior_anchor,
        },
    )
    summary_df = pd.DataFrame(per_target)
    draw_difficulty_chart(args.out_dir / "figures" / "difficulty_target_achieved.pdf", summary_df)
    print(f"wrote_rows={len(detail)} out_dir={args.out_dir}", flush=True)


if __name__ == "__main__":
    main()
