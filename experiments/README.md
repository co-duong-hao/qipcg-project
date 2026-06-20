# FISAT Experiment Pipeline

Main script:

- `zelda_pcg_experiment.py`

Team-facing run guide:

- `../Huong_dan_chay_dataset_QI-PCG.md`

The current pipeline uses two processed VGLC domains, an 80/20 train-test split,
six generators, train-reference novelty, seed-level permutation tests,
Holm-Bonferroni-adjusted p-values, and ablation outputs.

Main final output target:

- `output_fisat_main/`

Important artifacts:

- `output_fisat_main/run_config_main.json`
- `output_fisat_main/run_config_ablation.json`
- `output_fisat_main/combined_results_detailed.csv`
- `output_fisat_main/combined_results_summary.csv`
- `output_fisat_main/combined_statistical_tests.csv`
- `output_fisat_main/combined_ablation_detailed.csv`
- `output_fisat_main/combined_ablation_summary.csv`
- `output_fisat_main/figures/`
- `output_fisat_main/zelda/`
- `output_fisat_main/loderunner/`

The fair-budget main configuration uses:

- datasets: `zelda`, `loderunner`
- methods: `uniform_random`, `dataset_prior_random`, `positional_prior_random`, `quantum_inspired`, `genetic_algorithm`, `simulated_annealing`
- 500 generated levels per method per seed
- 10 seeds
- QI population 8, iterations 3, total 24 fitness evaluations
- GA population 8, generations 2, total 24 fitness evaluations
- SA steps 23, total 24 fitness evaluations
- ablation: 6 variants x 5 K values x 200 samples per cell x 2 datasets
- optional budget sweep: QI/GA/SA at 8, 16, 24, 32, and 64 fitness evaluations
- optional novelty sweep: QI/GA/SA at novelty weights 0, 25, 50, and 100
- reference configuration: `experiments/fisat_main_config.json`

Content metrics are seeded and should be reproducible with the same dataset and
commit. `generation_time` is machine-dependent and should be compared as a
trend only.

Smoke validation command:

```powershell
& 'C:\Users\ADMIN\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' experiments\zelda_pcg_experiment.py --out-dir experiments\output_fisat_fair_smoke --rooms-per-method 2 --seeds 1 --ablation-rooms-per-cell 1 --stat-permutations 19
& 'C:\Users\ADMIN\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' experiments\validate_q2_outputs.py --out-dir experiments\output_fisat_fair_smoke --expected-generated 24 --expected-reference 111 --expected-ablation-rows 60 --expected-ablation-cell-n 1 --skip-paper
```

Full final run command:

```powershell
& 'C:\Users\ADMIN\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' experiments\zelda_pcg_experiment.py --datasets zelda,loderunner --rooms-per-method 500 --seeds 10 --ablation-rooms-per-cell 200 --stat-permutations 999 --out-dir experiments\output_fisat_main
```

Optional fair-budget and novelty-pressure sweeps:

```powershell
& 'C:\Users\ADMIN\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' experiments\zelda_pcg_experiment.py --datasets zelda,loderunner --seeds 10 --sweep-rooms-per-cell 200 --run-budget-sweep --run-novelty-sweep --sweep-only --out-dir experiments\output_fisat_main
```

This writes:

- `output_fisat_main/combined_budget_sweep_detailed.csv`
- `output_fisat_main/combined_budget_sweep_summary.csv`
- `output_fisat_main/combined_novelty_sweep_detailed.csv`
- `output_fisat_main/combined_novelty_sweep_summary.csv`

Validate full output plus optional sweeps:

```powershell
& 'C:\Users\ADMIN\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' experiments\validate_q2_outputs.py --out-dir experiments\output_fisat_main --expected-generated 60000 --expected-reference 111 --expected-ablation-rows 12000 --expected-ablation-cell-n 200 --expected-budget-sweep-rows 60000 --expected-novelty-sweep-rows 48000 --expected-sweep-cell-n 200 --expect-standard-config --skip-paper
```

Regenerate vector paper figures after a full run:

```powershell
& 'C:\Users\ADMIN\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' experiments\make_vector_figures.py --out-dir experiments\output_fisat_main --paper-figures paper\q2_figures
```

Full final validation command:

```powershell
& 'C:\Users\ADMIN\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' experiments\validate_q2_outputs.py --out-dir experiments\output_fisat_main --expected-generated 60000 --expected-reference 111 --expected-ablation-rows 12000 --expected-ablation-cell-n 200 --expect-standard-config --skip-paper
```
