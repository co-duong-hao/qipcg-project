from __future__ import annotations

import argparse
import base64
import html
import json
from collections import deque
from pathlib import Path

import pandas as pd


TILE_LABELS = {
    "#": "Wall",
    ".": "Floor",
    "D": "Door",
    "G": "Collectible / goal marker",
    "E": "Enemy hazard",
    "T": "Trap hazard",
}
PASSABLE = {".", "D", "G", "E", "T"}
SAFE = {".", "D", "G"}
HAZARDS = {"E", "T"}
SPRITE_FILES = {
    "wall": [
        "tile_0008.png",
        "tile_0009.png",
        "tile_0010.png",
        "tile_0026.png",
        "tile_0027.png",
        "tile_0028.png",
        "tile_0044.png",
        "tile_0045.png",
        "tile_0046.png",
        "tile_0062.png",
        "tile_0063.png",
        "tile_0064.png",
        "tile_0080.png",
        "tile_0081.png",
        "tile_0082.png",
    ],
    "floor": ["tile_0001.png", "tile_0002.png"],
    "door": ["tile_0071.png"],
    "goal": ["tile_0192.png"],
    "enemy": ["tile_0106.png"],
    "trap": ["tile_0095.png"],
    "player": ["tile_0136.png"],
    "spawn": ["tile_0126.png"],
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"ERROR: {message}")


def parse_grid(text: str) -> list[str]:
    lines = text.splitlines()
    try:
        grid_start = lines.index("Level grid:") + 1
    except ValueError:
        grid_start = 0
    grid = [line.rstrip() for line in lines[grid_start:] if line.rstrip()]
    require(grid, "Stimulus file has no grid")
    width = len(grid[0])
    require(all(len(row) == width for row in grid), "Stimulus grid rows must have equal width")
    bad = sorted({char for row in grid for char in row if char not in TILE_LABELS})
    require(not bad, f"Stimulus grid contains unsupported tile symbols: {bad}")
    return grid


def neighbors(pos: tuple[int, int], grid: list[str], *, safe_only: bool) -> list[tuple[int, int]]:
    h = len(grid)
    w = len(grid[0])
    result = []
    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        r = pos[0] + dr
        c = pos[1] + dc
        if r < 0 or c < 0 or r >= h or c >= w:
            continue
        if safe_only:
            if grid[r][c] in SAFE:
                result.append((r, c))
        elif grid[r][c] in PASSABLE:
            result.append((r, c))
    return result


def bfs(grid: list[str], start: tuple[int, int], *, safe_only: bool = True) -> dict[tuple[int, int], int]:
    distances = {start: 0}
    queue: deque[tuple[int, int]] = deque([start])
    while queue:
        cur = queue.popleft()
        for nxt in neighbors(cur, grid, safe_only=safe_only):
            if nxt not in distances:
                distances[nxt] = distances[cur] + 1
                queue.append(nxt)
    return distances


def safe_cells(grid: list[str]) -> list[tuple[int, int]]:
    return [(r, c) for r, row in enumerate(grid) for c, char in enumerate(row) if char in SAFE]


def target_cells(grid: list[str], cells: set[tuple[int, int]]) -> list[tuple[int, int]]:
    goals = [(r, c) for r, c in cells if grid[r][c] == "G"]
    doors = [(r, c) for r, c in cells if grid[r][c] == "D"]
    return goals or doors


def component_from(grid: list[str], start: tuple[int, int]) -> set[tuple[int, int]]:
    return set(bfs(grid, start, safe_only=True))


def largest_safe_component(grid: list[str]) -> set[tuple[int, int]]:
    remaining = set(safe_cells(grid))
    best: set[tuple[int, int]] = set()
    while remaining:
        start = next(iter(remaining))
        comp = component_from(grid, start)
        if len(comp) > len(best):
            best = comp
        remaining -= comp
    return best


