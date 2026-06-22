# Quantum-Inspired PCG Experiment Pipeline

This repository contains the reproducible experiment pipeline for running and
validating the QI-PCG dataset experiments. It is meant for team members to clone,
install dependencies, place the dataset locally, and run smoke/full experiments.

The repository intentionally does **not** include:

- the VGLC dataset,
- generated experiment outputs,
- paper files,
- internal review notes,
- paper/report figures.

## Dataset Setup

Place the VGLC dataset at the project root with this structure:

```text
TheVGLC/
  The Legend of Zelda/Processed/
  Lode Runner/Processed/
```

Do not commit `TheVGLC/`; it is ignored by Git.

## Install Dependencies

```powershell
pip install -r requirements.txt
```

## Smoke Test

Run this first to confirm that Python, dependencies, and local dataset paths are
working:

```powershell
python experiments\run_experiments.py --out-dir experiments\output_reproduction_smoke --rooms-per-method 2 --seeds 1 --ablation-rooms-per-cell 1 --stat-permutations 19
```

Validate the smoke output:

```powershell
python experiments\validate_outputs.py --out-dir experiments\output_reproduction_smoke --expected-generated 24 --expected-reference 111 --expected-ablation-rows 60 --expected-ablation-cell-n 1 --skip-paper
```

## Full Experiment

Only run the full experiment after the smoke test passes. This can take a long
time.

The current paper uses the 30-seed reproduction configuration recorded in
`experiments/reproduction_config.json`. Use the command below unchanged when
trying to reproduce the paper tables. It can take a long time, so run the
smoke test first.

```powershell
python experiments\run_experiments.py --datasets zelda,loderunner --rooms-per-method 500 --seeds 30 --ablation-rooms-per-cell 200 --stat-permutations 9999 --out-dir experiments\output_reproduction_seed30
```

Validate the full output:

```powershell
python experiments\validate_outputs.py --out-dir experiments\output_reproduction_seed30 --expected-generated 180000 --expected-reference 111 --expected-ablation-rows 12000 --expected-ablation-cell-n 200 --expect-standard-config --skip-paper
```

## Optional Fair-Budget Sweeps

The main table uses one fair budget point: 24 fitness evaluations for QI, GA,
and SA. To reproduce the optional budget/novelty trade-off analysis without
rerunning the main experiment, run sweeps only:

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

Budget sweep uses `8,16,24,32,64` fitness evaluations for QI/GA/SA. Novelty
sweep uses novelty weights `0,25,50,100` at 24 evaluations.

After running the optional sweeps on top of `output_reproduction_seed30`, validate them
with:

```powershell
python experiments\validate_outputs.py --out-dir experiments\output_reproduction_seed30 --expected-generated 180000 --expected-reference 111 --expected-ablation-rows 12000 --expected-ablation-cell-n 200 --expected-budget-sweep-rows 180000 --expected-novelty-sweep-rows 144000 --expected-sweep-cell-n 200 --expect-standard-config --skip-paper
```

Most content metrics should be reproducible with the same dataset, code commit,
and command. `generation_time` is machine-dependent, so compare it as a trend
only, not byte-for-byte across different computers.

## Vector Figure Policy

Figures are generated artifacts and are not committed by default. If figures are
needed for a paper or report, they must be regenerated as **vector PDF** files.
Do not use PNG raster figures for final paper/report outputs because they are
easier to blur and harder to read.

After a full run, generate vector figures locally with:

```powershell
python experiments\generate_vector_figures.py --out-dir experiments\output_reproduction_seed30 --paper-figures paper\figures
```

If you only need to check the dataset pipeline, you do not need to generate
figures.

## Important Outputs

Generated outputs are local-only and ignored by Git. After a full run, check:

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

## Codex Context Prompt for Team Members

Copy this prompt into Codex when working on this repository:

```text
You are helping with the qipcg-project repository. This repo is only for running and validating the dataset experiment pipeline for the QI-PCG paper. Do not ask for paper files or private review files; they are intentionally not committed. The dataset is also not committed. Assume the user will place VGLC locally at ./TheVGLC with:
- TheVGLC/The Legend of Zelda/Processed/
- TheVGLC/Lode Runner/Processed/

Primary scripts:
- experiments/run_experiments.py: runs the experiment pipeline
- experiments/validate_outputs.py: validates generated outputs
- experiments/generate_vector_figures.py: regenerates vector PDF figures from output CSVs
- experiments/reproduction_config.json: records the paper reproduction configuration

Current paper context:
- The paper uses the 30-seed reproduction run, not the old 10-seed run.
- Main generated rows should be 180,000: 2 datasets x 6 methods x 30 seeds x 500 levels.
- Held-out reference rows should be 111.
- Ablation rows should be 12,000.
- Budget sweep rows should be 180,000.
- Novelty-pressure sweep rows should be 144,000.
- Statistical tests use 9,999 permutations.
- The public runner contains seed30 performance optimizations; do not revert them to the older slower implementation.

Default workflow:
1. Install dependencies from requirements.txt.
2. Run smoke test first.
3. Validate smoke output.
4. Only run full experiment if smoke passes.
5. Validate full outputs with --expect-standard-config when reproducing paper numbers.
6. Run optional sweeps with --run-budget-sweep --run-novelty-sweep --sweep-only only when checking fair-budget and novelty-pressure analysis.
7. If figures are needed for paper/report, generate vector PDF figures with experiments/generate_vector_figures.py. Do not use PNG raster figures for final paper/report.
8. Do not commit outputs, dataset, paper, or internal review notes.

Timing columns are machine-dependent; do not expect generation_time values to match exactly across computers.

When making changes, keep main runnable by smoke test and update README/guide if commands change.
```

## Team Rules

- Keep `main` runnable by smoke test.
- Update this README or `REPRODUCIBILITY_GUIDE.md` if commands change.
- Do not commit dataset, output folders, paper files, or internal notes.
- Commit small, focused changes and include the command used to test them.
