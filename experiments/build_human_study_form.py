from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

import pandas as pd


RATING_FIELDS = [
    ("playability", "1. Muc do co the choi duoc", "Level nay nhin co ve co duong di, co cau truc hop ly, khong bi vo/qua ngau nhien khong?"),
    ("style", "2. Do giong phong cach game", "Level nay nhin co hop voi phong cach cua game dang hien thi khong?"),
    ("novelty", "3. Do moi la", "Level nay co khac biet/thu vi so voi cac level khac, nhung van con hop ly khong?"),
    ("overall", "4. Chat luong tong the", "Neu phai chon de dua vao game/prototype, ban danh gia level nay tot den muc nao?"),
]

TILE_LEGEND = [
    ("#", "tuong/vat can"),
    (".", "o trong/co the di qua"),
    ("D", "cua/diem ket noi"),
    ("G", "muc tieu/vat pham/diem can den"),
    ("E", "ke dich/nguy hiem"),
    ("T", "bay/nguy hiem"),
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"ERROR: {message}")


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
        text = stimulus_path.read_text(encoding="utf-8")
        lines = text.splitlines()
        try:
            grid_start = lines.index("Level grid:") + 1
        except ValueError:
            grid_start = 0
        grid = "\n".join(lines[grid_start:]).strip()
        rows.append(
            {
                "stimulus_id": str(row["stimulus_id"]),
                "display_order": int(row["display_order"]),
                "dataset_label": str(row["dataset_label"]),
                "grid": grid,
            }
        )
    return rows


def radio_group(stimulus_id: str, field: str) -> str:
    options = []
    labels = {
        1: "1 - rat kem",
        2: "2 - kem",
        3: "3 - tam duoc",
        4: "4 - tot",
        5: "5 - rat tot",
    }
    for value in range(1, 6):
        name = f"{stimulus_id}_{field}"
        options.append(
            f'<label class="rating-option"><input type="radio" name="{html.escape(name)}" value="{value}" required> {html.escape(labels[value])}</label>'
        )
    return "\n".join(options)