def choose_task(grid: list[str]) -> dict:
    comp = largest_safe_component(grid)
    require(len(comp) >= 2, "Grid has fewer than two connected safe cells")
    targets = target_cells(grid, comp)
    if not targets:
        # Fall back to a virtual target on a floor tile. The source grid is not modified.
        targets = sorted(comp)

    best_goal = targets[0]
    best_spawn = targets[0]
    best_distance = -1
    for goal in sorted(targets):
        distances = bfs(grid, goal, safe_only=True)
        candidate_spawns = [cell for cell in comp if cell in distances and cell != goal and grid[cell[0]][cell[1]] not in {"G", "D"}]
        if not candidate_spawns:
            candidate_spawns = [cell for cell in comp if cell in distances and cell != goal]
        spawn = max(candidate_spawns, key=lambda cell: (distances[cell], -cell[0], -cell[1]))
        distance = distances[spawn]
        if distance > best_distance:
            best_goal = goal
            best_spawn = spawn
            best_distance = distance

    distances_from_spawn = bfs(grid, best_spawn, safe_only=True)
    collectible_candidates = [
        cell
        for cell in comp
        if grid[cell[0]][cell[1]] == "G"
        and cell != best_goal
        and cell in distances_from_spawn
    ]
    collectible_candidates.sort(key=lambda cell: (distances_from_spawn[cell], cell[0], cell[1]), reverse=True)
    collectibles = collectible_candidates[: min(3, len(collectible_candidates))]
    required = len(collectibles)
    hazard_count = sum(1 for row in grid for char in row if char in HAZARDS)
    timeout = max(25, min(60, int(best_distance * 1.8 + required * 8 + 12)))
    return {
        "spawn": list(best_spawn),
        "goal": list(best_goal),
        "collectibles": [list(cell) for cell in sorted(collectibles)],
        "required_collectibles": required,
        "optimal_path_length": int(best_distance),
        "hazard_count": int(hazard_count),
        "timeout_seconds": timeout,
    }


def load_stimuli(study_pack: Path) -> list[dict]:
    manifest_path = study_pack / "stimuli_manifest_blinded.csv"
    require(manifest_path.exists(), f"Missing blinded manifest: {manifest_path}")
    manifest = pd.read_csv(manifest_path).sort_values("display_order")
    required = {"stimulus_id", "display_order", "dataset_label", "stimulus_file"}
    missing = required - set(manifest.columns)
    require(not missing, f"Blinded manifest missing columns: {sorted(missing)}")
    require("method" not in manifest.columns, "Blinded manifest must not contain method labels")

    rows: list[dict] = []
    for row in manifest.to_dict(orient="records"):
        stimulus_path = study_pack / str(row["stimulus_file"])
        require(stimulus_path.exists(), f"Missing stimulus file: {stimulus_path}")
        grid = parse_grid(stimulus_path.read_text(encoding="utf-8"))
        task = choose_task(grid)
        rows.append(
            {
                "stimulus_id": str(row["stimulus_id"]),
                "display_order": int(row["display_order"]),
                "dataset_label": str(row["dataset_label"]),
                "grid": grid,
                **task,
            }
        )
    return rows


def symbol_name(symbol: str) -> str:
    return {
        "#": "wall",
        ".": "floor",
        "D": "door",
        "G": "goal",
        "E": "enemy",
        "T": "trap",
    }[symbol]


def load_sprites(sprite_dir: Path) -> dict[str, list[str]]:
    sprites: dict[str, list[str]] = {}
    for name, files in SPRITE_FILES.items():
        sprites[name] = []
        for filename in files:
            path = sprite_dir / filename
            require(path.exists(), f"Missing sprite file: {path}")
            encoded = base64.b64encode(path.read_bytes()).decode("ascii")
            sprites[name].append(f"data:image/png;base64,{encoded}")
    return sprites


