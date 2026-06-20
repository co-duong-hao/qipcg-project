# Reproducibility Guide

This guide explains how to reproduce the dataset experiments for the QI-PCG
project. The repository does not include the dataset, generated outputs, paper
files, or internal review notes.

## Dataset Layout

Place the VGLC dataset at the project root:

```text
TheVGLC/
  The Legend of Zelda/Processed/
  Lode Runner/Processed/
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

Use this command unchanged when reproducing the paper tables:

```powershell
python experiments\run_experiments.py --datasets zelda,loderunner --rooms-per-method 500 --seeds 10 --ablation-rooms-per-cell 200 --stat-permutations 999 --out-dir experiments\output_reproduction_main
```

Validate the full output:

```powershell
python experiments\validate_outputs.py --out-dir experiments\output_reproduction_main --expected-generated 60000 --expected-reference 111 --expected-ablation-rows 12000 --expected-ablation-cell-n 200 --expect-standard-config --skip-paper
```

## Optional Budget and Novelty Sweeps

These sweeps support fair-budget and novelty-pressure analysis for QI, GA, and
SA. They are not needed for a basic dataset smoke test.

```powershell
python experiments\run_experiments.py --datasets zelda,loderunner --seeds 10 --sweep-rooms-per-cell 200 --run-budget-sweep --run-novelty-sweep --sweep-only --out-dir experiments\output_reproduction_main
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
python experiments\validate_outputs.py --out-dir experiments\output_reproduction_main --expected-generated 60000 --expected-reference 111 --expected-ablation-rows 12000 --expected-ablation-cell-n 200 --expected-budget-sweep-rows 60000 --expected-novelty-sweep-rows 48000 --expected-sweep-cell-n 200 --expect-standard-config --skip-paper
```

## Vector Figures

Figures for paper or report use must be vector PDF files. Do not use PNG raster
figures for final submission artifacts.

After a full run, regenerate vector figures locally:

```powershell
python experiments\generate_vector_figures.py --out-dir experiments\output_reproduction_main --paper-figures paper\figures
```

If only validating the dataset pipeline, figure generation is optional.

## Expected Full Output

After the full run, check:

```text
experiments/output_reproduction_main/
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
- `generation_time` depends on CPU and local environment, so compare it as a
  trend rather than as an exact value across computers.
- If a full run is interrupted, prefer rerunning with a new `--out-dir` to avoid
  mixing old and new outputs.
- Generated outputs, dataset files, paper files, and internal notes must remain
  uncommitted.
