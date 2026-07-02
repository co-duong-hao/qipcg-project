# Quantum-Inspired PCG Experiment Pipeline

This repository is the public reproducibility package for the QI-PCG experiment
pipeline. It contains the code and documentation needed to run the dataset
experiments, validate outputs, and regenerate vector figures from local output
files.

Repository scope:

- reproduce the current 30-seed experiment configuration;
- validate generated CSV outputs and statistical-test files;
- regenerate vector PDF figures locally when needed;
- prepare an optional blinded mini human-study pack from generated outputs;
- support team members and reviewers who want to inspect the experiment
  pipeline.

The repository intentionally does **not** include:

- the VGLC dataset,
- generated experiment outputs,
- paper files,
- internal review notes,
- paper/report figures.

For details, see `DATA_AVAILABILITY.md`.

## Current Paper Configuration

The current paper uses the 30-seed configuration:

```text
datasets: Zelda, Lode Runner
methods: 6 generators
seeds: 30, seed range 42--71
main generated rows: 180,000
held-out reference rows: 111
ablation rows: 12,000
budget sweep rows: 180,000
novelty-pressure sweep rows: 144,000
primary novelty metric: 2x2 n-gram Jensen-Shannon divergence
statistical permutations: 9,999
```

The implementation includes optimized sampling and metric code required for the
30-seed Lode Runner run. The primary `novelty` column uses the 2x2 n-gram
Jensen-Shannon metric by default; the legacy cell-wise Hamming value is exported
as `novelty_hamming` for comparison. Do not revert these optimizations unless
replacing them with an equivalent validated implementation.

## Dataset Setup

Place the VGLC dataset at the project root with this structure:

```text
TheVGLC/
  The Legend of Zelda/Processed/
  Lode Runner/Processed/
  Super Mario Bros/Processed/        # optional third-domain extension
```

Do not commit `TheVGLC/`; it is ignored by Git.

## Dataset Citation

The dataset itself is not part of this repository. When using VGLC data, cite
the VGLC paper:

```bibtex
@inproceedings{summerville2016vglc,
  title={The VGLC: The Video Game Level Corpus},
  author={Summerville, Adam James and Snodgrass, Sam and Mateas, Michael and Onta{\~n}{\'o}n, Santiago},
  booktitle={Proceedings of the Workshop on Procedural Content Generation},
  year={2016}
}
```

Also cite this repository when reporting results reproduced from this code. A
`CITATION.cff` file is included so GitHub can generate a citation entry.

## License

The code and documentation in this repository are released under the MIT
License. The VGLC dataset, generated outputs, paper files, paper/report figures,
and internal review notes are not included in this repository and are governed
by their own sources, owners, or project policies.

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

## Optional Super Mario Bros Domain

The runner also supports a third VGLC domain, `mario`, for cross-domain
structural validation beyond Zelda and Lode Runner. Super Mario Bros levels are
long platformer maps, so the adapter slices each processed level into
non-overlapping `14 x 16` windows and evaluates playability with a simple
left-to-right structural reachability proxy.

Three-domain smoke test:

```powershell
python experiments\run_experiments.py --datasets zelda,loderunner,mario --out-dir experiments\output_mario_domain_smoke --rooms-per-method 2 --seeds 1 --ablation-rooms-per-cell 1 --stat-permutations 19 --skip-ablation
python experiments\validate_outputs.py --out-dir experiments\output_mario_domain_smoke --expected-generated 36 --expected-reference 149 --skip-paper
```

Three-domain full run, if you want to create a new extended result set:

```powershell
python experiments\run_experiments.py --datasets zelda,loderunner,mario --rooms-per-method 500 --seeds 30 --ablation-rooms-per-cell 200 --stat-permutations 9999 --out-dir experiments\output_reproduction_seed30_mario
python experiments\validate_outputs.py --out-dir experiments\output_reproduction_seed30_mario --expected-generated 270000 --expected-reference 149 --expected-ablation-rows 18000 --expected-ablation-cell-n 200 --skip-paper
```

This is an extension path, not the current two-domain paper reproduction
configuration. Do not use `--expect-standard-config` when validating a
three-domain output unless the standard config is intentionally updated.

