from __future__ import annotations

import argparse
import math
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "experiments" / "output_reproduction_main"
DEFAULT_PAPER_FIGS = ROOT / "paper" / "figures"

METHOD_ORDER = [
    "uniform_random",
    "dataset_prior_random",
    "positional_prior_random",
    "quantum_inspired",
    "genetic_algorithm",
    "simulated_annealing",
]
SEARCH_METHOD_ORDER = ["quantum_inspired", "genetic_algorithm", "simulated_annealing"]
METHOD_LABELS = {
    "uniform_random": "Uniform",
    "dataset_prior_random": "Dataset prior",
    "positional_prior_random": "Position prior",
    "quantum_inspired": "QI evolving prior",
    "genetic_algorithm": "GA",
    "simulated_annealing": "SA",
}
VARIANT_ORDER = ["full", "no_playability", "no_pattern", "no_path_diversity", "no_style", "no_difficulty"]
VARIANT_LABELS = {
    "full": "Full",
    "no_playability": "No playability",
    "no_pattern": "No pattern",
    "no_path_diversity": "No path diversity",
    "no_style": "No style",
    "no_difficulty": "No difficulty",
}
DATASET_LABELS = {"zelda": "Zelda", "loderunner": "Lode Runner"}
METRIC_LABELS = {
    "playability": "Playability",
    "generation_time": "Generation time (seconds)",
    "style_similarity": "Style similarity",
    "novelty": "Novelty",
    "pattern_similarity_2x2": "2x2 pattern similarity",
}
COLORS = {
    "uniform_random": colors.HexColor("#6f6f6f"),
    "dataset_prior_random": colors.HexColor("#8c564b"),
    "positional_prior_random": colors.HexColor("#ff7f0e"),
    "quantum_inspired": colors.HexColor("#0057b8"),
    "genetic_algorithm": colors.HexColor("#9467bd"),
    "simulated_annealing": colors.HexColor("#2ca02c"),
    "full": colors.HexColor("#0057b8"),
    "no_playability": colors.HexColor("#6f6f6f"),
    "no_pattern": colors.HexColor("#d62728"),
    "no_path_diversity": colors.HexColor("#2ca02c"),
    "no_style": colors.HexColor("#ff7f0e"),
    "no_difficulty": colors.HexColor("#9467bd"),
}

PAGE_W = 560
PAGE_H = 380
LEFT = 68
RIGHT = 28
TOP = 46
BOTTOM = 78


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create vector PDF paper figures from experiment CSV outputs.")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--paper-figures", type=Path, default=DEFAULT_PAPER_FIGS)
    return parser.parse_args()


def make_canvas(
    path: Path,
    title: str,
    y_label: str,
    x_label: str = "",
    *,
    y_label_mode: str = "vertical",
) -> tuple[canvas.Canvas, tuple[float, float, float, float]]:
    path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(path), pagesize=(PAGE_W, PAGE_H))
    c.setTitle(title)
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 24, title)
    c.setFont("Helvetica", 9)
    if y_label_mode == "horizontal":
        c.drawString(18, PAGE_H - TOP + 8, y_label)
    else:
        c.saveState()
        c.translate(18, (PAGE_H - TOP + BOTTOM) / 2)
        c.rotate(90)
        c.drawCentredString(0, 0, y_label)
        c.restoreState()
    if x_label:
        c.drawCentredString(PAGE_W / 2, 22, x_label)
    plot = (LEFT, BOTTOM, PAGE_W - RIGHT, PAGE_H - TOP)
    draw_axes(c, plot)
    return c, plot


def draw_axes(c: canvas.Canvas, plot: tuple[float, float, float, float]) -> None:
    left, bottom, right, top = plot
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.8)
    c.line(left, bottom, right, bottom)
    c.line(left, bottom, left, top)


