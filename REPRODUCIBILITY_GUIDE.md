# Reproducibility Guide

This guide explains how to reproduce the dataset experiments for the QI-PCG
project. The repository does not include the dataset, generated outputs, paper
files, or internal review notes.

See `DATA_AVAILABILITY.md` for dataset citation and artifact availability.

## Dataset Layout

Place the VGLC dataset at the project root:

```text
TheVGLC/
  The Legend of Zelda/Processed/
  Lode Runner/Processed/
  Super Mario Bros/Processed/        # optional third-domain extension
```

Do not rename these dataset folders. The experiment scripts expect the VGLC
processed text-grid layout.

## Install Dependencies

```powershell
pip install -r requirements.txt
```

Required Python packages:

```text
numpy
pandas
Pillow
reportlab
pypdf
```

## Smoke Test

Run a smoke test before any full experiment. It checks that Python,
dependencies, dataset paths, and output writing all work on the local machine.

```powershell
python experiments\run_experiments.py --out-dir experiments\output_reproduction_smoke --rooms-per-method 2 --seeds 1 --ablation-rooms-per-cell 1 --stat-permutations 19
```

Validate the smoke output:

```powershell
python experiments\validate_outputs.py --out-dir experiments\output_reproduction_smoke --expected-generated 24 --expected-reference 111 --expected-ablation-rows 60 --expected-ablation-cell-n 1 --skip-paper
```

If `python` is not available on Windows, try `py`:

```powershell
py experiments\run_experiments.py --out-dir experiments\output_reproduction_smoke --rooms-per-method 2 --seeds 1 --ablation-rooms-per-cell 1 --stat-permutations 19
```

## Full Experiment

Run the full experiment only after the smoke test passes. The reference
configuration is recorded in:

```text
experiments/reproduction_config.json
```

The current paper uses the 30-seed reproduction run. Use this command unchanged
when reproducing the paper tables:

```powershell
python experiments\run_experiments.py --datasets zelda,loderunner --rooms-per-method 500 --seeds 30 --ablation-rooms-per-cell 200 --stat-permutations 9999 --out-dir experiments\output_reproduction_seed30
```

Validate the full output:

```powershell
python experiments\validate_outputs.py --out-dir experiments\output_reproduction_seed30 --expected-generated 180000 --expected-reference 111 --expected-ablation-rows 12000 --expected-ablation-cell-n 200 --expect-standard-config --skip-paper
```

## Optional Budget and Novelty Sweeps

These sweeps support fair-budget and novelty-pressure analysis for QI, GA, and
SA. They are not needed for a basic dataset smoke test.

```powershell
python experiments\run_experiments.py --datasets zelda,loderunner --seeds 30 --sweep-rooms-per-cell 200 --run-budget-sweep --run-novelty-sweep --sweep-only --out-dir experiments\output_reproduction_seed30
```

This adds:

```text
combined_budget_sweep_detailed.csv
combined_budget_sweep_summary.csv
combined_novelty_sweep_detailed.csv
combined_novelty_sweep_summary.csv
```

Validate the full output with sweeps:

```powershell
python experiments\validate_outputs.py --out-dir experiments\output_reproduction_seed30 --expected-generated 180000 --expected-reference 111 --expected-ablation-rows 12000 --expected-ablation-cell-n 200 --expected-budget-sweep-rows 180000 --expected-novelty-sweep-rows 144000 --expected-sweep-cell-n 200 --expect-standard-config --skip-paper
```

## Vector Figures

Figures for paper or report use must be vector PDF files. Do not use PNG raster
figures for final submission artifacts.

After a full run, regenerate vector figures locally:

```powershell
python experiments\generate_vector_figures.py --out-dir experiments\output_reproduction_seed30 --paper-figures paper\figures
```

If only validating the dataset pipeline, figure generation is optional.

## Optional Super Mario Bros Domain

The experiment runner supports `mario` as an optional third domain. Because
Super Mario Bros processed levels are long platformer maps rather than fixed
rooms, the loader slices them into non-overlapping `14 x 16` windows and uses a
left-to-right structural reachability proxy for playability.

Smoke test the three-domain setup:

```powershell
python experiments\run_experiments.py --datasets zelda,loderunner,mario --out-dir experiments\output_mario_domain_smoke --rooms-per-method 2 --seeds 1 --ablation-rooms-per-cell 1 --stat-permutations 19 --skip-ablation
python experiments\validate_outputs.py --out-dir experiments\output_mario_domain_smoke --expected-generated 36 --expected-reference 149 --skip-paper
```