def render_html(stimuli: list[dict], sprites: dict[str, list[str]]) -> str:
    payload = json.dumps(stimuli, ensure_ascii=False)
    sprites_json = json.dumps(sprites)
    tile_legend = "".join(
        f'<span class="legend-item"><span class="legend-swatch sprite-swatch" data-sprite="{html.escape(symbol_name(symbol))}" aria-hidden="true"></span>'
        f"{html.escape(label)}</span>"
        for symbol, label in TILE_LABELS.items()
    )
    return f"""<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Blinded Goal-Oriented Playtest</title>
  <style>
    :root {{
      --bg: #f3f5f7; --panel: #fff; --text: #1f2933; --muted: #5b6778;
      --line: #d7dde7; --accent: #0f6abf; --danger: #b42318;
      --tile: clamp(15px, 2.2vw, 25px);
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Arial, sans-serif; background: var(--bg); color: var(--text); line-height: 1.45; }}
    main {{ max-width: 1120px; margin: 0 auto; padding: 24px 16px 44px; }}
    h1 {{ margin: 0 0 6px; font-size: 28px; }}
    h2 {{ margin: 0 0 8px; font-size: 21px; }}
    button {{ border: 0; border-radius: 6px; padding: 10px 14px; font-weight: 700; cursor: pointer; background: var(--accent); color: #fff; }}
    button.secondary {{ background: #42526e; }}
    button.warning {{ background: var(--danger); }}
    input[type="text"], textarea {{ width: 100%; border: 1px solid var(--line); border-radius: 6px; padding: 8px; font: inherit; }}
    .panel {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 16px; margin: 14px 0; }}
    .layout {{ display: grid; grid-template-columns: minmax(0, 1fr) 330px; gap: 16px; align-items: start; }}
    .board-wrap {{ overflow: auto; background: #101820; border-radius: 8px; padding: 12px; border: 1px solid #0b121a; }}
    .board {{ display: grid; gap: 1px; width: max-content; margin: 0 auto; }}
    .tile {{ position: relative; width: var(--tile); height: var(--tile); display: grid; place-items: center; border-radius: 3px; overflow: hidden; image-rendering: pixelated; background-size: cover; background-position: center; }}
    .spawn {{ outline: 3px solid #16a34a; outline-offset: -2px; }}
    .spawn::after {{ content: ""; position: absolute; inset: 18%; background-image: var(--spawn-sprite); background-size: contain; background-repeat: no-repeat; background-position: center; opacity: .95; pointer-events: none; }}
    .player {{ outline: 3px solid #111827; outline-offset: -2px; background-image: var(--player-sprite) !important; background-size: cover; }}
    .final-goal {{ outline: 3px solid #f97316; outline-offset: -2px; }}
    .collectible {{ box-shadow: inset 0 0 0 3px #0f6abf; }}
    .collected {{ opacity: .35; }}
    .status-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }}
    .status {{ border: 1px solid var(--line); border-radius: 6px; padding: 8px; background: #f8fafc; }}
    .status strong {{ display: block; font-size: 18px; }}
    .muted {{ color: var(--muted); }}
    .legend {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }}
    .legend-item {{ display: inline-flex; align-items: center; gap: 6px; border: 1px solid var(--line); border-radius: 999px; padding: 4px 9px; background: #f8fafc; font-size: 14px; }}
    .sprite-swatch {{ width: 22px; height: 22px; border-radius: 4px; flex: 0 0 auto; image-rendering: pixelated; background-size: cover; background-position: center; }}
    .actions {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }}
    .rating-group {{ border-top: 1px solid var(--line); padding-top: 12px; margin-top: 12px; }}
    .rating-row {{ display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 7px; }}
    .rating-row label {{ border: 1px solid var(--line); border-radius: 6px; padding: 7px; background: #f8fafc; text-align: center; }}
    .hidden {{ display: none !important; }}
    .kbd {{ border: 1px solid #aab4c3; border-bottom-width: 2px; border-radius: 4px; padding: 1px 5px; background: #fff; font-size: 13px; }}
    @media (max-width: 860px) {{ .layout {{ grid-template-columns: 1fr; }} .rating-row {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
<main>
  <h1>Blinded Goal-Oriented Playtest</h1>
  <p class="muted">Nguoi tham gia choi tung level an danh. Ten thuat toan sinh level khong duoc hien thi.</p>

  <section id="intro" class="panel">
    <h2>Thong tin tham gia</h2>
    <p>Moi level co diem bat dau mau xanh, muc tieu cuoi vien cam, va co the co vat pham can thu thap vien xanh duong.</p>
    <p>Dieu khien bang <span class="kbd">WASD</span> hoac phim mui ten. Cham enemy/trap se bi phat thoi gian va dua ve diem bat dau.</p>
    <label>Ma nguoi tham gia <input type="text" id="participantId" placeholder="P001" required></label>
    <p><label><input type="checkbox" id="consent"> Toi dong y tham gia tu nguyen va hieu rang ket qua chi duoc tong hop cho muc dich hoc thuat.</label></p>
    <div class="legend">{tile_legend}</div>
    <div class="actions"><button id="startBtn" type="button">Bat dau</button></div>
  </section>

  <section id="play" class="panel hidden">
    <h2><span id="stimulusTitle"></span> <span id="datasetLabel" class="muted"></span></h2>
    <div class="layout">
      <div class="board-wrap"><div id="board" class="board" aria-label="Level board"></div></div>
      <aside>
        <div class="status-grid">
          <div class="status">Thoi gian<strong id="timeValue">0.0s</strong></div>
          <div class="status">Buoc di<strong id="movesValue">0</strong></div>
          <div class="status">That bai<strong id="failuresValue">0</strong></div>
          <div class="status">Vat pham<strong id="collectValue">0/0</strong></div>
          <div class="status">Toi uu<strong id="optimalValue">0</strong></div>
          <div class="status">Level<strong id="progressValue">1/24</strong></div>
        </div>
        <p class="muted" id="objectiveText"></p>
        <div class="actions">
          <button id="restartBtn" type="button" class="secondary">Restart level</button>
          <button id="skipBtn" type="button" class="warning">Bo qua / het gio</button>
        </div>
      </aside>
    </div>
  </section>

  <section id="rating" class="panel hidden">
    <h2>Danh gia sau level</h2>
    <p id="ratingSummary" class="muted"></p>
    <div class="rating-group"><strong>Do kho cua level</strong><div class="rating-row" data-field="difficulty_rating"></div></div>
    <div class="rating-group"><strong>Muc do thu vi khi choi</strong><div class="rating-row" data-field="fun_rating"></div></div>
    <div class="rating-group"><strong>Chat luong tong the</strong><div class="rating-row" data-field="overall_rating"></div></div>
    <label class="rating-group"><strong>Ghi chu tuy chon</strong><textarea id="comment" rows="3"></textarea></label>
    <div class="actions"><button id="nextBtn" type="button">Level tiep theo</button></div>
  </section>

  <section id="done" class="panel hidden">
    <h2>Hoan thanh</h2>
    <p>Cam on ban da tham gia. Hay tai file CSV va gui lai cho nguoi phu trach khao sat.</p>
    <div class="actions"><button id="downloadBtn" type="button">Tai file CSV</button></div>
  </section>
</main>

<script>
const stimuli = {payload};
const sprites = {sprites_json};
const hazardPenaltySeconds = 5;
let participantId = "";
let currentIndex = 0;
let current = null;
let player = null;
let startedAt = 0;
let timer = null;
let moves = 0;
let failures = 0;
let restarts = 0;
let completed = false;
let timedOut = false;
let elapsed = 0;
let penaltySeconds = 0;
let collected = new Set();
const rows = [];

function key(pos) {{ return `${{pos[0]}},${{pos[1]}}`; }}
function tileClass(char) {{ return {{"#":"wall",".":"floor","D":"door","G":"goal","E":"enemy","T":"trap"}}[char] || "floor"; }}
function isPassable(char) {{ return char !== "#"; }}
function isHazard(char) {{ return char === "E" || char === "T"; }}
function same(a, b) {{ return a && b && a[0] === b[0] && a[1] === b[1]; }}
function requiredCollected() {{ return collected.size >= current.required_collectibles; }}
function spriteFor(name, r = 0, c = 0) {{
  const options = sprites[name] || [];
  if (!options.length) return "";
  const index = Math.abs((r * 928371 + c * 364479 + name.length * 9973)) % options.length;
  return options[index];
}}
function setSprite(element, name, r = 0, c = 0) {{
  const src = spriteFor(name, r, c);
  if (src) element.style.backgroundImage = `url("${{src}}")`;
}}
document.querySelectorAll(".sprite-swatch").forEach((node) => setSprite(node, node.dataset.sprite || "floor"));
document.documentElement.style.setProperty("--player-sprite", `url("${{spriteFor("player")}}")`);
document.documentElement.style.setProperty("--spawn-sprite", `url("${{spriteFor("spawn")}}")`);

function renderBoard() {{
  const board = document.getElementById("board");
  const grid = current.grid;
  board.style.gridTemplateColumns = `repeat(${{grid[0].length}}, var(--tile))`;
  board.innerHTML = "";
  const collectibleKeys = new Set(current.collectibles.map(key));
  for (let r = 0; r < grid.length; r++) {{
    for (let c = 0; c < grid[r].length; c++) {{
      const char = grid[r][c];
      const pos = [r, c];
      const div = document.createElement("div");
      div.className = `tile tile-${{tileClass(char)}}`;
      setSprite(div, tileClass(char), r, c);
      if (same(pos, current.spawn)) div.classList.add("spawn");
      if (same(pos, current.goal)) div.classList.add("final-goal");
      if (collectibleKeys.has(key(pos))) div.classList.add("collectible");
      if (collected.has(key(pos))) div.classList.add("collected");
      if (same(pos, player)) {{
        div.classList.add("player");
      }}
      board.appendChild(div);
    }}
  }}
}}

function updateStatus() {{
  document.getElementById("movesValue").textContent = moves;
  document.getElementById("failuresValue").textContent = failures;
  document.getElementById("collectValue").textContent = `${{collected.size}}/${{current.required_collectibles}}`;
  document.getElementById("optimalValue").textContent = current.optimal_path_length;
  document.getElementById("progressValue").textContent = `${{currentIndex + 1}}/${{stimuli.length}}`;
  document.getElementById("timeValue").textContent = `${{elapsed.toFixed(1)}}s / ${{current.timeout_seconds}}s`;
}}

function show(id) {{
  for (const section of ["intro", "play", "rating", "done"]) {{
    document.getElementById(section).classList.toggle("hidden", section !== id);
  }}
}}

function startLevel() {{
  current = stimuli[currentIndex];
  player = [...current.spawn];
  moves = 0;
  failures = 0;
  restarts = 0;
  completed = false;
  timedOut = false;
  elapsed = 0;
  penaltySeconds = 0;
  collected = new Set();
  document.getElementById("stimulusTitle").textContent = current.stimulus_id;
  document.getElementById("datasetLabel").textContent = current.dataset_label;
  document.getElementById("objectiveText").textContent =
    current.required_collectibles > 0
      ? `Thu thap du ${{current.required_collectibles}} vat pham vien xanh duong, sau do den muc tieu vien cam.`
      : "Di den muc tieu vien cam truoc khi het thoi gian.";
  startedAt = performance.now();
  clearInterval(timer);
  timer = setInterval(() => {{
    elapsed = (performance.now() - startedAt) / 1000 + penaltySeconds;
    if (elapsed >= current.timeout_seconds) finishLevel(false, true);
    updateStatus();
  }}, 100);
  renderBoard();
  updateStatus();
  show("play");
}}

function finishLevel(wasCompleted, wasTimedOut) {{
  clearInterval(timer);
  elapsed = Math.min(current.timeout_seconds, (performance.now() - startedAt) / 1000 + penaltySeconds);
  completed = wasCompleted;
  timedOut = wasTimedOut;
  const efficiency = completed && current.optimal_path_length > 0 ? (moves / current.optimal_path_length).toFixed(3) : "";
  document.getElementById("ratingSummary").textContent =
    `${{current.stimulus_id}}: ${{completed ? "hoan thanh" : "chua hoan thanh"}}, thoi gian ${{elapsed.toFixed(1)}}s, buoc di ${{moves}}, that bai ${{failures}}, efficiency ${{efficiency || "NA"}}.`;
  document.getElementById("comment").value = "";
  document.querySelectorAll(".rating-row input").forEach(input => input.checked = false);
  show("rating");
}}

function move(dr, dc) {{
  if (!current) return;
  const nr = player[0] + dr;
  const nc = player[1] + dc;
  if (nr < 0 || nc < 0 || nr >= current.grid.length || nc >= current.grid[nr].length) return;
  const char = current.grid[nr][nc];
  if (!isPassable(char)) return;
  moves += 1;
  if (isHazard(char)) {{
    failures += 1;
    penaltySeconds += hazardPenaltySeconds;
    player = [...current.spawn];
  }} else {{
    player = [nr, nc];
    const posKey = key(player);
    if (current.collectibles.map(key).includes(posKey)) collected.add(posKey);
    if (same(player, current.goal) && requiredCollected()) {{
      renderBoard();
      updateStatus();
      finishLevel(true, false);
      return;
    }}
  }}
  renderBoard();
  updateStatus();
}}

function selectedRating(field) {{
  const input = document.querySelector(`input[name="${{field}}"]:checked`);
  return input ? input.value : "";
}}

function saveRatingAndContinue() {{
  const difficulty = selectedRating("difficulty_rating");
  const fun = selectedRating("fun_rating");
  const overall = selectedRating("overall_rating");
  if (!difficulty || !fun || !overall) {{
    alert("Vui long cham du 3 tieu chi truoc khi tiep tuc.");
    return;
  }}
  const efficiency = completed && current.optimal_path_length > 0 ? moves / current.optimal_path_length : "";
  rows.push({{
    participant_id: participantId,
    stimulus_id: current.stimulus_id,
    dataset_label: current.dataset_label,
    completed: completed ? 1 : 0,
    time_seconds: elapsed.toFixed(3),
    moves,
    failures,
    restarts,
    timed_out: timedOut ? 1 : 0,
    collected_count: collected.size,
    required_collectibles: current.required_collectibles,
    optimal_path_length: current.optimal_path_length,
    efficiency_ratio: efficiency === "" ? "" : efficiency.toFixed(3),
    timeout_seconds: current.timeout_seconds,
    difficulty_rating: difficulty,
    fun_rating: fun,
    overall_rating: overall,
    comment: document.getElementById("comment").value.trim()
  }});
  currentIndex += 1;
  if (currentIndex >= stimuli.length) show("done");
  else startLevel();
}}

function csvEscape(value) {{
  const text = String(value ?? "");
  if (/[",\\n]/.test(text)) return '"' + text.replace(/"/g, '""') + '"';
  return text;
}}

function downloadCsv() {{
  const columns = ["participant_id", "stimulus_id", "dataset_label", "completed", "time_seconds", "moves", "failures", "restarts", "timed_out", "collected_count", "required_collectibles", "optimal_path_length", "efficiency_ratio", "timeout_seconds", "difficulty_rating", "fun_rating", "overall_rating", "comment"];
  const csv = [columns, ...rows.map(row => columns.map(col => row[col]))]
    .map(row => row.map(csvEscape).join(",")).join("\\n") + "\\n";
  const blob = new Blob([csv], {{type: "text/csv;charset=utf-8"}});
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `playtest_response_${{participantId}}.csv`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(link.href);
}}

for (const field of ["difficulty_rating", "fun_rating", "overall_rating"]) {{
  const row = document.querySelector(`.rating-row[data-field="${{field}}"]`);
  for (let i = 1; i <= 5; i++) {{
    const label = document.createElement("label");
    label.innerHTML = `<input type="radio" name="${{field}}" value="${{i}}"> ${{i}}`;
    row.appendChild(label);
  }}
}}

document.getElementById("startBtn").addEventListener("click", () => {{
  participantId = document.getElementById("participantId").value.trim();
  if (!participantId) {{ alert("Vui long nhap ma nguoi tham gia."); return; }}
  if (!document.getElementById("consent").checked) {{ alert("Vui long tick dong y tham gia."); return; }}
  startLevel();
}});
document.getElementById("restartBtn").addEventListener("click", () => {{
  restarts += 1;
  player = [...current.spawn];
  renderBoard();
  updateStatus();
}});
document.getElementById("skipBtn").addEventListener("click", () => finishLevel(false, true));
document.getElementById("nextBtn").addEventListener("click", saveRatingAndContinue);
document.getElementById("downloadBtn").addEventListener("click", downloadCsv);
document.addEventListener("keydown", event => {{
  if (document.getElementById("play").classList.contains("hidden")) return;
  const map = {{
    "arrowup": [-1, 0], "w": [-1, 0],
    "arrowdown": [1, 0], "s": [1, 0],
    "arrowleft": [0, -1], "a": [0, -1],
    "arrowright": [0, 1], "d": [0, 1]
  }};
  const keyName = event.key.toLowerCase();
  if (map[keyName]) {{
    event.preventDefault();
    move(map[keyName][0], map[keyName][1]);
  }}
}});
</script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a self-contained blinded goal-oriented HTML playtest from a study pack.")
    parser.add_argument("--study-pack", type=Path, default=Path("human_study/study_pack_seed2026"))
    parser.add_argument("--out-dir", type=Path, default=Path("human_study_playtest/playtest_pack_seed2026"))
    parser.add_argument("--sprite-dir", type=Path, default=Path("Sprite"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    stimuli = load_stimuli(args.study_pack)
    sprites = load_sprites(args.sprite_dir)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    output = args.output or (args.out_dir / "playtest_form.html")
    output.write_text(render_html(stimuli, sprites), encoding="utf-8")
    print(f"wrote_html={output} stimuli={len(stimuli)}")


if __name__ == "__main__":
    main()
