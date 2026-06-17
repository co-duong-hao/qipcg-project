# qipcg-project

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
python experiments\zelda_pcg_experiment.py --out-dir experiments\output_fisat_fair_smoke --rooms-per-method 2 --seeds 1 --ablation-rooms-per-cell 1 --stat-permutations 19
```

Validate the smoke output:

```powershell
python experiments\validate_q2_outputs.py --out-dir experiments\output_fisat_fair_smoke --expected-generated 24 --expected-reference 111 --expected-ablation-rows 60 --expected-ablation-cell-n 1 --skip-paper
```

## Full Experiment

Only run the full experiment after the smoke test passes. This can take a long
time.

```powershell
python experiments\zelda_pcg_experiment.py --datasets zelda,loderunner --rooms-per-method 500 --seeds 10 --ablation-rooms-per-cell 200 --stat-permutations 999 --out-dir experiments\output_fisat_main
```

Validate the full output:

```powershell
python experiments\validate_q2_outputs.py --out-dir experiments\output_fisat_main --expected-generated 60000 --expected-reference 111 --expected-ablation-rows 12000 --expected-ablation-cell-n 200 --skip-paper
```

## Vector Figure Policy

Figures are generated artifacts and are not committed by default. If figures are
needed for a paper or report, they must be regenerated as **vector PDF** files.
Do not use PNG raster figures for final paper/report outputs because they are
easier to blur and harder to read.

After a full run, generate vector figures locally with:

```powershell
python experiments\make_vector_figures.py --out-dir experiments\output_fisat_main --paper-figures paper\q2_figures
```

If you only need to check the dataset pipeline, you do not need to generate
figures.

## Important Outputs

Generated outputs are local-only and ignored by Git. After a full run, check:

```text
experiments/output_fisat_main/
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
- experiments/zelda_pcg_experiment.py: runs the experiment pipeline
- experiments/validate_q2_outputs.py: validates generated outputs
- experiments/make_vector_figures.py: regenerates vector PDF figures from output CSVs

Default workflow:
1. Install dependencies from requirements.txt.
2. Run smoke test first.
3. Validate smoke output.
4. Only run full experiment if smoke passes.
5. If figures are needed for paper/report, generate vector PDF figures with experiments/make_vector_figures.py. Do not use PNG raster figures for final paper/report.
6. Do not commit outputs, dataset, paper, or internal review notes.

When making changes, keep main runnable by smoke test and update README/guide if commands change.
```

## Team Rules

- Keep `main` runnable by smoke test.
- Update this README or `Huong_dan_chay_dataset_QI-PCG.md` if commands change.
- Do not commit dataset, output folders, paper files, or internal notes.
- Commit small, focused changes and include the command used to test them.