def render_form(stimuli: list[dict]) -> str:
    stimulus_html = []
    for item in stimuli:
        sid = html.escape(item["stimulus_id"])
        dataset = html.escape(item["dataset_label"])
        grid = html.escape(item["grid"])
        rating_blocks = []
        for field, title, prompt in RATING_FIELDS:
            rating_blocks.append(
                "\n".join(
                    [
                        '<div class="rating-block">',
                        f"<div><strong>{html.escape(title)}</strong></div>",
                        f"<div class=\"prompt\">{html.escape(prompt)}</div>",
                        f'<div class="rating-row">{radio_group(sid, field)}</div>',
                        "</div>",
                    ]
                )
            )
        stimulus_html.append(
            "\n".join(
                [
                    '<section class="stimulus" data-stimulus-id="' + sid + '">',
                    f"<h2>{sid} <span>{dataset}</span></h2>",
                    '<p class="hint">Hay nhin tong the level ben duoi va cham diem theo cam nhan cua ban. Khong can biet level nay do thuat toan nao tao ra.</p>',
                    f"<pre>{grid}</pre>",
                    *rating_blocks,
                    '<label class="comment-label">Ghi chu tuy chon</label>',
                    f'<textarea name="{sid}_comment" rows="2"></textarea>',
                    "</section>",
                ]
            )
        )

    stimuli_json = json.dumps(
        [{"stimulus_id": item["stimulus_id"], "dataset_label": item["dataset_label"]} for item in stimuli],
        ensure_ascii=False,
    )
    return f"""<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Khao sat danh gia level game</title>
  <style>
    body {{ font-family: Arial, sans-serif; line-height: 1.5; margin: 0; color: #1f2937; background: #f6f7f9; }}
    main {{ max-width: 980px; margin: 0 auto; padding: 28px 18px 48px; }}
    h1 {{ margin: 0 0 8px; font-size: 28px; }}
    .intro, .guide, .stimulus, .export-box {{ background: #fff; border: 1px solid #d8dde6; border-radius: 8px; padding: 18px; margin: 16px 0; }}
    .stimulus h2 {{ margin: 0 0 12px; font-size: 20px; }}
    .stimulus h2 span {{ font-weight: 400; color: #4b5563; margin-left: 8px; }}
    pre {{ background: #111827; color: #f9fafb; padding: 14px; border-radius: 6px; overflow-x: auto; font-family: Consolas, "Courier New", monospace; font-size: 14px; line-height: 1.18; }}
    .rating-block {{ border-top: 1px solid #e5e7eb; padding-top: 12px; margin-top: 12px; }}
    .prompt {{ color: #4b5563; margin: 2px 0 8px; }}
    .hint {{ color: #4b5563; margin: 0 0 10px; }}
    .rating-row {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 8px; }}
    .rating-option {{ border: 1px solid #d8dde6; border-radius: 6px; padding: 7px 8px; background: #f9fafb; }}
    .comment-label {{ display: block; margin-top: 14px; font-weight: 700; }}
    textarea, input[type="text"] {{ width: 100%; box-sizing: border-box; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px; font: inherit; }}
    button {{ background: #0f5fb8; color: #fff; border: 0; border-radius: 6px; padding: 10px 16px; font-weight: 700; cursor: pointer; }}
    button:hover {{ background: #0b4f99; }}
    .small {{ color: #4b5563; font-size: 14px; }}
    .legend {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 8px; padding: 0; margin: 10px 0 0; list-style: none; }}
    .legend li {{ border: 1px solid #e5e7eb; border-radius: 6px; padding: 7px 8px; background: #f9fafb; }}
    code {{ background: #eef2f7; padding: 1px 5px; border-radius: 4px; }}
  </style>
</head>
<body>
<main>
  <h1>Khao sat danh gia level game</h1>
  <div class="intro">
    <p>Ban se xem 24 level game dang luoi ky tu. Cac level nay do nhieu thuat toan khac nhau tao ra, nhung ten thuat toan da duoc an di de dam bao danh gia cong bang.</p>
    <p>Nhiem vu cua ban: nhin tung level va cham diem theo cam nhan. Khong can choi that, khong can hieu sau ve thuat toan.</p>
    <label>Ma nguoi tham gia <input type="text" id="participant_id" placeholder="P001" required></label>
    <p><label><input type="checkbox" id="consent" required> Toi dong y tham gia tu nguyen va hieu rang cau tra loi se duoc tong hop cho muc dich hoc thuat.</label></p>
  </div>
  <div class="guide">
    <h2>Cach cham diem</h2>
    <p>Moi tieu chi cham tu 1 den 5:</p>
    <p><strong>1</strong> = rat kem, <strong>2</strong> = kem, <strong>3</strong> = tam duoc/khong chac, <strong>4</strong> = tot, <strong>5</strong> = rat tot.</p>
    <p>Hay cham theo truc giac cua ban. Neu level nhin qua ngau nhien, bi vo cau truc, hoac kho hieu thi co the cho diem thap.</p>
    <h2>Y nghia ky tu trong level</h2>
    <ul class="legend">
      {''.join(f'<li><code>{html.escape(symbol)}</code> = {html.escape(description)}</li>' for symbol, description in TILE_LEGEND)}
    </ul>
  </div>
  <form id="surveyForm">
    {''.join(stimulus_html)}
    <div class="export-box">
      <button type="submit">Tai file cau tra loi CSV</button>
      <p class="small">Chi bam nut nay sau khi da cham het 24 level. Gui file CSV vua tai ve cho nguoi phu trach khao sat.</p>
    </div>
  </form>
</main>
<script>
const stimuli = {stimuli_json};
const ratingFields = {json.dumps([field for field, _, _ in RATING_FIELDS])};

function csvEscape(value) {{
  const text = String(value ?? "");
  if (/[",\\n]/.test(text)) {{
    return '"' + text.replace(/"/g, '""') + '"';
  }}
  return text;
}}

function download(filename, text) {{
  const blob = new Blob([text], {{type: "text/csv;charset=utf-8"}});
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(link.href);
}}

document.getElementById("surveyForm").addEventListener("submit", function(event) {{
  event.preventDefault();
  const participantId = document.getElementById("participant_id").value.trim();
  if (!participantId) {{
    alert("Vui long nhap ma nguoi tham gia, vi du P001.");
    return;
  }}
  if (!document.getElementById("consent").checked) {{
    alert("Vui long tick vao o dong y tham gia truoc khi nop.");
    return;
  }}
  const rows = [["participant_id", "stimulus_id", "playability", "style", "novelty", "overall", "comment"]];
  for (const stimulus of stimuli) {{
    const row = [participantId, stimulus.stimulus_id];
    for (const field of ratingFields) {{
      const selected = document.querySelector(`input[name="${{stimulus.stimulus_id}}_${{field}}"]:checked`);
      if (!selected) {{
        alert(`Ban chua cham muc ${{field}} cho ${{stimulus.stimulus_id}}.`);
        return;
      }}
      row.push(selected.value);
    }}
    const comment = document.querySelector(`textarea[name="${{stimulus.stimulus_id}}_comment"]`).value.trim();
    row.push(comment);
    rows.push(row);
  }}
  const csv = rows.map(row => row.map(csvEscape).join(",")).join("\\n") + "\\n";
  download(`human_study_response_${{participantId}}.csv`, csv);
}});
</script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a self-contained blinded HTML survey from a human-study pack.")
    parser.add_argument("--study-pack", type=Path, default=Path("human_study/study_pack_seed2026"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    stimuli = load_stimuli(args.study_pack)
    output = args.output or (args.study_pack / "survey_form.html")
    output.write_text(render_form(stimuli), encoding="utf-8")
    print(f"wrote_html={output} stimuli={len(stimuli)}")


if __name__ == "__main__":
    main()
