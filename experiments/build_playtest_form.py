from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

import pandas as pd


TILE_LABELS = {
    "#": "Wall",
    ".": "Floor",
    "D": "Door",
    "G": "Goal",
    "E": "Enemy",
    "T": "Trap",
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
    allowed = set(TILE_LABELS)
    bad = sorted({char for row in grid for char in row if char not in allowed})
    require(not bad, f"Stimulus grid contains unsupported tile symbols: {bad}")
    return grid


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
        rows.append(
            {
                "stimulus_id": str(row["stimulus_id"]),
                "display_order": int(row["display_order"]),
                "dataset_label": str(row["dataset_label"]),
                "grid": grid,
            }
        )
    return rows


def render_html(stimuli: list[dict]) -> str:
    payload = json.dumps(stimuli, ensure_ascii=False)
    tile_legend = "".join(
        f'<span class="legend-item tile-{html.escape(symbol_name(symbol))}">'
        f'<span class="legend-swatch">{html.escape(symbol)}</span>{html.escape(label)}</span>'
        for symbol, label in TILE_LABELS.items()
    )
    return f"""<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Blinded Level Playtest</title>
  <style>
    :root {{
      --bg: #f3f5f7;
      --panel: #ffffff;
      --text: #1f2933;
      --muted: #5b6778;
      --line: #d7dde7;
      --accent: #0f6abf;
      --danger: #c2410c;
      --tile: clamp(14px, 2.2vw, 24px);
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Arial, sans-serif; background: var(--bg); color: var(--text); line-height: 1.45; }}
    main {{ max-width: 1120px; margin: 0 auto; padding: 24px 16px 44px; }}
    h1 {{ margin: 0 0 6px; font-size: 28px; }}
    h2 {{ margin: 0 0 8px; font-size: 21px; }}
    button {{ border: 0; border-radius: 6px; padding: 10px 14px; font-weight: 700; cursor: pointer; background: var(--accent); color: #fff; }}
    button.secondary {{ background: #42526e; }}
    button.warning {{ background: var(--danger); }}
    button:disabled {{ background: #9aa5b1; cursor: not-allowed; }}
    input[type="text"], textarea {{ width: 100%; border: 1px solid var(--line); border-radius: 6px; padding: 8px; font: inherit; }}
    .panel {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 16px; margin: 14px 0; }}
    .layout {{ display: grid; grid-template-columns: minmax(0, 1fr) 320px; gap: 16px; align-items: start; }}
    .board-wrap {{ overflow: auto; background: #101820; border-radius: 8px; padding: 12px; border: 1px solid #0b121a; }}
    .board {{ display: grid; gap: 1px; width: max-content; margin: 0 auto; }}
    .tile {{ width: var(--tile); height: var(--tile); display: grid; place-items: center; font-size: calc(var(--tile) * .62); font-weight: 700; border-radius: 2px; }}
    .tile-wall {{ background: #26323f; box-shadow: inset 0 0 0 1px #3b4a5d; }}
    .tile-floor {{ background: #edf2f7; }}
    .tile-door {{ background: #93c5fd; color: #0f315c; }}
    .tile-goal {{ background: #facc15; color: #4b3b00; }}
    .tile-enemy {{ background: #ef4444; color: #fff; }}
    .tile-trap {{ background: #a855f7; color: #fff; }}
    .player {{ outline: 3px solid #111827; background: #22c55e !important; color: #06210f; }}
    .target {{ box-shadow: inset 0 0 0 3px rgba(17, 24, 39, .3); }}
    .status-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }}
    .status {{ border: 1px solid var(--line); border-radius: 6px; padding: 8px; background: #f8fafc; }}
    .status strong {{ display: block; font-size: 18px; }}
    .muted {{ color: var(--muted); }}
    .legend {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }}
    .legend-item {{ display: inline-flex; align-items: center; gap: 6px; border: 1px solid var(--line); border-radius: 999px; padding: 4px 9px; background: #f8fafc; font-size: 14px; }}
    .legend-swatch {{ display: grid; place-items: center; width: 22px; height: 22px; border-radius: 4px; font-weight: 700; background: #e5e7eb; }}
    .actions {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }}
    .rating-group {{ border-top: 1px solid var(--line); padding-top: 12px; margin-top: 12px; }}
    .rating-row {{ display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 7px; }}
    .rating-row label {{ border: 1px solid var(--line); border-radius: 6px; padding: 7px; background: #f8fafc; text-align: center; }}
    .hidden {{ display: none !important; }}
    .kbd {{ border: 1px solid #aab4c3; border-bottom-width: 2px; border-radius: 4px; padding: 1px 5px; background: #fff; font-size: 13px; }}
    @media (max-width: 860px) {{
      .layout {{ grid-template-columns: 1fr; }}
      .rating-row {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
<main>
  <h1>Blinded Level Playtest</h1>
  <p class="muted">Nguoi tham gia choi tung level an danh. Ten thuat toan sinh level khong duoc hien thi.</p>

  <section id="intro" class="panel">
    <h2>Thong tin tham gia</h2>
    <p>Ban se choi 24 level ngan. Moi level ket thuc khi ban cham toi muc tieu mau vang hoac het thoi gian.</p>
    <p>Dieu khien bang <span class="kbd">WASD</span> hoac cac phim mui ten. Cham o do/tim se tinh la that bai va dua ban ve diem bat dau.</p>
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
          <div class="status">Level<strong id="progressValue">1/24</strong></div>
        </div>
        <p class="muted">Muc tieu: di chuyen den o vang. Neu bi ket, bam Restart.</p>
        <div class="actions">
          <button id="restartBtn" type="button" class="secondary">Restart level</button>
          <button id="skipBtn" type="button" class="warning">Het thoi gian/bo qua</button>
        </div>
      </aside>
    </div>
  </section>

  <section id="rating" class="panel hidden">
    <h2>Danh gia sau level</h2>
    <p id="ratingSummary" class="muted"></p>
    <div class="rating-group">
      <strong>Do kho cua level</strong>
      <div class="rating-row" data-field="difficulty_rating"></div>
    </div>
    <div class="rating-group">
      <strong>Muc do thu vi khi choi</strong>
      <div class="rating-row" data-field="fun_rating"></div>
    </div>
    <div class="rating-group">
      <strong>Chat luong tong the</strong>
      <div class="rating-row" data-field="overall_rating"></div>
    </div>
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
const timeoutSeconds = 90;
let participantId = "";
let currentIndex = 0;
let current = null;
let player = null;
let spawn = null;
let startedAt = 0;
let timer = null;
let moves = 0;
let failures = 0;
let restarts = 0;
let completed = false;
let timedOut = false;
let elapsed = 0;
const rows = [];

function tileClass(char) {{
  return {{
    "#": "wall",
    ".": "floor",
    "D": "door",
    "G": "goal",
    "E": "enemy",
    "T": "trap"
  }}[char] || "floor";
}}

function isPassable(char) {{
  return char !== "#";
}}

function isHazard(char) {{
  return char === "E" || char === "T";
}}

function targets(grid) {{
  const result = [];
  for (let r = 0; r < grid.length; r++) {{
    for (let c = 0; c < grid[r].length; c++) {{
      if (grid[r][c] === "G") result.push([r, c]);
    }}
  }}
  if (result.length) return result;
  for (let r = 0; r < grid.length; r++) {{
    for (let c = 0; c < grid[r].length; c++) {{
      if (grid[r][c] === "D") result.push([r, c]);
    }}
  }}
  return result;
}}

function neighbors(pos, grid) {{
  const dirs = [[1,0],[-1,0],[0,1],[0,-1]];
  const result = [];
  for (const [dr, dc] of dirs) {{
    const r = pos[0] + dr;
    const c = pos[1] + dc;
    if (r >= 0 && c >= 0 && r < grid.length && c < grid[r].length && isPassable(grid[r][c])) result.push([r, c]);
  }}
  return result;
}}

function chooseSpawn(grid) {{
  const targetList = targets(grid);
  let best = null;
  let bestScore = -1;
  for (let r = 0; r < grid.length; r++) {{
    for (let c = 0; c < grid[r].length; c++) {{
      const char = grid[r][c];
      if (!isPassable(char) || isHazard(char) || char === "G") continue;
      const queue = [[r, c, 0]];
      const seen = new Set([`${{r}},${{c}}`]);
      let nearestTarget = -1;
      for (let qi = 0; qi < queue.length; qi++) {{
        const [cr, cc, dist] = queue[qi];
        if (targetList.some(([tr, tc]) => tr === cr && tc === cc)) {{
          nearestTarget = dist;
          break;
        }}
        for (const [nr, nc] of neighbors([cr, cc], grid)) {{
          const key = `${{nr}},${{nc}}`;
          if (!seen.has(key) && !isHazard(grid[nr][nc])) {{
            seen.add(key);
            queue.push([nr, nc, dist + 1]);
          }}
        }}
      }}
      const score = nearestTarget >= 0 ? nearestTarget : 0;
      if (score > bestScore) {{
        bestScore = score;
        best = [r, c];
      }}
    }}
  }}
  return best || [0, 0];
}}

function renderBoard() {{
  const board = document.getElementById("board");
  const grid = current.grid;
  board.style.gridTemplateColumns = `repeat(${{grid[0].length}}, var(--tile))`;
  board.innerHTML = "";
  const targetKeys = new Set(targets(grid).map(([r, c]) => `${{r}},${{c}}`));
  for (let r = 0; r < grid.length; r++) {{
    for (let c = 0; c < grid[r].length; c++) {{
      const char = grid[r][c];
      const div = document.createElement("div");
      div.className = `tile tile-${{tileClass(char)}}`;
      if (targetKeys.has(`${{r}},${{c}}`)) div.classList.add("target");
      if (player && player[0] === r && player[1] === c) {{
        div.classList.add("player");
        div.textContent = "@";
      }} else if (char !== ".") {{
        div.textContent = char;
      }}
      board.appendChild(div);
    }}
  }}
}}

function updateStatus() {{
  document.getElementById("movesValue").textContent = moves;
  document.getElementById("failuresValue").textContent = failures;
  document.getElementById("progressValue").textContent = `${{currentIndex + 1}}/${{stimuli.length}}`;
  document.getElementById("timeValue").textContent = `${{elapsed.toFixed(1)}}s`;
}}

function show(id) {{
  for (const section of ["intro", "play", "rating", "done"]) {{
    document.getElementById(section).classList.toggle("hidden", section !== id);
  }}
}}

function startLevel() {{
  current = stimuli[currentIndex];
  spawn = chooseSpawn(current.grid);
  player = [...spawn];
  moves = 0;
  failures = 0;
  restarts = 0;
  completed = false;
  timedOut = false;
  elapsed = 0;
  document.getElementById("stimulusTitle").textContent = current.stimulus_id;
  document.getElementById("datasetLabel").textContent = current.dataset_label;
  startedAt = performance.now();
  clearInterval(timer);
  timer = setInterval(() => {{
    elapsed = (performance.now() - startedAt) / 1000;
    if (elapsed >= timeoutSeconds) finishLevel(false, true);
    updateStatus();
  }}, 100);
  renderBoard();
  updateStatus();
  show("play");
}}

function finishLevel(wasCompleted, wasTimedOut) {{
  clearInterval(timer);
  elapsed = Math.min(timeoutSeconds, (performance.now() - startedAt) / 1000);
  completed = wasCompleted;
  timedOut = wasTimedOut;
  document.getElementById("ratingSummary").textContent =
    `${{current.stimulus_id}}: ${{completed ? "hoan thanh" : "chua hoan thanh"}}, thoi gian ${{elapsed.toFixed(1)}}s, buoc di ${{moves}}, that bai ${{failures}}.`;
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
    player = [...spawn];
  }} else {{
    player = [nr, nc];
    if (targets(current.grid).some(([tr, tc]) => tr === nr && tc === nc)) {{
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
  const columns = ["participant_id", "stimulus_id", "dataset_label", "completed", "time_seconds", "moves", "failures", "restarts", "timed_out", "difficulty_rating", "fun_rating", "overall_rating", "comment"];
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
  if (!participantId) {{
    alert("Vui long nhap ma nguoi tham gia.");
    return;
  }}
  if (!document.getElementById("consent").checked) {{
    alert("Vui long tick dong y tham gia.");
    return;
  }}
  startLevel();
}});
document.getElementById("restartBtn").addEventListener("click", () => {{
  restarts += 1;
  player = [...spawn];
  renderBoard();
  updateStatus();
}});
document.getElementById("skipBtn").addEventListener("click", () => finishLevel(false, true));
document.getElementById("nextBtn").addEventListener("click", saveRatingAndContinue);
document.getElementById("downloadBtn").addEventListener("click", downloadCsv);
document.addEventListener("keydown", event => {{
  if (document.getElementById("play").classList.contains("hidden")) return;
  const key = event.key.toLowerCase();
  const map = {{
    "arrowup": [-1, 0], "w": [-1, 0],
    "arrowdown": [1, 0], "s": [1, 0],
    "arrowleft": [0, -1], "a": [0, -1],
    "arrowright": [0, 1], "d": [0, 1]
  }};
  if (map[key]) {{
    event.preventDefault();
    move(map[key][0], map[key][1]);
  }}
}});
</script>
</body>
</html>
"""


def symbol_name(symbol: str) -> str:
    return {
        "#": "wall",
        ".": "floor",
        "D": "door",
        "G": "goal",
        "E": "enemy",
        "T": "trap",
    }[symbol]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a self-contained blinded HTML playtest from a study pack.")
    parser.add_argument("--study-pack", type=Path, default=Path("human_study/study_pack_seed2026"))
    parser.add_argument("--out-dir", type=Path, default=Path("human_study_playtest/playtest_pack_seed2026"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    stimuli = load_stimuli(args.study_pack)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    output = args.output or (args.out_dir / "playtest_form.html")
    output.write_text(render_html(stimuli), encoding="utf-8")
    print(f"wrote_html={output} stimuli={len(stimuli)}")


if __name__ == "__main__":
    main()