def draw_y_ticks(
    c: canvas.Canvas,
    plot: tuple[float, float, float, float],
    ticks: list[float],
    y_min: float,
    y_max: float,
    label_fn=lambda value: f"{value:.2f}",
) -> None:
    left, bottom, right, top = plot
    span = max(1e-12, y_max - y_min)
    c.setFont("Helvetica", 8)
    c.setStrokeColor(colors.HexColor("#d0d0d0"))
    c.setLineWidth(0.4)
    for tick in ticks:
        y = bottom + (tick - y_min) / span * (top - bottom)
        c.line(left, y, right, y)
        c.setFillColor(colors.black)
        c.drawRightString(left - 5, y - 3, label_fn(tick))
    c.setStrokeColor(colors.black)


def bar_chart(
    path: Path,
    rows: pd.DataFrame,
    dataset: str,
    metric: str,
    *,
    log: bool = False,
    zoom: tuple[float, float] | None = None,
    show_error_bars: bool = True,
    y_label_mode: str = "vertical",
) -> None:
    title = f"{DATASET_LABELS[dataset]}: {METRIC_LABELS[metric]}"
    y_label = METRIC_LABELS[metric] + (" (log scale)" if log else "")
    c, plot = make_canvas(path, title, y_label, "Method", y_label_mode=y_label_mode)
    left, bottom, right, top = plot
    rows = rows[(rows["dataset"] == dataset) & (rows["seed"].astype(str) == "ALL")]
    rows = rows[rows["method"].isin(METHOD_ORDER)].set_index("method")
    methods = [method for method in METHOD_ORDER if method in rows.index]
    values = [float(rows.loc[method, f"{metric}_mean"]) for method in methods]
    stds = [float(rows.loc[method, f"{metric}_std"]) for method in methods]
    if log:
        y_values = [math.log10(max(v, 1e-9)) for v in values]
        y_min = math.floor(min(y_values))
        y_max = math.ceil(max(y_values))
        ticks = list(range(int(y_min), int(y_max) + 1))
        label_fn = lambda value: f"1e{int(value)}"
    elif zoom:
        y_values = values
        y_min, y_max = zoom
        ticks = [y_min + i * (y_max - y_min) / 4 for i in range(5)]
        label_fn = lambda value: f"{value:.3f}"
    else:
        y_values = values
        y_min, y_max = 0.0, 1.05 if metric == "playability" else max(values) * 1.10
        ticks = [y_min + i * (y_max - y_min) / 5 for i in range(6)]
        label_fn = lambda value: f"{value:.2f}"
    draw_y_ticks(c, plot, ticks, y_min, y_max, label_fn)
    span = max(1e-12, y_max - y_min)
    slot = (right - left) / len(methods)
    bar_w = slot * 0.56
    for idx, method in enumerate(methods):
        raw = values[idx]
        val = y_values[idx]
        x = left + idx * slot + slot * 0.22
        y = bottom + (min(max(val, y_min), y_max) - y_min) / span * (top - bottom)
        c.setFillColor(COLORS[method])
        c.rect(x, bottom, bar_w, max(0.5, y - bottom), fill=1, stroke=0)
        if show_error_bars:
            draw_error_bar(c, x + bar_w / 2, raw, stds[idx], y_min, y_max, plot, log)
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 8)
        c.drawCentredString(x + bar_w / 2, y + 5, fmt_value(raw))
        label_lines = METHOD_LABELS[method].split(" ")
        if method == "quantum_inspired":
            label_lines = ["QI evolving", "prior"]
        elif method == "dataset_prior_random":
            label_lines = ["Dataset", "prior"]
        elif method == "positional_prior_random":
            label_lines = ["Position", "prior"]
        for line_no, label in enumerate(label_lines):
            c.drawCentredString(x + bar_w / 2, bottom - 18 - line_no * 10, label)
    c.save()


def draw_error_bar(c: canvas.Canvas, x: float, raw: float, std: float, y_min: float, y_max: float, plot: tuple[float, float, float, float], log: bool) -> None:
    if std <= 0:
        return
    left, bottom, right, top = plot
    span = max(1e-12, y_max - y_min)
    if log:
        lo = math.log10(max(raw - std, 1e-9))
        hi = math.log10(max(raw + std, 1e-9))
    else:
        lo = raw - std
        hi = raw + std
    y_lo = bottom + (min(max(lo, y_min), y_max) - y_min) / span * (top - bottom)
    y_hi = bottom + (min(max(hi, y_min), y_max) - y_min) / span * (top - bottom)
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.8)
    c.line(x, y_lo, x, y_hi)
    c.line(x - 4, y_lo, x + 4, y_lo)
    c.line(x - 4, y_hi, x + 4, y_hi)