Run a separate three-domain full experiment only when you intend to produce a
new extended result set:

```powershell
python experiments\run_experiments.py --datasets zelda,loderunner,mario --rooms-per-method 500 --seeds 30 --ablation-rooms-per-cell 200 --stat-permutations 9999 --out-dir experiments\output_reproduction_seed30_mario
python experiments\validate_outputs.py --out-dir experiments\output_reproduction_seed30_mario --expected-generated 270000 --expected-reference 149 --expected-ablation-rows 18000 --expected-ablation-cell-n 200 --skip-paper
```

The standard reproduction config remains the two-domain Zelda/Lode Runner
configuration, so skip `--expect-standard-config` for this optional extension.

## Optional Mini Human Study

The optional mini human study uses generated outputs from the full run. It
creates a blinded stimulus pack for 15--20 participants. New participant-facing
work should use the simplified playtest workflow in `human_study_playtest/`.
The older static visual-rating workflow is preserved under
`human_study_archive/static_perceptual_study_2026-06-26/`.

Create the blinded pack:

```powershell
python experiments\create_human_study_pack.py --input-csv experiments\output_reproduction_seed30\combined_results_detailed.csv --out-dir human_study\study_pack_seed2026 --playtest-ready
```

The pack contains public survey materials plus a private answer key:

```text
human_study/study_pack_seed2026/
  stimuli/
  README_FOR_PLAYTEST_BUILDER.md
  stimuli_manifest_blinded.csv
  coordinator_notes_private.md
  answer_key_private.csv
```

Build and validate the simplified playable HTML study:

```powershell
python experiments\build_playtest_form.py --study-pack human_study\study_pack_seed2026 --out-dir human_study_playtest\playtest_pack_seed2026
python experiments\validate_playtest_study.py --source-study-pack human_study\study_pack_seed2026 --playtest-pack human_study_playtest\playtest_pack_seed2026
```

Share `human_study_playtest\playtest_pack_seed2026\playtest_form.html` with
participants. It logs completion, time, moves, failures, restarts, timeout
status, required collectibles, shortest safe path length, efficiency ratio, and
post-level ratings. Do not show `coordinator_notes_private.md` or
`answer_key_private.csv` to participants.

After exporting playtest responses as CSV, validate and analyze them:

```powershell
python experiments\validate_playtest_study.py --source-study-pack human_study\study_pack_seed2026 --playtest-pack human_study_playtest\playtest_pack_seed2026 --responses human_study_playtest\responses.csv
python experiments\analyze_playtest_study.py --responses human_study_playtest\responses.csv --answer-key human_study\study_pack_seed2026\answer_key_private.csv --out-dir human_study_playtest\results_seed2026
```

The playtest is a goal-oriented grid-navigation proxy, not a faithful
implementation of Zelda or Lode Runner mechanics.

The legacy static visual-rating survey is preserved only in
`human_study_archive/static_perceptual_study_2026-06-26/`.

## Expected Full Output

After the full run, check:

```text
experiments/output_reproduction_seed30/
  combined_results_detailed.csv
  combined_results_summary.csv
  combined_statistical_tests.csv
  combined_ablation_detailed.csv
  combined_ablation_summary.csv
  figures/*.pdf
  zelda/
  loderunner/
```

## Reproducibility Notes

- Content metrics are seeded and should be reproducible with the same dataset,
  code commit, and command.
- The paper configuration uses seeds 42--71, 9,999 statistical permutations,
  180,000 generated main rows, 12,000 ablation rows, 180,000 budget-sweep rows,
  and 144,000 novelty-sweep rows.
- The default `novelty` column uses a 2x2 n-gram Jensen-Shannon metric because
  cell-wise Hamming distance is overly sensitive to spatial shifts. The legacy
  Hamming value remains available as `novelty_hamming`.
- The public experiment runner includes optimized sampling and metric code for
  the 30-seed Lode Runner run; keep these optimizations unless replacing them
  with an equivalent validated implementation.
- `generation_time` depends on CPU and local environment, so compare it as a
  trend rather than as an exact value across computers.
- If a full run is interrupted, prefer rerunning with a new `--out-dir` to avoid
  mixing old and new outputs.
- Generated outputs, dataset files, paper files, and internal notes must remain
  uncommitted.