## Optional Mini Human Study

The repository includes optional materials for a blinded mini human study with
15--20 participants. This is not required for reproducing the paper tables.

The original static visual-rating workflow has been archived under
`human_study_archive/static_perceptual_study_2026-06-26/`. New participant-facing
work should use the simplified blinded playtest workflow in
`human_study_playtest/`.

Build the playtest form from the existing blinded stimulus pack:

```powershell
python experiments\build_playtest_form.py --study-pack human_study\study_pack_seed2026 --out-dir human_study_playtest\playtest_pack_seed2026
```

Validate the playtest files and analyze exported responses with:

```powershell
python experiments\validate_playtest_study.py --source-study-pack human_study\study_pack_seed2026 --playtest-pack human_study_playtest\playtest_pack_seed2026
python experiments\analyze_playtest_study.py --responses human_study_playtest\responses.csv --answer-key human_study\study_pack_seed2026\answer_key_private.csv --out-dir human_study_playtest\results_seed2026
```

The playtest is a goal-oriented grid-navigation proxy with computed start,
single final target, required collectibles, hazard penalties, and efficiency
logging. It is not a faithful
implementation of Zelda or Lode Runner mechanics.

After a full run exists, create a blinded 24-stimulus pack:

```powershell
python experiments\create_human_study_pack.py --input-csv experiments\output_reproduction_seed30\combined_results_detailed.csv --out-dir human_study\study_pack_seed2026 --playtest-ready
```

Validate the playtest files before sending them to anyone:

```powershell
python experiments\validate_playtest_study.py --source-study-pack human_study\study_pack_seed2026 --playtest-pack human_study_playtest\playtest_pack_seed2026
```

The legacy static visual-rating survey and its scripts are kept only in
`human_study_archive/static_perceptual_study_2026-06-26/`.
Generated study packs and results are local artifacts and are ignored by Git.

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
- Optional extension: TheVGLC/Super Mario Bros/Processed/

Primary scripts:
- experiments/run_experiments.py: runs the experiment pipeline
- experiments/validate_outputs.py: validates generated outputs
- experiments/generate_vector_figures.py: regenerates vector PDF figures from output CSVs
- experiments/create_human_study_pack.py: creates a blinded optional mini human-study pack from generated outputs
- experiments/build_playtest_form.py: creates a self-contained goal-oriented playable HTML study from the blinded pack
- experiments/validate_playtest_study.py: validates playtest blinding, pack balance, and response completeness
- experiments/analyze_playtest_study.py: analyzes exported playtest responses
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
- Super Mario Bros is supported as an optional third-domain extension named `mario`; it slices processed Mario levels into 14 x 16 windows and uses a left-to-right structural playability proxy. Do not treat this as part of the default paper reproduction unless explicitly requested.

Default workflow:
1. Install dependencies from requirements.txt.
2. Run smoke test first.
3. Validate smoke output.
4. Only run full experiment if smoke passes.
5. Validate full outputs with --expect-standard-config when reproducing paper numbers.
6. Run optional sweeps with --run-budget-sweep --run-novelty-sweep --sweep-only only when checking fair-budget and novelty-pressure analysis.
7. If figures are needed for paper/report, generate vector PDF figures with experiments/generate_vector_figures.py. Do not use PNG raster figures for final paper/report.
8. For optional human-study work, create a blinded pack with experiments/create_human_study_pack.py, build playtest_form.html with experiments/build_playtest_form.py, validate it with experiments/validate_playtest_study.py, and keep answer_key_private.csv hidden from participants until responses are complete.
9. Do not commit outputs, dataset, paper, human-study packs/results, or internal review notes.

Timing columns are machine-dependent; do not expect generation_time values to match exactly across computers.

When making changes, keep main runnable by smoke test and update README/guide if commands change.
```

## Team Rules

- Keep `main` runnable by smoke test.
- Update this README or `REPRODUCIBILITY_GUIDE.md` if commands change.
- Do not commit dataset, output folders, paper files, or internal notes.
- Commit small, focused changes and include the command used to test them.