def fmt_value(value: float) -> str:
    if value != 0 and (abs(value) < 0.001 or abs(value) >= 1000):
        return f"{value:.1e}"
    return f"{value:.3f}".rstrip("0").rstrip(".")


def scatter_chart(path: Path, rows: pd.DataFrame, dataset: str) -> None:
    title = f"{DATASET_LABELS[dataset]}: novelty vs. style similarity"
    c, plot = make_canvas(path, title, "Style similarity", "Novelty")
    plot = (LEFT, BOTTOM, PAGE_W - 160, PAGE_H - TOP)
    left, bottom, right, top = plot
    old_right = PAGE_W - RIGHT
    c.setFillColor(colors.white)
    c.rect(right + 1, bottom - 5, old_right - right + 10, top - bottom + 10, fill=1, stroke=0)
    c.rect(0, 0, PAGE_W, 35, fill=1, stroke=0)
    draw_axes(c, plot)
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 9)
    c.drawCentredString((left + right) / 2, 22, "Novelty")
    rows = rows[(rows["dataset"] == dataset) & (rows["seed"].astype(str) == "ALL")]
    rows = rows[rows["method"].isin(METHOD_ORDER)]
    x_vals = rows["novelty_mean"].astype(float).tolist()
    y_vals = rows["style_similarity_mean"].astype(float).tolist()
    x_pad = max(0.025, (max(x_vals) - min(x_vals)) * 0.10)
    y_pad = max(0.025, (max(y_vals) - min(y_vals)) * 0.10)
    x_min, x_max = max(0.0, min(x_vals) - x_pad), min(1.0, max(x_vals) + x_pad)
    y_min, y_max = max(0.0, min(y_vals) - y_pad), min(1.0, max(y_vals) + y_pad)
    draw_y_ticks(c, plot, [y_min + i * (y_max - y_min) / 4 for i in range(5)], y_min, y_max, lambda v: f"{v:.2f}")
    c.setFont("Helvetica", 8)
    for i in range(5):
        x_tick = x_min + i * (x_max - x_min) / 4
        x = left + (x_tick - x_min) / (x_max - x_min) * (right - left)
        c.drawCentredString(x, bottom - 15, f"{x_tick:.2f}")
    for _, row in rows.iterrows():
        method = row["method"]
        x = left + (float(row["novelty_mean"]) - x_min) / (x_max - x_min) * (right - left)
        y = bottom + (float(row["style_similarity_mean"]) - y_min) / (y_max - y_min) * (top - bottom)
        radius = 4.8 if method == "quantum_inspired" else 4.2
        c.setFillColor(COLORS[method])
        c.circle(x, y, radius, fill=1, stroke=0)
    legend_x = right + 28
    legend_y = bottom + (top - bottom) * 0.56
    row_gap = 22
    c.setFont("Helvetica", 9)
    for idx, method in enumerate(METHOD_ORDER):
        lx = legend_x
        ly = legend_y - idx * row_gap
        c.setFillColor(COLORS[method])
        c.rect(lx, ly, 7, 7, fill=1, stroke=0)
        c.setFillColor(colors.black)
        c.drawString(lx + 13, ly, METHOD_LABELS[method])
    c.save()


def apply_right_legend_layout(
    c: canvas.Canvas,
    x_label: str,
    *,
    legend_width: float = 132,
) -> tuple[float, float, float, float]:
    plot = (LEFT, BOTTOM, PAGE_W - legend_width - RIGHT, PAGE_H - TOP)
    left, bottom, right, top = plot
    old_right = PAGE_W - RIGHT
    c.setFillColor(colors.white)
    c.rect(right + 1, bottom - 5, old_right - right + 10, top - bottom + 10, fill=1, stroke=0)
    c.rect(0, 0, PAGE_W, 35, fill=1, stroke=0)
    draw_axes(c, plot)
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 9)
    c.drawCentredString((left + right) / 2, 22, x_label)
    return plot


