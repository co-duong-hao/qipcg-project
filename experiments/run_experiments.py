from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
import time
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

import numpy as np

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover
    Image = None
    ImageDraw = None
    ImageFont = None


CATEGORIES = ["path", "wall", "enemy", "trap", "door", "goal_or_exit"]
CAT_TO_ID = {name: idx for idx, name in enumerate(CATEGORIES)}
ID_TO_CAT = {idx: name for name, idx in CAT_TO_ID.items()}
CHAR_FOR_CAT = {
    "path": ".",
    "wall": "#",
    "enemy": "E",
    "trap": "T",
    "door": "D",
    "goal_or_exit": "G",
}
WALKABLE = {CAT_TO_ID[x] for x in ["path", "enemy", "trap", "door", "goal_or_exit"]}
IMPORTANT = {CAT_TO_ID["door"], CAT_TO_ID["goal_or_exit"]}
PATTERN_BINS_2X2 = len(CATEGORIES) ** 4


@dataclass(frozen=True)
class DatasetSpec:
    name: str
    path: Path
    height: int
    width: int
    kind: str
    raw_to_cat: dict[str, str]
    uses_doors: bool


@dataclass(frozen=True)
class RoomRecord:
    dataset: str
    source: str
    row: int
    col: int
    grid: np.ndarray


def dataset_specs(root: Path) -> dict[str, DatasetSpec]:
    return {
        "zelda": DatasetSpec(
            name="zelda",
            path=root / "The Legend of Zelda" / "Processed",
            height=16,
            width=11,
            kind="zelda_rooms",
            uses_doors=True,
            raw_to_cat={
                "F": "path",
                "B": "wall",
                "W": "wall",
                "M": "enemy",
                "P": "trap",
                "O": "trap",
                "D": "door",
                "S": "goal_or_exit",
                "I": "unknown",
                "-": "unknown",
            },
        ),
        "loderunner": DatasetSpec(
            name="loderunner",
            path=root / "Lode Runner" / "Processed",
            height=22,
            width=32,
            kind="fixed_levels",
            uses_doors=False,
            raw_to_cat={
                ".": "path",
                "-": "path",
                "#": "path",
                "G": "goal_or_exit",
                "M": "goal_or_exit",
                "E": "enemy",
                "B": "wall",
                "b": "wall",
            },
        ),
    }


def neighbors(h: int, w: int, r: int, c: int) -> Iterable[tuple[int, int]]:
    if r > 0:
        yield r - 1, c
    if r + 1 < h:
        yield r + 1, c
    if c > 0:
        yield r, c - 1
    if c + 1 < w:
        yield r, c + 1


def room_to_ascii(grid: np.ndarray) -> str:
    return "\n".join("".join(CHAR_FOR_CAT[ID_TO_CAT[int(v)]] for v in row) for row in grid)


def load_dataset(spec: DatasetSpec) -> tuple[list[RoomRecord], dict]:
    if spec.kind == "zelda_rooms":
        return load_zelda(spec)
    if spec.kind == "fixed_levels":
        return load_fixed_levels(spec)
    raise ValueError(f"unknown dataset kind: {spec.kind}")