def ablation_curve(path: Path, rows: pd.DataFrame, dataset: str, metric: str, *, log: bool = False) -> None:
    title = f"{DATASET_LABELS[dataset]}: ablation {METRIC_LABELS[metric].lower()}"
    y_label = METRIC_LABELS[metric] + (" (log scale)" if log else "")
    c, plot = make_canvas(path, title, y_label, "Candidate budget K")
    plot = apply_right_legend_layout(c, "Candidate budget K")
    left, bottom, right, top = plot
    rows = rows[rows["dataset"] == dataset]
    values = rows[f"{metric}_mean"].astype(float).tolist()
    if log:
        transformed = [math.log10(max(v, 1e-9)) for v in values]
        y_min, y_max = math.floor(min(transformed)), math.ceil(max(transformed))
        ticks = list(range(int(y_min), int(y_max) + 1))
        label_fn = lambda value: f"1e{int(value)}"
    else:
        transformed = values
        y_min, y_max = min(transformed), max(transformed)
        pad = max(0.01, (y_max - y_min) * 0.12)
        y_min, y_max = max(0.0, y_min - pad), min(1.0, y_max + pad)
        ticks = [y_min + i * (y_max - y_min) / 4 for i in range(5)]
        label_fn = lambda value: f"{value:.3f}" if y_max - y_min < 0.2 else f"{value:.2f}"
    draw_y_ticks(c, plot, ticks, y_min, y_max, label_fn)
    ks = sorted(rows["k"].astype(int).unique())
    k_min, k_max = min(ks), max(ks)
    c.setFont("Helvetica", 8)
    for k in ks:
        x = left + (k - k_min) / (k_max - k_min) * (right - left)
        c.drawCentredString(x, bottom - 15, str(k))
    span = max(1e-12, y_max - y_min)
    for variant in VARIANT_ORDER:
        vr = rows[rows["ablation"] == variant].sort_values("k")
        points: list[tuple[float, float]] = []
        for _, row in vr.iterrows():
            raw = float(row[f"{metric}_mean"])
            yv = math.log10(max(raw, 1e-9)) if log else raw
            x = left + (int(row["k"]) - k_min) / (k_max - k_min) * (right - left)
            y = bottom + (yv - y_min) / span * (top - bottom)
            points.append((x, y))
        c.setStrokeColor(COLORS[variant])
        c.setLineWidth(1.4 if variant != "full" else 2.1)
        for p1, p2 in zip(points, points[1:]):
            c.line(p1[0], p1[1], p2[0], p2[1])
        c.setFillColor(COLORS[variant])
        for x, y in points:
            c.circle(x, y, 2.8, fill=1, stroke=0)
    draw_legend(c, right + 28, PAGE_H - 92, VARIANT_ORDER, VARIANT_LABELS, font_size=8.5, row_gap=15)
    c.save()


def budget_curve(path: Path, rows: pd.DataFrame, dataset: str, metric: str) -> None:
    title = f"{DATASET_LABELS[dataset]}: {METRIC_LABELS[metric]} by evaluation budget"
    c, plot = make_canvas(path, title, METRIC_LABELS[metric], "Fitness evaluations")
    plot = apply_right_legend_layout(c, "Fitness evaluations", legend_width=122)
    left, bottom, right, top = plot
    rows = rows[(rows["dataset"] == dataset) & (rows["seed"].astype(str) == "ALL")]
    rows = rows[rows["method"].isin(SEARCH_METHOD_ORDER)]
    values = rows[f"{metric}_mean"].astype(float).tolist()
    y_min, y_max = min(values), max(values)
    pad = max(0.01, (y_max - y_min) * 0.12)
    y_min, y_max = max(0.0, y_min - pad), min(1.0, y_max + pad)
    ticks = [y_min + i * (y_max - y_min) / 4 for i in range(5)]
    draw_y_ticks(c, plot, ticks, y_min, y_max, lambda value: f"{value:.3f}" if y_max - y_min < 0.2 else f"{value:.2f}")
    budgets = sorted(rows["fitness_budget"].astype(int).unique())
    x_min, x_max = min(budgets), max(budgets)
    c.setFont("Helvetica", 8)
    for budget in budgets:
        x = left + (budget - x_min) / (x_max - x_min) * (right - left)
        c.drawCentredString(x, bottom - 15, str(budget))
    span = max(1e-12, y_max - y_min)
    for method in SEARCH_METHOD_ORDER:
        vr = rows[rows["method"] == method].sort_values("fitness_budget")
        points: list[tuple[float, float]] = []
        for _, row in vr.iterrows():
            x = left + (int(row["fitness_budget"]) - x_min) / (x_max - x_min) * (right - left)
            y = bottom + (float(row[f"{metric}_mean"]) - y_min) / span * (top - bottom)
            points.append((x, y))
        c.setStrokeColor(COLORS[method])
        c.setLineWidth(2.0 if method == "quantum_inspired" else 1.4)
        for p1, p2 in zip(points, points[1:]):
            c.line(p1[0], p1[1], p2[0], p2[1])
        c.setFillColor(COLORS[method])
        for x, y in points:
            c.circle(x, y, 3.0, fill=1, stroke=0)
    draw_legend(c, right + 28, PAGE_H - 98, SEARCH_METHOD_ORDER, METHOD_LABELS, font_size=8.5, row_gap=16)
    c.save()


def novelty_tradeoff_chart(path: Path, rows: pd.DataFrame, dataset: str) -> None:
    title = f"{DATASET_LABELS[dataset]}: novelty-weight trade-off"
    path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(path), pagesize=(PAGE_W, PAGE_H))
    c.setTitle(title)
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 24, title)
    rows = rows[(rows["dataset"] == dataset) & (rows["seed"].astype(str) == "ALL")]
    rows = rows[rows["method"].isin(SEARCH_METHOD_ORDER)]
    metrics = ["playability", "style_similarity", "novelty"]
    panel_w = 118
    gap = 18
    bottom, top = 78, PAGE_H - 58
    left0 = 54
    weights = sorted(rows["novelty_weight"].astype(float).unique())
    x_min, x_max = min(weights), max(weights)
    for panel_idx, metric in enumerate(metrics):
        left = left0 + panel_idx * (panel_w + gap)
        right = left + panel_w
        plot = (left, bottom, right, top)
        draw_axes(c, plot)
        c.setFont("Helvetica-Bold", 8.5)
        c.drawCentredString((left + right) / 2, top + 10, METRIC_LABELS[metric])
        vals = rows[f"{metric}_mean"].astype(float).tolist()
        y_min, y_max = min(vals), max(vals)
        pad = max(0.01, (y_max - y_min) * 0.16)
        y_min, y_max = max(0.0, y_min - pad), min(1.0, y_max + pad)
        ticks = [y_min + i * (y_max - y_min) / 3 for i in range(4)]
        draw_y_ticks(c, plot, ticks, y_min, y_max, lambda value: f"{value:.2f}")
        c.setFont("Helvetica", 7)
        for weight in weights:
            x = left + (weight - x_min) / max(1e-12, x_max - x_min) * (right - left)
            c.drawCentredString(x, bottom - 14, fmt_value(weight))
        span = max(1e-12, y_max - y_min)
        for method in SEARCH_METHOD_ORDER:
            vr = rows[rows["method"] == method].sort_values("novelty_weight")
            points: list[tuple[float, float]] = []
            for _, row in vr.iterrows():
                x = left + (float(row["novelty_weight"]) - x_min) / max(1e-12, x_max - x_min) * (right - left)
                y = bottom + (float(row[f"{metric}_mean"]) - y_min) / span * (top - bottom)
                points.append((x, y))
            c.setStrokeColor(COLORS[method])
            c.setLineWidth(2.0 if method == "quantum_inspired" else 1.3)
            for p1, p2 in zip(points, points[1:]):
                c.line(p1[0], p1[1], p2[0], p2[1])
            c.setFillColor(COLORS[method])
            for x, y in points:
                c.circle(x, y, 2.6, fill=1, stroke=0)
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 9)
    c.drawCentredString(PAGE_W / 2, 22, "Novelty weight in fitness")
    draw_legend(c, PAGE_W - 96, PAGE_H - 92, SEARCH_METHOD_ORDER, METHOD_LABELS, font_size=8, row_gap=15)
    c.save()