def load_zelda(spec: DatasetSpec) -> tuple[list[RoomRecord], dict]:
    records: list[RoomRecord] = []
    candidates = 0
    removed = Counter()
    dimensions = []
    raw_counts = Counter()
    for path in sorted(spec.path.glob("tloz*.txt")):
        rows = [line.rstrip("\n") for line in path.read_text(encoding="utf-8").splitlines() if line.rstrip("\n")]
        h = len(rows)
        w = max(len(row) for row in rows) if rows else 0
        dimensions.append(
            {
                "file": path.name,
                "height": h,
                "width": w,
                "room_rows": h // spec.height,
                "room_cols": w // spec.width,
                "candidate_rooms": (h // spec.height) * (w // spec.width),
            }
        )
        for row in rows:
            raw_counts.update(row)
        for rr in range(0, h, spec.height):
            for cc in range(0, w, spec.width):
                if rr + spec.height > h or cc + spec.width > w:
                    continue
                candidates += 1
                raw_room = [row[cc : cc + spec.width] for row in rows[rr : rr + spec.height]]
                cats = [spec.raw_to_cat.get(ch, "unknown") for row in raw_room for ch in row]
                counts = Counter(cats)
                if len(counts) == 1:
                    removed["single_category"] += 1
                    continue
                if counts["unknown"] / len(cats) > 0.40:
                    removed["too_many_unknown"] += 1
                    continue
                if counts["path"] == 0:
                    removed["no_path"] += 1
                    continue
                ids = [CAT_TO_ID.get(cat, CAT_TO_ID["wall"]) for cat in cats]
                grid = np.array(ids, dtype=np.int16).reshape(spec.height, spec.width)
                records.append(RoomRecord(spec.name, path.name, rr // spec.height, cc // spec.width, grid))
    meta = {
        "dataset": spec.name,
        "dataset_dir": str(spec.path),
        "files": len(list(spec.path.glob("tloz*.txt"))),
        "dimensions": dimensions,
        "raw_symbol_counts": dict(raw_counts),
        "total_candidates": candidates,
        "clean_rooms": len(records),
        "removed": dict(removed),
        "room_size": [spec.height, spec.width],
        "categories": CATEGORIES,
    }
    return records, meta


def load_fixed_levels(spec: DatasetSpec) -> tuple[list[RoomRecord], dict]:
    records: list[RoomRecord] = []
    removed = Counter()
    dimensions = []
    raw_counts = Counter()
    for path in sorted(spec.path.glob("*.txt")):
        rows = [line.rstrip("\n") for line in path.read_text(encoding="utf-8").splitlines() if line.rstrip("\n")]
        h = len(rows)
        w = max(len(row) for row in rows) if rows else 0
        dimensions.append({"file": path.name, "height": h, "width": w})
        for row in rows:
            raw_counts.update(row)
        if h != spec.height or w != spec.width:
            removed["wrong_size"] += 1
            continue
        cats = [spec.raw_to_cat.get(ch, "unknown") for row in rows for ch in row]
        if any(cat == "unknown" for cat in cats):
            removed["unknown_symbol"] += 1
            continue
        ids = [CAT_TO_ID[cat] for cat in cats]
        grid = np.array(ids, dtype=np.int16).reshape(spec.height, spec.width)
        if int(np.sum(grid == CAT_TO_ID["path"])) == 0:
            removed["no_path"] += 1
            continue
        records.append(RoomRecord(spec.name, path.name, 0, 0, grid))
    meta = {
        "dataset": spec.name,
        "dataset_dir": str(spec.path),
        "files": len(list(spec.path.glob("*.txt"))),
        "dimensions": dimensions,
        "raw_symbol_counts": dict(raw_counts),
        "total_candidates": len(dimensions),
        "clean_rooms": len(records),
        "removed": dict(removed),
        "room_size": [spec.height, spec.width],
        "categories": CATEGORIES,
    }
    return records, meta


def split_records(records: list[RoomRecord], train_ratio: float, seed: int) -> tuple[list[RoomRecord], list[RoomRecord]]:
    rng = random.Random(seed)
    shuffled = list(records)
    rng.shuffle(shuffled)
    cut = max(1, min(len(shuffled) - 1, int(round(len(shuffled) * train_ratio))))
    return shuffled[:cut], shuffled[cut:]


def important_cells(grid: np.ndarray) -> list[tuple[int, int]]:
    coords = np.argwhere(np.isin(grid, list(IMPORTANT)))
    return [(int(r), int(c)) for r, c in coords]


def bfs(grid: np.ndarray, start: tuple[int, int]) -> dict[tuple[int, int], int]:
    h, w = grid.shape
    distances = {start: 0}
    q = deque([start])
    while q:
        r, c = q.popleft()
        for nr, nc in neighbors(h, w, r, c):
            if (nr, nc) in distances or int(grid[nr, nc]) not in WALKABLE:
                continue
            distances[(nr, nc)] = distances[(r, c)] + 1
            q.append((nr, nc))
    return distances


def playability_and_path(grid: np.ndarray) -> tuple[int, int]:
    cells = important_cells(grid)
    if len(cells) < 2:
        return 0, -1
    distances = bfs(grid, cells[0])
    if any(cell not in distances for cell in cells[1:]):
        return 0, -1
    return 1, max(distances[cell] for cell in cells)


def largest_walkable_component(grid: np.ndarray) -> int:
    h, w = grid.shape
    seen: set[tuple[int, int]] = set()
    best = 0
    for r in range(h):
        for c in range(w):
            if int(grid[r, c]) not in WALKABLE or (r, c) in seen:
                continue
            q = deque([(r, c)])
            seen.add((r, c))
            size = 0
            while q:
                cr, cc = q.popleft()
                size += 1
                for nr, nc in neighbors(h, w, cr, cc):
                    if (nr, nc) not in seen and int(grid[nr, nc]) in WALKABLE:
                        seen.add((nr, nc))
                        q.append((nr, nc))
            best = max(best, size)
    return best


def tile_distribution(grid: np.ndarray) -> np.ndarray:
    counts = np.bincount(grid.ravel(), minlength=len(CATEGORIES)).astype(float)
    return counts / max(1.0, counts.sum())


def entropy(grid: np.ndarray) -> float:
    counts = np.bincount(grid.ravel(), minlength=len(CATEGORIES)).astype(float)
    probs = counts[counts > 0] / counts.sum()
    return float(-(probs * np.log2(probs)).sum() / math.log2(len(CATEGORIES)))


def pattern_distribution(grid: np.ndarray) -> np.ndarray:
    h, w = grid.shape
    counts = np.zeros(PATTERN_BINS_2X2, dtype=float)
    if h < 2 or w < 2:
        return counts
    for r in range(h - 1):
        for c in range(w - 1):
            a = int(grid[r, c])
            b = int(grid[r, c + 1])
            d = int(grid[r + 1, c])
            e = int(grid[r + 1, c + 1])
            counts[((a * 6 + b) * 6 + d) * 6 + e] += 1.0
    total = counts.sum()
    return counts / total if total else counts


def style_similarity(grid: np.ndarray, global_dist: np.ndarray) -> float:
    return float(max(0.0, 1.0 - 0.5 * np.abs(tile_distribution(grid) - global_dist).sum()))


def pattern_similarity(grid: np.ndarray, benchmark_pattern_dist: np.ndarray) -> float:
    return float(max(0.0, 1.0 - 0.5 * np.abs(pattern_distribution(grid) - benchmark_pattern_dist).sum()))


def novelty(grid: np.ndarray, train_flat: np.ndarray) -> float:
    flat = grid.ravel()
    return float(np.min(np.mean(train_flat != flat, axis=1)))


def difficulty_score(grid: np.ndarray, shortest_path: int) -> float:
    h, w = grid.shape
    total = h * w
    enemy_density = float(np.mean(grid == CAT_TO_ID["enemy"]))
    trap_density = float(np.mean(grid == CAT_TO_ID["trap"]))
    door_density = float(np.mean(grid == CAT_TO_ID["door"]))
    path_norm = 0.0 if shortest_path < 0 else min(1.0, shortest_path / max(1, h + w))
    return float(min(1.0, 0.35 * path_norm + 0.30 * min(1.0, enemy_density * 10) + 0.25 * min(1.0, trap_density * 8) + 0.10 * min(1.0, door_density * 20)))


def path_diversity(grid: np.ndarray) -> float:
    h, w = grid.shape
    walkable = np.isin(grid, list(WALKABLE))
    walkable_count = int(walkable.sum())
    if walkable_count == 0:
        return 0.0
    branch = []
    for r in range(h):
        for c in range(w):
            if not walkable[r, c]:
                continue
            degree = sum(1 for nr, nc in neighbors(h, w, r, c) if walkable[nr, nc])
            branch.append(max(0, degree - 1) / 3.0)
    component = largest_walkable_component(grid) / walkable_count
    return float(0.65 * statistics.fmean(branch) + 0.35 * component)


def door_score(grid: np.ndarray, uses_doors: bool) -> float:
    if not uses_doors:
        return 0.0
    doors = int(np.sum(grid == CAT_TO_ID["door"]))
    if 2 <= doors <= 8:
        return 1.0
    if doors == 0:
        return 0.0
    return max(0.0, 1.0 - abs(doors - 5) / 10.0)


def goal_score(grid: np.ndarray) -> float:
    count = int(np.sum(grid == CAT_TO_ID["goal_or_exit"]))
    if count == 0:
        return 0.0
    return min(1.0, count / 4.0)


def evaluate_grid(grid: np.ndarray, stats_data: dict, target: float) -> dict[str, float | int]:
    playable, shortest = playability_and_path(grid)
    diff = difficulty_score(grid, shortest)
    return {
        "playability": playable,
        "shortest_path_length": shortest,
        "difficulty_score": diff,
        "target_difficulty_error": abs(diff - target),
        "tile_diversity": entropy(grid),
        "path_diversity": path_diversity(grid),
        "novelty": novelty(grid, stats_data["train_flat"]),
        "style_similarity": style_similarity(grid, stats_data["global_dist"]),
        "pattern_similarity_2x2": pattern_similarity(grid, stats_data["pattern_dist"]),
    }


def fitness(
    grid: np.ndarray,
    stats_data: dict,
    target: float,
    ablation: str = "full",
    novelty_weight: float = 0.0,
) -> float:
    playable, shortest = playability_and_path(grid)
    diff = difficulty_score(grid, shortest)
    style = style_similarity(grid, stats_data["global_dist"])
    patt = pattern_similarity(grid, stats_data["pattern_dist"])
    pdiv = path_diversity(grid)
    novelty_score = novelty(grid, stats_data["train_flat"]) if novelty_weight else 0.0
    weights = {
        "playability": 100.0,
        "style": 35.0,
        "pattern": 25.0,
        "difficulty": 25.0,
        "path_diversity": 20.0,
        "novelty": novelty_weight,
        "door": 10.0,
        "goal": 5.0,
    }
    if ablation == "no_playability":
        weights["playability"] = 0.0
    elif ablation == "no_style":
        weights["style"] = 0.0
    elif ablation == "no_pattern":
        weights["pattern"] = 0.0
    elif ablation == "no_difficulty":
        weights["difficulty"] = 0.0
    elif ablation == "no_path_diversity":
        weights["path_diversity"] = 0.0
    return float(
        weights["playability"] * playable
        + weights["style"] * style
        + weights["pattern"] * patt
        + weights["difficulty"] * (1.0 - abs(diff - target))
        + weights["path_diversity"] * pdiv
        + weights["novelty"] * novelty_score
        + weights["door"] * door_score(grid, stats_data["uses_doors"])
        + weights["goal"] * goal_score(grid)
    )


def build_stats(train: list[RoomRecord], test: list[RoomRecord], spec: DatasetSpec) -> dict:
    train_grids = np.stack([record.grid for record in train])
    test_grids = np.stack([record.grid for record in test])
    train_flat = train_grids.reshape(len(train_grids), spec.height * spec.width)
    counts = np.bincount(train_flat.ravel(), minlength=len(CATEGORIES)).astype(float)
    global_dist = counts / counts.sum()
    positional = np.zeros((spec.height, spec.width, len(CATEGORIES)), dtype=float)
    for r in range(spec.height):
        for c in range(spec.width):
            cell_counts = np.bincount(train_grids[:, r, c], minlength=len(CATEGORIES)).astype(float) + 1.0
            positional[r, c] = cell_counts / cell_counts.sum()
    pattern_dist = np.zeros(PATTERN_BINS_2X2, dtype=float)
    for grid in train_grids:
        pattern_dist += pattern_distribution(grid)
    pattern_dist = pattern_dist / max(1, len(train_grids))
    return {
        "spec": spec,
        "uses_doors": spec.uses_doors,
        "train_grids": train_grids,
        "test_grids": test_grids,
        "train_flat": train_flat,
        "global_dist": global_dist,
        "positional_prior": positional,
        "pattern_dist": pattern_dist,
    }


def sample_from_positional(rng: np.random.Generator, stats_data: dict) -> np.ndarray:
    return sample_from_probs(rng, stats_data["positional_prior"])


def sample_from_probs(rng: np.random.Generator, probs: np.ndarray) -> np.ndarray:
    h, w, _ = probs.shape
    grid = np.zeros((h, w), dtype=np.int16)
    for r in range(h):
        for c in range(w):
            grid[r, c] = int(rng.choice(len(CATEGORIES), p=probs[r, c]))
    return grid


def uniform_random(rng: np.random.Generator, stats_data: dict, target: float, params: dict) -> np.ndarray:
    h, w, _ = stats_data["positional_prior"].shape
    return rng.integers(0, len(CATEGORIES), size=(h, w), dtype=np.int16)


def dataset_prior_random(rng: np.random.Generator, stats_data: dict, target: float, params: dict) -> np.ndarray:
    h, w, _ = stats_data["positional_prior"].shape
    return rng.choice(len(CATEGORIES), size=(h, w), p=stats_data["global_dist"]).astype(np.int16)


def positional_prior_random(rng: np.random.Generator, stats_data: dict, target: float, params: dict) -> np.ndarray:
    return sample_from_positional(rng, stats_data)


def quantum_inspired(rng: np.random.Generator, stats_data: dict, target: float, params: dict) -> np.ndarray:
    budget = max(1, int(params.get("fitness_budget", params.get("k", 24))))
    population = max(1, int(params.get("quantum_population", min(8, budget))))
    iterations = max(1, int(params.get("quantum_iterations", math.ceil(budget / population))))
    eta = float(params.get("quantum_eta", 0.18))
    min_prob = float(params.get("quantum_min_prob", 0.005))
    prior_anchor = float(params.get("quantum_prior_anchor", 0.05))
    novelty_weight = float(params.get("novelty_weight", 0.0))
    ablation = params.get("ablation", "full")
    prior = stats_data["positional_prior"]
    probs = prior.copy()
    best_grid = None
    best_score = -1e18
    eye = np.eye(len(CATEGORIES), dtype=float)
    for _ in range(iterations):
        generation_best = None
        generation_score = -1e18
        for _ in range(population):
            grid = sample_from_probs(rng, probs)
            score = fitness(grid, stats_data, target, ablation, novelty_weight)
            if score > generation_score:
                generation_score = score
                generation_best = grid
            if score > best_score:
                best_score = score
                best_grid = grid
        one_hot = eye[generation_best]
        probs = probs * np.exp(eta * one_hot)
        probs = probs / probs.sum(axis=2, keepdims=True)
        if prior_anchor:
            probs = (1.0 - prior_anchor) * probs + prior_anchor * prior
        if min_prob:
            probs = np.maximum(probs, min_prob)
            probs = probs / probs.sum(axis=2, keepdims=True)
    return best_grid


def genetic_algorithm(rng: np.random.Generator, stats_data: dict, target: float, params: dict) -> np.ndarray:
    pop_size = int(params.get("ga_population", 32))
    generations = int(params.get("ga_generations", 30))
    mutation_rate = float(params.get("mutation_rate", 0.03))
    novelty_weight = float(params.get("novelty_weight", 0.0))
    population = [sample_from_positional(rng, stats_data) for _ in range(pop_size)]
    scores = [fitness(grid, stats_data, target, novelty_weight=novelty_weight) for grid in population]
    for _ in range(generations):
        order = np.argsort(scores)[::-1]
        elites = [population[int(i)].copy() for i in order[: max(2, pop_size // 4)]]
        next_pop = [elites[0].copy(), elites[1].copy()]
        while len(next_pop) < pop_size:
            a = elites[int(rng.integers(0, len(elites)))]
            b = elites[int(rng.integers(0, len(elites)))]
            mask = rng.random(a.shape) < 0.5
            child = np.where(mask, a, b).astype(np.int16)
            mutate = rng.random(child.shape) < mutation_rate
            if np.any(mutate):
                child[mutate] = rng.choice(len(CATEGORIES), size=int(mutate.sum()), p=stats_data["global_dist"])
            next_pop.append(child)
        population = next_pop
        scores = [fitness(grid, stats_data, target, novelty_weight=novelty_weight) for grid in population]
    return population[int(np.argmax(scores))]


def simulated_annealing(rng: np.random.Generator, stats_data: dict, target: float, params: dict) -> np.ndarray:
    steps = int(params.get("sa_steps", 250))
    temp = float(params.get("sa_start_temp", 8.0))
    cooling = float(params.get("sa_cooling", 0.97))
    novelty_weight = float(params.get("novelty_weight", 0.0))
    current = sample_from_positional(rng, stats_data)
    current_score = fitness(current, stats_data, target, novelty_weight=novelty_weight)
    best = current.copy()
    best_score = current_score
    h, w = current.shape
    for _ in range(steps):
        candidate = current.copy()
        changes = max(1, int(rng.poisson(2)))
        for _ in range(changes):
            r = int(rng.integers(0, h))
            c = int(rng.integers(0, w))
            candidate[r, c] = int(rng.choice(len(CATEGORIES), p=stats_data["positional_prior"][r, c]))
        score = fitness(candidate, stats_data, target, novelty_weight=novelty_weight)
        if score >= current_score or rng.random() < math.exp((score - current_score) / max(temp, 1e-9)):
            current = candidate
            current_score = score
        if score > best_score:
            best = candidate
            best_score = score
        temp *= cooling
    return best


GENERATORS: dict[str, Callable[[np.random.Generator, dict, float, dict], np.ndarray]] = {
    "uniform_random": uniform_random,
    "dataset_prior_random": dataset_prior_random,
    "positional_prior_random": positional_prior_random,
    "quantum_inspired": quantum_inspired,
    "genetic_algorithm": genetic_algorithm,
    "simulated_annealing": simulated_annealing,
}
SEARCH_METHODS = ["quantum_inspired", "genetic_algorithm", "simulated_annealing"]
METHOD_SEED_OFFSETS = {method: idx * 10007 for idx, method in enumerate(GENERATORS)}
METHOD_LABELS = {
    "uniform_random": "Uniform\nrandom",
    "dataset_prior_random": "Dataset\nprior",
    "positional_prior_random": "Position\nprior",
    "quantum_inspired": "QI evolving\nprior",
    "genetic_algorithm": "Genetic\nalgorithm",
    "simulated_annealing": "Simulated\nannealing",
}
METRIC_LABELS = {
    "playability": "Playability",
    "style_similarity": "Style similarity",
    "generation_time": "Generation time (s)",
    "novelty": "Novelty",
    "pattern_similarity_2x2": "2x2 pattern similarity",
}
METRICS = [
    "playability",
    "shortest_path_length",
    "difficulty_score",
    "target_difficulty_error",
    "tile_diversity",
    "path_diversity",
    "novelty",
    "style_similarity",
    "pattern_similarity_2x2",
    "fitness_evaluations",
    "generation_time",
    "failure_flag",
]


def stable_offset(*parts: object) -> int:
    text = "|".join(str(part) for part in parts)
    total = 0
    for idx, ch in enumerate(text):
        total = (total + (idx + 1) * ord(ch)) % 1_000_003
    return total


def method_fitness_evaluations(method: str, params: dict) -> int:
    if method in {"uniform_random", "dataset_prior_random", "positional_prior_random"}:
        return 0
    if method == "quantum_inspired":
        population = max(1, int(params.get("quantum_population", min(8, int(params.get("k", 24))))))
        iterations = max(1, int(params.get("quantum_iterations", math.ceil(int(params.get("k", 24)) / population))))
        return population * iterations
    if method == "genetic_algorithm":
        return int(params.get("ga_population", 32)) * (int(params.get("ga_generations", 30)) + 1)
    if method == "simulated_annealing":
        return int(params.get("sa_steps", 250)) + 1
    return 0


def parse_int_list(value: str) -> list[int]:
    return [int(part.strip()) for part in value.split(",") if part.strip()]


def parse_float_list(value: str) -> list[float]:
    return [float(part.strip()) for part in value.split(",") if part.strip()]


def base_search_params(args: argparse.Namespace, novelty_weight: float | None = None) -> dict:
    return {
        "k": args.k,
        "ga_population": args.ga_population,
        "ga_generations": args.ga_generations,
        "mutation_rate": args.mutation_rate,
        "sa_steps": args.sa_steps,
        "quantum_population": args.quantum_population,
        "quantum_iterations": args.quantum_iterations,
        "quantum_eta": args.quantum_eta,
        "quantum_min_prob": args.quantum_min_prob,
        "quantum_prior_anchor": args.quantum_prior_anchor,
        "novelty_weight": args.novelty_weight if novelty_weight is None else novelty_weight,
    }


def fair_budget_params(args: argparse.Namespace, method: str, budget: int, novelty_weight: float | None = None) -> dict:
    if budget < 1:
        raise ValueError(f"Fitness budget must be positive, got {budget}")
    params = base_search_params(args, novelty_weight)
    params["k"] = budget
    if method == "quantum_inspired":
        population = min(args.quantum_population, budget)
        if budget % population != 0:
            raise ValueError(f"QI budget {budget} must be divisible by population {population}")
        params["quantum_population"] = population
        params["quantum_iterations"] = budget // population
    elif method == "genetic_algorithm":
        population = min(args.ga_population, budget)
        if budget % population != 0:
            raise ValueError(f"GA budget {budget} must be divisible by population {population}")
        params["ga_population"] = population
        params["ga_generations"] = budget // population - 1
    elif method == "simulated_annealing":
        params["sa_steps"] = budget - 1
    else:
        raise ValueError(f"Budget sweep only supports search methods, got {method}")
    return params


def run_reference_rows(test: list[RoomRecord], stats_data: dict, target: float, split_seed: int) -> list[dict]:
    rows = []
    for idx, record in enumerate(test):
        metrics = evaluate_grid(record.grid, stats_data, target)
        rows.append(
            {
                "dataset": record.dataset,
                "method": "heldout_reference",
                "seed": split_seed,
                "room_index": idx,
                "source": record.source,
                "is_reference": 1,
                "target_difficulty": target,
                "generation_time": 0.0,
                "fitness_evaluations": 0,
                "failure_flag": 0,
                **metrics,
                "ascii": room_to_ascii(record.grid),
            }
        )
    return rows


def run_generation(dataset: str, stats_data: dict, methods: list[str], args: argparse.Namespace) -> list[dict]:
    rows = []
    params = base_search_params(args)
    for seed in range(args.seed_start, args.seed_start + args.seeds):
        for method in methods:
            rng = np.random.default_rng(seed * 1009 + METHOD_SEED_OFFSETS[method])
            generator = GENERATORS[method]
            fitness_evaluations = method_fitness_evaluations(method, params)
            for idx in range(args.rooms_per_method):
                start = time.perf_counter()
                failure = 0
                try:
                    grid = generator(rng, stats_data, args.target_difficulty, params)
                except Exception:
                    failure = 1
                    h, w, _ = stats_data["positional_prior"].shape
                    grid = np.full((h, w), CAT_TO_ID["wall"], dtype=np.int16)
                elapsed = time.perf_counter() - start
                metrics = evaluate_grid(grid, stats_data, args.target_difficulty)
                rows.append(
                    {
                        "dataset": dataset,
                        "method": method,
                        "seed": seed,
                        "room_index": idx,
                        "source": "generated",
                        "is_reference": 0,
                        "target_difficulty": args.target_difficulty,
                        "generation_time": elapsed,
                        "fitness_evaluations": fitness_evaluations,
                        "failure_flag": failure,
                        **metrics,
                        "ascii": room_to_ascii(grid),
                    }
                )
    return rows


def run_search_sweep(
    dataset: str,
    stats_data: dict,
    args: argparse.Namespace,
    *,
    sweep_name: str,
    budgets: list[int],
    novelty_weights: list[float],
) -> list[dict]:
    rows = []
    for seed in range(args.seed_start, args.seed_start + args.seeds):
        for method in SEARCH_METHODS:
            generator = GENERATORS[method]
            for budget in budgets:
                for novelty_weight in novelty_weights:
                    params = fair_budget_params(args, method, budget, novelty_weight)
                    fitness_evaluations = method_fitness_evaluations(method, params)
                    rng_seed = seed * 1009 + METHOD_SEED_OFFSETS[method] + stable_offset(dataset, sweep_name, budget, novelty_weight)
                    rng = np.random.default_rng(rng_seed)
                    for idx in range(args.sweep_rooms_per_cell):
                        start = time.perf_counter()
                        failure = 0
                        try:
                            grid = generator(rng, stats_data, args.target_difficulty, params)
                        except Exception:
                            failure = 1
                            h, w, _ = stats_data["positional_prior"].shape
                            grid = np.full((h, w), CAT_TO_ID["wall"], dtype=np.int16)
                        elapsed = time.perf_counter() - start
                        rows.append(
                            {
                                "dataset": dataset,
                                "sweep": sweep_name,
                                "method": method,
                                "seed": seed,
                                "room_index": idx,
                                "fitness_budget": budget,
                                "novelty_weight": novelty_weight,
                                "target_difficulty": args.target_difficulty,
                                "generation_time": elapsed,
                                "fitness_evaluations": fitness_evaluations,
                                "failure_flag": failure,
                                **evaluate_grid(grid, stats_data, args.target_difficulty),
                            }
                        )
    return rows


def summarize(rows: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for row in rows:
        grouped[(row["dataset"], row["method"], str(row["seed"]))].append(row)
        grouped[(row["dataset"], row["method"], "ALL")].append(row)
    out = []
    for (dataset, method, seed), group in sorted(grouped.items()):
        item = {"dataset": dataset, "method": method, "seed": seed, "n": len(group)}
        for metric in METRICS:
            vals = [float(row[metric]) for row in group]
            item[f"{metric}_mean"] = statistics.fmean(vals)
            item[f"{metric}_std"] = statistics.pstdev(vals) if len(vals) > 1 else 0.0
        out.append(item)
    return out


def summarize_search_sweep(rows: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, str, str, str, int, float], list[dict]] = defaultdict(list)
    for row in rows:
        key = (
            row["dataset"],
            row["sweep"],
            row["method"],
            str(row["seed"]),
            int(row["fitness_budget"]),
            float(row["novelty_weight"]),
        )
        all_key = (row["dataset"], row["sweep"], row["method"], "ALL", int(row["fitness_budget"]), float(row["novelty_weight"]))
        grouped[key].append(row)
        grouped[all_key].append(row)
    out = []
    for (dataset, sweep, method, seed, budget, novelty_weight), group in sorted(grouped.items()):
        item = {
            "dataset": dataset,
            "sweep": sweep,
            "method": method,
            "seed": seed,
            "fitness_budget": budget,
            "novelty_weight": novelty_weight,
            "n": len(group),
        }
        for metric in METRICS:
            vals = [float(row[metric]) for row in group]
            item[f"{metric}_mean"] = statistics.fmean(vals)
            item[f"{metric}_std"] = statistics.pstdev(vals) if len(vals) > 1 else 0.0
        out.append(item)
    return out


def rankdata(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg_rank = (i + 1 + j + 1) / 2.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg_rank
        i = j + 1
    return ranks


def kruskal_h(groups: list[list[float]]) -> float:
    values = [v for group in groups for v in group]
    n = len(values)
    if n == 0:
        return math.nan
    ranks = rankdata(values)
    offset = 0
    h_stat = 0.0
    for group in groups:
        group_ranks = ranks[offset : offset + len(group)]
        offset += len(group)
        h_stat += (sum(group_ranks) ** 2) / max(1, len(group))
    h_stat = 12.0 / (n * (n + 1)) * h_stat - 3 * (n + 1)
    counts = Counter(values)
    tie = 1.0 - sum(c**3 - c for c in counts.values()) / max(1, n**3 - n)
    return float(h_stat / tie) if tie > 0 else 0.0


def permutation_pvalue_kruskal(groups: list[list[float]], permutations: int, seed: int) -> tuple[float, float | str]:
    if any(len(group) == 0 for group in groups):
        return math.nan, "not_applicable"
    observed = kruskal_h(groups)
    if observed == 0.0:
        return observed, 1.0
    values = [v for group in groups for v in group]
    sizes = [len(group) for group in groups]
    rng = random.Random(seed)
    exceed = 0
    for _ in range(permutations):
        shuffled = list(values)
        rng.shuffle(shuffled)
        perm_groups = []
        offset = 0
        for size in sizes:
            perm_groups.append(shuffled[offset : offset + size])
            offset += size
        if kruskal_h(perm_groups) >= observed:
            exceed += 1
    return observed, (exceed + 1) / (permutations + 1)


def mann_whitney_u(a: list[float], b: list[float]) -> float:
    ranks = rankdata(a + b)
    rank_a = sum(ranks[: len(a)])
    return rank_a - len(a) * (len(a) + 1) / 2.0


def permutation_pvalue_pair(a: list[float], b: list[float], permutations: int, seed: int) -> tuple[float, float | str]:
    if not a or not b:
        return math.nan, "not_applicable"
    observed = mann_whitney_u(a, b)
    n_a = len(a)
    values = a + b
    if len(set(values)) <= 1:
        return observed, 1.0
    center = n_a * len(b) / 2.0
    obs_dist = abs(observed - center)
    rng = random.Random(seed)
    exceed = 0
    for _ in range(permutations):
        shuffled = list(values)
        rng.shuffle(shuffled)
        stat = mann_whitney_u(shuffled[:n_a], shuffled[n_a:])
        if abs(stat - center) >= obs_dist:
            exceed += 1
    return observed, (exceed + 1) / (permutations + 1)


def cliffs_delta(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return math.nan
    more = 0
    less = 0
    for x in a:
        for y in b:
            if x > y:
                more += 1
            elif x < y:
                less += 1
    return (more - less) / (len(a) * len(b))


def add_holm_bonferroni(rows: list[dict]) -> list[dict]:
    numeric: list[tuple[int, float]] = []
    for idx, row in enumerate(rows):
        try:
            p_value = float(row["p_value"])
        except (TypeError, ValueError):
            row["p_value_holm"] = row["p_value"]
            row["significant_holm_0_05"] = "not_applicable"
            continue
        if math.isnan(p_value):
            row["p_value_holm"] = "not_applicable"
            row["significant_holm_0_05"] = "not_applicable"
            continue
        numeric.append((idx, p_value))

    m = len(numeric)
    running = 0.0
    for rank, (idx, p_value) in enumerate(sorted(numeric, key=lambda item: item[1]), start=1):
        adjusted = min(1.0, (m - rank + 1) * p_value)
        running = max(running, adjusted)
        rows[idx]["p_value_holm"] = running
        rows[idx]["significant_holm_0_05"] = running <= 0.05
    return rows


def statistical_tests(summary_rows: list[dict], permutations: int, seed: int) -> list[dict]:
    methods = [m for m in GENERATORS if m != "heldout_reference"]
    generated = [row for row in summary_rows if row["seed"] != "ALL" and row["method"] in methods]
    datasets = sorted({row["dataset"] for row in generated})
    metric_names = [m for m in METRICS if m not in {"failure_flag"}]
    out = []
    for dataset in datasets:
        for metric in metric_names:
            by_method = {
                method: [float(row[f"{metric}_mean"]) for row in generated if row["dataset"] == dataset and row["method"] == method]
                for method in methods
            }
            groups = [by_method[method] for method in methods]
            stat, pval = permutation_pvalue_kruskal(groups, permutations, seed + stable_offset(dataset, metric))
            out.append(
                {
                    "dataset": dataset,
                    "test": "kruskal_wallis_permutation_seed_means",
                    "metric": metric,
                    "method_a": "ALL",
                    "method_b": "ALL",
                    "statistic": stat,
                    "p_value": pval,
                    "effect_size": "",
                    "n_a": "",
                    "n_b": "",
                }
            )
            q = by_method.get("quantum_inspired", [])
            for method in methods:
                if method == "quantum_inspired":
                    continue
                stat, p_pair = permutation_pvalue_pair(q, by_method[method], permutations, seed + stable_offset(dataset, metric, method))
                out.append(
                    {
                        "dataset": dataset,
                        "test": "mann_whitney_permutation_vs_quantum_seed_means",
                        "metric": metric,
                        "method_a": "quantum_inspired",
                        "method_b": method,
                        "statistic": stat,
                        "p_value": p_pair,
                        "effect_size": cliffs_delta(q, by_method[method]),
                        "n_a": len(q),
                        "n_b": len(by_method[method]),
                    }
                )
    return add_holm_bonferroni(out)


def write_csv(path: Path, rows: list[dict], include_ascii: bool = True) -> None:
    if not rows:
        return
    keys = list(rows[0].keys())
    if not include_ascii:
        keys = [key for key in keys if key != "ascii"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in keys})


def write_json(path: Path, data) -> None:
    def default(obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (np.integer, np.floating)):
            return obj.item()
        raise TypeError(type(obj).__name__)

    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=default), encoding="utf-8")


def write_samples(out_dir: Path, rows: list[dict], count: int = 5) -> None:
    samples = out_dir / "samples"
    samples.mkdir(parents=True, exist_ok=True)
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if int(row["is_reference"]) == 0:
            grouped[row["method"]].append(row)
    for method, group in grouped.items():
        ranked = sorted(group, key=lambda r: (float(r["playability"]), float(r["pattern_similarity_2x2"]), -float(r["target_difficulty_error"])), reverse=True)
        for idx, row in enumerate(ranked[:count]):
            text = "\n".join(
                [
                    f"dataset={row['dataset']}",
                    f"method={method}",
                    f"seed={row['seed']}",
                    f"room_index={row['room_index']}",
                    f"playability={row['playability']}",
                    f"novelty={float(row['novelty']):.4f}",
                    f"style_similarity={float(row['style_similarity']):.4f}",
                    "",
                    row["ascii"],
                    "",
                ]
            )
            (samples / f"{method}_{idx + 1}.txt").write_text(text, encoding="utf-8")


def font():
    return ImageFont.load_default() if ImageFont else None


def draw_bar_chart(path: Path, title: str, rows: list[dict], metric: str, log: bool = False, zoom: tuple[float, float] | None = None) -> None:
    if Image is None:
        return
    all_rows = [r for r in rows if r["seed"] == "ALL" and r["method"] in GENERATORS]
    methods = [m for m in GENERATORS if any(r["method"] == m for r in all_rows)]
    by_method = {r["method"]: r for r in all_rows}
    width, height = 1300, 760
    left, top, bottom, right = 140, 90, 210, 80
    plot_w, plot_h = width - left - right, height - top - bottom
    values = [float(by_method[m][f"{metric}_mean"]) for m in methods]
    std_values = [float(by_method[m].get(f"{metric}_std", 0.0)) for m in methods]
    if log:
        transformed = [math.log10(max(v, 1e-9)) for v in values]
        ymin, ymax = min(transformed), max(transformed)
    elif zoom:
        ymin, ymax = zoom
        transformed = values
    else:
        transformed = values
        ymin, ymax = 0.0, max(values) * 1.08 if values else 1.0
    span = max(1e-9, ymax - ymin)
    image = Image.new("RGB", (width, height), "white")
    d = ImageDraw.Draw(image)
    f = font()
    y_label = METRIC_LABELS.get(metric, metric.replace("_", " "))
    if log:
        y_label += " (log10 scale)"
    d.text((width // 2 - len(title) * 3, 28), title, fill="black", font=f)
    d.text((20, top + 12), y_label, fill="black", font=f)
    d.line((left, top, left, top + plot_h), fill="black", width=2)
    d.line((left, top + plot_h, left + plot_w, top + plot_h), fill="black", width=2)
    colors = {
        "quantum_inspired": "#1f77b4",
        "genetic_algorithm": "#9467bd",
        "simulated_annealing": "#2ca02c",
        "positional_prior_random": "#ff7f0e",
        "dataset_prior_random": "#8c564b",
        "uniform_random": "#7f7f7f",
    }
    bar_w = plot_w / max(1, len(methods)) * 0.55
    for i, method in enumerate(methods):
        raw = values[i]
        val = transformed[i]
        x = left + (i + 0.25) * plot_w / len(methods)
        val_for_plot = min(max(val, ymin), ymax)
        h = (val_for_plot - ymin) / span * plot_h
        y = top + plot_h - h
        d.rectangle((x, y, x + bar_w, top + plot_h), fill=colors.get(method, "#999999"))
        err = std_values[i]
        if log:
            hi_raw = max(raw + err, 1e-9)
            lo_raw = max(raw - err, 1e-9)
            y_hi = top + plot_h - (min(max(math.log10(hi_raw), ymin), ymax) - ymin) / span * plot_h
            y_lo = top + plot_h - (min(max(math.log10(lo_raw), ymin), ymax) - ymin) / span * plot_h
        else:
            y_hi = top + plot_h - (min(max(raw + err, ymin), ymax) - ymin) / span * plot_h
            y_lo = top + plot_h - (min(max(raw - err, ymin), ymax) - ymin) / span * plot_h
        x_mid = x + bar_w / 2
        d.line((x_mid, y_hi, x_mid, y_lo), fill="black", width=2)
        d.line((x_mid - 7, y_hi, x_mid + 7, y_hi), fill="black", width=2)
        d.line((x_mid - 7, y_lo, x_mid + 7, y_lo), fill="black", width=2)
        d.text((x, y - 16), f"{raw:.3g}", fill="black", font=f)
        label_lines = METHOD_LABELS.get(method, method.replace("_", " ")).split("\n")
        for line_idx, label in enumerate(label_lines):
            d.text((x - 8, top + plot_h + 20 + line_idx * 16), label, fill="black", font=f)
    d.text((left + plot_w // 2 - 35, height - 42), "Method", fill="black", font=f)
    image.save(path)


def draw_scatter(path: Path, rows: list[dict]) -> None:
    if Image is None:
        return
    all_rows = [r for r in rows if r["seed"] == "ALL" and r["method"] in GENERATORS]
    width, height = 1200, 800
    left, top, bottom, right = 120, 80, 100, 260
    plot_w, plot_h = width - left - right, height - top - bottom
    image = Image.new("RGB", (width, height), "white")
    d = ImageDraw.Draw(image)
    f = font()
    d.text((430, 28), "Novelty vs. style similarity", fill="black", font=f)
    d.text((left + plot_w // 2 - 35, height - 42), "Novelty", fill="black", font=f)
    d.text((18, top + 12), "Style similarity", fill="black", font=f)
    d.line((left, top, left, top + plot_h), fill="black", width=2)
    d.line((left, top + plot_h, left + plot_w, top + plot_h), fill="black", width=2)
    colors = {
        "quantum_inspired": "#0047AB",
        "genetic_algorithm": "#9467bd",
        "simulated_annealing": "#2ca02c",
        "positional_prior_random": "#ff7f0e",
        "dataset_prior_random": "#8c564b",
        "uniform_random": "#7f7f7f",
    }
    for row in all_rows:
        x = left + float(row["novelty_mean"]) * plot_w
        y = top + (1.0 - float(row["style_similarity_mean"])) * plot_h
        method = row["method"]
        radius = 10 if method == "quantum_inspired" else 7
        d.ellipse((x - radius, y - radius, x + radius, y + radius), fill=colors.get(method, "#888888"), outline="black")
        d.text((x + 12, y - 8), METHOD_LABELS.get(method, method.replace("_", " ")).replace("\n", " "), fill="black", font=f)
    image.save(path)


def write_figures(out_dir: Path, summary_rows: list[dict]) -> None:
    figures = out_dir / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    for dataset in sorted({r["dataset"] for r in summary_rows}):
        rows = [r for r in summary_rows if r["dataset"] == dataset]
        draw_bar_chart(figures / f"{dataset}_playability.png", f"{dataset}: playability", rows, "playability")
        draw_bar_chart(figures / f"{dataset}_generation_time_log.png", f"{dataset}: generation time (log)", rows, "generation_time", log=True)
        draw_bar_chart(figures / f"{dataset}_style_zoom.png", f"{dataset}: style similarity (zoomed)", rows, "style_similarity", zoom=(0.94, 0.98))
        draw_scatter(figures / f"{dataset}_novelty_style.png", rows)


def draw_ablation_curve(path: Path, title: str, rows: list[dict], metric: str, log: bool = False) -> None:
    if Image is None or not rows:
        return
    width, height = 1200, 760
    left, top, bottom, right = 140, 90, 120, 260
    plot_w, plot_h = width - left - right, height - top - bottom
    variants = ["full", "no_playability", "no_pattern", "no_path_diversity", "no_style", "no_difficulty"]
    colors = {
        "full": "#0047AB",
        "no_playability": "#7f7f7f",
        "no_pattern": "#d62728",
        "no_path_diversity": "#2ca02c",
        "no_style": "#ff7f0e",
        "no_difficulty": "#9467bd",
    }
    values = [float(row[f"{metric}_mean"]) for row in rows]
    if log:
        values_plot = [math.log10(max(v, 1e-9)) for v in values]
        y_min, y_max = min(values_plot), max(values_plot)
    else:
        values_plot = values
        y_min, y_max = min(values_plot), max(values_plot)
        pad = max(0.01, (y_max - y_min) * 0.08)
        y_min = max(0.0, y_min - pad)
        y_max = y_max + pad
    span = max(1e-9, y_max - y_min)
    ks = sorted({int(row["k"]) for row in rows})
    k_min, k_max = min(ks), max(ks)
    image = Image.new("RGB", (width, height), "white")
    d = ImageDraw.Draw(image)
    f = font()
    d.text((width // 2 - len(title) * 3, 28), title, fill="black", font=f)
    y_label = METRIC_LABELS.get(metric, metric.replace("_", " "))
    if log:
        y_label += " (log10 scale)"
    d.text((20, top + 12), y_label, fill="black", font=f)
    d.text((left + plot_w // 2 - 45, height - 42), "Candidate budget K", fill="black", font=f)
    d.line((left, top, left, top + plot_h), fill="black", width=2)
    d.line((left, top + plot_h, left + plot_w, top + plot_h), fill="black", width=2)
    for k in ks:
        x = left + (k - k_min) / max(1, k_max - k_min) * plot_w
        d.line((x, top + plot_h, x, top + plot_h + 6), fill="black", width=1)
        d.text((x - 8, top + plot_h + 14), str(k), fill="black", font=f)
    for variant in variants:
        points = []
        for row in sorted([r for r in rows if r["ablation"] == variant], key=lambda r: int(r["k"])):
            x = left + (int(row["k"]) - k_min) / max(1, k_max - k_min) * plot_w
            raw_y = float(row[f"{metric}_mean"])
            y_value = math.log10(max(raw_y, 1e-9)) if log else raw_y
            y = top + plot_h - (y_value - y_min) / span * plot_h
            points.append((x, y))
        if len(points) >= 2:
            d.line(points, fill=colors.get(variant, "#555555"), width=3)
        for x, y in points:
            d.ellipse((x - 4, y - 4, x + 4, y + 4), fill=colors.get(variant, "#555555"), outline="black")
    legend_x = left + plot_w + 28
    for idx, variant in enumerate(variants):
        y = top + idx * 28
        d.rectangle((legend_x, y, legend_x + 16, y + 16), fill=colors.get(variant, "#555555"))
        d.text((legend_x + 24, y), variant.replace("_", " "), fill="black", font=f)
    image.save(path)


def write_ablation_figures(out_dir: Path, ablation_summary: list[dict]) -> None:
    if not ablation_summary:
        return
    figures = out_dir / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    for dataset in sorted({r["dataset"] for r in ablation_summary}):
        rows = [r for r in ablation_summary if r["dataset"] == dataset]
        draw_ablation_curve(figures / f"{dataset}_ablation_novelty.png", f"{dataset}: ablation novelty", rows, "novelty")
        draw_ablation_curve(figures / f"{dataset}_ablation_pattern.png", f"{dataset}: ablation pattern similarity", rows, "pattern_similarity_2x2")
        draw_ablation_curve(figures / f"{dataset}_ablation_time.png", f"{dataset}: ablation generation time", rows, "generation_time", log=True)


def run_ablation(dataset: str, stats_data: dict, args: argparse.Namespace) -> list[dict]:
    variants = ["full", "no_playability", "no_pattern", "no_path_diversity", "no_style", "no_difficulty"]
    ks = [8, 16, 24, 32, 64]
    rows = []
    for variant in variants:
        for k in ks:
            rng = np.random.default_rng(args.seed_start * 1231 + k + stable_offset(dataset, variant))
            params = {"k": k, "ablation": variant}
            fitness_evaluations = method_fitness_evaluations("quantum_inspired", params)
            for idx in range(args.ablation_rooms_per_cell):
                start = time.perf_counter()
                grid = quantum_inspired(rng, stats_data, args.target_difficulty, params)
                elapsed = time.perf_counter() - start
                rows.append(
                    {
                        "dataset": dataset,
                        "ablation": variant,
                        "k": k,
                        "room_index": idx,
                        "generation_time": elapsed,
                        "fitness_evaluations": fitness_evaluations,
                        **evaluate_grid(grid, stats_data, args.target_difficulty),
                    }
                )
    return rows


def summarize_ablation(rows: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, str, int], list[dict]] = defaultdict(list)
    for row in rows:
        grouped[(row["dataset"], row["ablation"], int(row["k"]))].append(row)
    out = []
    for (dataset, variant, k), group in sorted(grouped.items()):
        item = {"dataset": dataset, "ablation": variant, "k": k, "n": len(group)}
        for metric in ["playability", "difficulty_score", "target_difficulty_error", "path_diversity", "novelty", "style_similarity", "pattern_similarity_2x2", "fitness_evaluations", "generation_time"]:
            vals = [float(row[metric]) for row in group]
            item[f"{metric}_mean"] = statistics.fmean(vals)
            item[f"{metric}_std"] = statistics.pstdev(vals) if len(vals) > 1 else 0.0
        out.append(item)
    return out


def process_dataset(
    spec: DatasetSpec,
    args: argparse.Namespace,
    root_out: Path,
    methods: list[str],
) -> tuple[list[dict], list[dict], list[dict], list[dict], list[dict], list[dict], list[dict], list[dict], list[dict]]:
    records, meta = load_dataset(spec)
    train, test = split_records(records, args.train_ratio, args.split_seed)
    stats_data = build_stats(train, test, spec)
    out_dir = root_out / spec.name
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        out_dir / "benchmark_stats.json",
        {
            **meta,
            "train_rooms": len(train),
            "test_rooms": len(test),
            "train_ratio": args.train_ratio,
            "split_seed": args.split_seed,
            "global_distribution_train": {ID_TO_CAT[idx]: float(v) for idx, v in enumerate(stats_data["global_dist"])},
        },
    )
    write_json(out_dir / "split_metadata.json", {"train": [r.source for r in train], "test": [r.source for r in test]})
    detail = run_reference_rows(test, stats_data, args.target_difficulty, args.split_seed)
    detail += run_generation(spec.name, stats_data, methods, args)
    summary = summarize(detail)
    tests = statistical_tests(summary, args.stat_permutations, args.split_seed)
    write_csv(out_dir / "results_detailed.csv", detail)
    write_csv(out_dir / "results_summary.csv", summary, include_ascii=False)
    write_csv(out_dir / "statistical_tests.csv", tests, include_ascii=False)
    write_samples(out_dir, detail)
    write_figures(out_dir, summary)
    ablation_detail: list[dict] = []
    ablation_summary: list[dict] = []
    if not args.skip_ablation:
        ablation_detail = run_ablation(spec.name, stats_data, args)
        ablation_summary = summarize_ablation(ablation_detail)
        write_csv(out_dir / "ablation_detailed.csv", ablation_detail, include_ascii=False)
        write_csv(out_dir / "ablation_summary.csv", ablation_summary, include_ascii=False)
    budget_detail: list[dict] = []
    budget_summary: list[dict] = []
    novelty_detail: list[dict] = []
    novelty_summary: list[dict] = []
    if args.run_budget_sweep:
        budget_detail = run_search_sweep(
            spec.name,
            stats_data,
            args,
            sweep_name="budget",
            budgets=parse_int_list(args.budget_sweep_values),
            novelty_weights=[args.novelty_weight],
        )
        budget_summary = summarize_search_sweep(budget_detail)
        write_csv(out_dir / "budget_sweep_detailed.csv", budget_detail, include_ascii=False)
        write_csv(out_dir / "budget_sweep_summary.csv", budget_summary, include_ascii=False)
    if args.run_novelty_sweep:
        novelty_detail = run_search_sweep(
            spec.name,
            stats_data,
            args,
            sweep_name="novelty_weight",
            budgets=[args.k],
            novelty_weights=parse_float_list(args.novelty_sweep_weights),
        )
        novelty_summary = summarize_search_sweep(novelty_detail)
        write_csv(out_dir / "novelty_sweep_detailed.csv", novelty_detail, include_ascii=False)
        write_csv(out_dir / "novelty_sweep_summary.csv", novelty_summary, include_ascii=False)
    return detail, summary, tests, ablation_summary, ablation_detail, budget_summary, budget_detail, novelty_summary, novelty_detail


def combine_outputs(
    root_out: Path,
    all_detail: list[dict],
    all_summary: list[dict],
    all_tests: list[dict],
    all_ablation_summary: list[dict],
    all_ablation_detail: list[dict],
    all_budget_summary: list[dict],
    all_budget_detail: list[dict],
    all_novelty_summary: list[dict],
    all_novelty_detail: list[dict],
) -> None:
    write_csv(root_out / "combined_results_detailed.csv", all_detail)
    write_csv(root_out / "combined_results_summary.csv", all_summary, include_ascii=False)
    write_csv(root_out / "combined_statistical_tests.csv", all_tests, include_ascii=False)
    write_figures(root_out, all_summary)
    if all_ablation_summary:
        write_csv(root_out / "combined_ablation_summary.csv", all_ablation_summary, include_ascii=False)
        write_ablation_figures(root_out, all_ablation_summary)
    if all_ablation_detail:
        write_csv(root_out / "combined_ablation_detailed.csv", all_ablation_detail, include_ascii=False)
    if all_budget_summary:
        write_csv(root_out / "combined_budget_sweep_summary.csv", all_budget_summary, include_ascii=False)
    if all_budget_detail:
        write_csv(root_out / "combined_budget_sweep_detailed.csv", all_budget_detail, include_ascii=False)
    if all_novelty_summary:
        write_csv(root_out / "combined_novelty_sweep_summary.csv", all_novelty_summary, include_ascii=False)
    if all_novelty_detail:
        write_csv(root_out / "combined_novelty_sweep_detailed.csv", all_novelty_detail, include_ascii=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Multi-dataset quantum-inspired PCG experiment runner.")
    parser.add_argument("--vglc-root", type=Path, default=Path("TheVGLC"))
    parser.add_argument("--datasets", default="zelda,loderunner")
    parser.add_argument("--out-dir", type=Path, default=Path("experiments") / "output_reproduction")
    parser.add_argument("--rooms-per-method", type=int, default=500)
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument("--seed-start", type=int, default=42)
    parser.add_argument("--split-seed", type=int, default=2026)
    parser.add_argument("--train-ratio", type=float, default=0.8)
    parser.add_argument("--target-difficulty", type=float, default=0.5)
    parser.add_argument("--methods", default="uniform_random,dataset_prior_random,positional_prior_random,quantum_inspired,genetic_algorithm,simulated_annealing")
    parser.add_argument("--k", type=int, default=24)
    parser.add_argument("--quantum-population", type=int, default=8)
    parser.add_argument("--quantum-iterations", type=int, default=3)
    parser.add_argument("--quantum-eta", type=float, default=0.18)
    parser.add_argument("--quantum-min-prob", type=float, default=0.005)
    parser.add_argument("--quantum-prior-anchor", type=float, default=0.05)
    parser.add_argument("--novelty-weight", type=float, default=0.0)
    parser.add_argument("--ga-population", type=int, default=8)
    parser.add_argument("--ga-generations", type=int, default=2)
    parser.add_argument("--mutation-rate", type=float, default=0.03)
    parser.add_argument("--sa-steps", type=int, default=23)
    parser.add_argument("--ablation-rooms-per-cell", type=int, default=200)
    parser.add_argument("--stat-permutations", type=int, default=999)
    parser.add_argument("--skip-ablation", action="store_true")
    parser.add_argument("--ablation-only", action="store_true", help="Run only ablation outputs for the selected datasets.")
    parser.add_argument("--run-budget-sweep", action="store_true", help="Run QI/GA/SA quality curves over multiple fitness budgets.")
    parser.add_argument("--run-novelty-sweep", action="store_true", help="Run QI/GA/SA trade-off curves over novelty fitness weights.")
    parser.add_argument("--sweep-only", action="store_true", help="Run only the enabled sweep outputs without regenerating main or ablation outputs.")
    parser.add_argument("--sweep-rooms-per-cell", type=int, default=200)
    parser.add_argument("--budget-sweep-values", default="8,16,24,32,64")
    parser.add_argument("--novelty-sweep-weights", default="0,25,50,100")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    specs = dataset_specs(args.vglc_root)
    datasets = [x.strip() for x in args.datasets.split(",") if x.strip()]
    methods = [x.strip() for x in args.methods.split(",") if x.strip()]
    unknown_datasets = [name for name in datasets if name not in specs]
    unknown_methods = [name for name in methods if name not in GENERATORS]
    if unknown_datasets:
        raise SystemExit(f"Unknown datasets: {unknown_datasets}")
    if unknown_methods:
        raise SystemExit(f"Unknown methods: {unknown_methods}")
    if not args.sweep_only:
        write_json(
            args.out_dir / "run_config_main.json",
            {
                "datasets": datasets,
                "rooms_per_method": args.rooms_per_method,
                "seeds": args.seeds,
                "seed_start": args.seed_start,
                "split_seed": args.split_seed,
                "train_ratio": args.train_ratio,
                "target_difficulty": args.target_difficulty,
                "methods": methods,
                "k": args.k,
                "quantum_population": args.quantum_population,
                "quantum_iterations": args.quantum_iterations,
                "quantum_eta": args.quantum_eta,
                "quantum_min_prob": args.quantum_min_prob,
                "quantum_prior_anchor": args.quantum_prior_anchor,
                "novelty_weight": args.novelty_weight,
                "ga_population": args.ga_population,
                "ga_generations": args.ga_generations,
                "mutation_rate": args.mutation_rate,
                "sa_steps": args.sa_steps,
                "stat_permutations": args.stat_permutations,
                "run_budget_sweep": args.run_budget_sweep,
                "run_novelty_sweep": args.run_novelty_sweep,
                "sweep_rooms_per_cell": args.sweep_rooms_per_cell,
                "budget_sweep_values": parse_int_list(args.budget_sweep_values),
                "novelty_sweep_weights": parse_float_list(args.novelty_sweep_weights),
            },
        )
    if not args.skip_ablation and not args.sweep_only:
        write_json(args.out_dir / "run_config_ablation.json", {"ablation_rooms_per_cell": args.ablation_rooms_per_cell, "k_values": [8, 16, 24, 32, 64]})
    if args.run_budget_sweep:
        write_json(
            args.out_dir / "run_config_budget_sweep.json",
            {
                "sweep_rooms_per_cell": args.sweep_rooms_per_cell,
                "methods": SEARCH_METHODS,
                "fitness_budgets": parse_int_list(args.budget_sweep_values),
                "novelty_weight": args.novelty_weight,
                "seeds": args.seeds,
                "seed_start": args.seed_start,
            },
        )
    if args.run_novelty_sweep:
        write_json(
            args.out_dir / "run_config_novelty_sweep.json",
            {
                "sweep_rooms_per_cell": args.sweep_rooms_per_cell,
                "methods": SEARCH_METHODS,
                "fitness_budget": args.k,
                "novelty_weights": parse_float_list(args.novelty_sweep_weights),
                "seeds": args.seeds,
                "seed_start": args.seed_start,
            },
        )
    if args.sweep_only:
        if not args.run_budget_sweep and not args.run_novelty_sweep:
            raise SystemExit("--sweep-only requires --run-budget-sweep and/or --run-novelty-sweep")
        all_budget_detail: list[dict] = []
        all_budget_summary: list[dict] = []
        all_novelty_detail: list[dict] = []
        all_novelty_summary: list[dict] = []
        for dataset in datasets:
            print(f"running sweeps dataset={dataset}", flush=True)
            records, _ = load_dataset(specs[dataset])
            train, test = split_records(records, args.train_ratio, args.split_seed)
            stats_data = build_stats(train, test, specs[dataset])
            out_dir = args.out_dir / dataset
            out_dir.mkdir(parents=True, exist_ok=True)
            if args.run_budget_sweep:
                budget_detail = run_search_sweep(
                    dataset,
                    stats_data,
                    args,
                    sweep_name="budget",
                    budgets=parse_int_list(args.budget_sweep_values),
                    novelty_weights=[args.novelty_weight],
                )
                budget_summary = summarize_search_sweep(budget_detail)
                write_csv(out_dir / "budget_sweep_detailed.csv", budget_detail, include_ascii=False)
                write_csv(out_dir / "budget_sweep_summary.csv", budget_summary, include_ascii=False)
                all_budget_detail.extend(budget_detail)
                all_budget_summary.extend(budget_summary)
                print(f"dataset={dataset} budget_sweep_rows={len(budget_detail)}", flush=True)
            if args.run_novelty_sweep:
                novelty_detail = run_search_sweep(
                    dataset,
                    stats_data,
                    args,
                    sweep_name="novelty_weight",
                    budgets=[args.k],
                    novelty_weights=parse_float_list(args.novelty_sweep_weights),
                )
                novelty_summary = summarize_search_sweep(novelty_detail)
                write_csv(out_dir / "novelty_sweep_detailed.csv", novelty_detail, include_ascii=False)
                write_csv(out_dir / "novelty_sweep_summary.csv", novelty_summary, include_ascii=False)
                all_novelty_detail.extend(novelty_detail)
                all_novelty_summary.extend(novelty_summary)
                print(f"dataset={dataset} novelty_sweep_rows={len(novelty_detail)}", flush=True)
        if all_budget_summary:
            write_csv(args.out_dir / "combined_budget_sweep_summary.csv", all_budget_summary, include_ascii=False)
        if all_budget_detail:
            write_csv(args.out_dir / "combined_budget_sweep_detailed.csv", all_budget_detail, include_ascii=False)
        if all_novelty_summary:
            write_csv(args.out_dir / "combined_novelty_sweep_summary.csv", all_novelty_summary, include_ascii=False)
        if all_novelty_detail:
            write_csv(args.out_dir / "combined_novelty_sweep_detailed.csv", all_novelty_detail, include_ascii=False)
        print(f"output_dir={args.out_dir.resolve()}", flush=True)
        return
    if args.ablation_only:
        all_ablation_detail: list[dict] = []
        all_ablation_summary: list[dict] = []
        for dataset in datasets:
            print(f"running ablation dataset={dataset}", flush=True)
            records, _ = load_dataset(specs[dataset])
            train, test = split_records(records, args.train_ratio, args.split_seed)
            stats_data = build_stats(train, test, specs[dataset])
            out_dir = args.out_dir / dataset
            out_dir.mkdir(parents=True, exist_ok=True)
            ablation_detail = run_ablation(dataset, stats_data, args)
            ablation_summary = summarize_ablation(ablation_detail)
            write_csv(out_dir / "ablation_detailed.csv", ablation_detail, include_ascii=False)
            write_csv(out_dir / "ablation_summary.csv", ablation_summary, include_ascii=False)
            all_ablation_detail.extend(ablation_detail)
            all_ablation_summary.extend(ablation_summary)
            print(f"dataset={dataset} ablation_rows={len(ablation_detail)}", flush=True)
        write_csv(args.out_dir / "combined_ablation_detailed.csv", all_ablation_detail, include_ascii=False)
        write_csv(args.out_dir / "combined_ablation_summary.csv", all_ablation_summary, include_ascii=False)
        write_ablation_figures(args.out_dir, all_ablation_summary)
        print(f"output_dir={args.out_dir.resolve()}", flush=True)
        return
    all_detail: list[dict] = []
    all_summary: list[dict] = []
    all_tests: list[dict] = []
    all_ablation_summary: list[dict] = []
    all_ablation_detail: list[dict] = []
    all_budget_summary: list[dict] = []
    all_budget_detail: list[dict] = []
    all_novelty_summary: list[dict] = []
    all_novelty_detail: list[dict] = []
    for dataset in datasets:
        print(f"running dataset={dataset}", flush=True)
        (
            detail,
            summary,
            tests,
            ablation_summary,
            ablation_detail,
            budget_summary,
            budget_detail,
            novelty_summary,
            novelty_detail,
        ) = process_dataset(specs[dataset], args, args.out_dir, methods)
        all_detail.extend(detail)
        all_summary.extend(summary)
        all_tests.extend(tests)
        all_ablation_summary.extend(ablation_summary)
        all_ablation_detail.extend(ablation_detail)
        all_budget_summary.extend(budget_summary)
        all_budget_detail.extend(budget_detail)
        all_novelty_summary.extend(novelty_summary)
        all_novelty_detail.extend(novelty_detail)
        generated_rows = sum(1 for row in detail if int(row["is_reference"]) == 0)
        print(f"dataset={dataset} generated_rows={generated_rows} total_rows={len(detail)}", flush=True)
    combine_outputs(
        args.out_dir,
        all_detail,
        all_summary,
        all_tests,
        all_ablation_summary,
        all_ablation_detail,
        all_budget_summary,
        all_budget_detail,
        all_novelty_summary,
        all_novelty_detail,
    )
    print(f"output_dir={args.out_dir.resolve()}", flush=True)


if __name__ == "__main__":
    main()