def draw_legend(
    c: canvas.Canvas,
    x: float,
    y: float,
    keys: list[str],
    labels: dict[str, str],
    *,
    font_size: float = 7.5,
    row_gap: float = 13,
) -> None:
    c.setFont("Helvetica", font_size)
    for idx, key in enumerate(keys):
        yy = y - idx * row_gap
        c.setFillColor(COLORS[key])
        c.rect(x, yy - 2, 7, 7, fill=1, stroke=0)
        c.setFillColor(colors.black)
        c.drawString(x + 10, yy - 1, labels[key])


def main() -> int:
    args = parse_args()
    out_dir = args.out_dir if args.out_dir.is_absolute() else ROOT / args.out_dir
    paper_figures = args.paper_figures if args.paper_figures.is_absolute() else ROOT / args.paper_figures
    summary = pd.read_csv(out_dir / "combined_results_summary.csv")
    ablation_path = out_dir / "combined_ablation_summary.csv"
    budget_path = out_dir / "combined_budget_sweep_summary.csv"
    novelty_path = out_dir / "combined_novelty_sweep_summary.csv"
    ablation = pd.read_csv(ablation_path) if ablation_path.exists() else pd.DataFrame()
    budget = pd.read_csv(budget_path) if budget_path.exists() else pd.DataFrame()
    novelty = pd.read_csv(novelty_path) if novelty_path.exists() else pd.DataFrame()
    figure_dir = out_dir / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)
    paper_figures.mkdir(parents=True, exist_ok=True)
    targets = [figure_dir, paper_figures]
    for target in targets:
        for dataset in ["zelda", "loderunner"]:
            bar_chart(
                target / f"{dataset}_playability.pdf",
                summary,
                dataset,
                "playability",
                show_error_bars=False,
            )
            bar_chart(
                target / f"{dataset}_generation_time_log.pdf",
                summary,
                dataset,
                "generation_time",
                log=True,
                show_error_bars=False,
            )
            bar_chart(
                target / f"{dataset}_style_zoom.pdf",
                summary,
                dataset,
                "style_similarity",
                zoom=(0.94, 0.985),
                show_error_bars=False,
            )
            scatter_chart(target / f"{dataset}_novelty_style.pdf", summary, dataset)
            if not ablation.empty:
                ablation_curve(target / f"{dataset}_ablation_novelty.pdf", ablation, dataset, "novelty")
                ablation_curve(target / f"{dataset}_ablation_pattern.pdf", ablation, dataset, "pattern_similarity_2x2")
                ablation_curve(target / f"{dataset}_ablation_time.pdf", ablation, dataset, "generation_time", log=True)
            if not budget.empty:
                budget_curve(target / f"{dataset}_budget_playability.pdf", budget, dataset, "playability")
                budget_curve(target / f"{dataset}_budget_novelty.pdf", budget, dataset, "novelty")
                budget_curve(target / f"{dataset}_budget_style.pdf", budget, dataset, "style_similarity")
            if not novelty.empty:
                novelty_tradeoff_chart(target / f"{dataset}_novelty_weight_tradeoff.pdf", novelty, dataset)
    per_dataset = 4
    if not ablation.empty:
        per_dataset += 3
    if not budget.empty:
        per_dataset += 3
    if not novelty.empty:
        per_dataset += 1
    print(f"wrote_vector_figures={len(targets) * 2 * per_dataset}")
    print(f"paper_figures={paper_figures}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
