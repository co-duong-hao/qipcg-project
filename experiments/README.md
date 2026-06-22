# Experiment Reproduction Pipeline

Main script:

- `run_experiments.py`

Team-facing run guide:

- `../REPRODUCIBILITY_GUIDE.md`

The current pipeline uses two processed VGLC domains, an 80/20 train-test split,
six generators, train-reference novelty, seed-level permutation tests,
Holm-Bonferroni-adjusted p-values, and ablation outputs.

Main final output target:

- `output_reproduction_seed30/`

Important artifacts:

- `output_reproduction_seed30/run_config_main.json`
- `output_reproduction_seed30/run_config_ablation.json`
- `output_reproduction_seed30/combined_results_detailed.csv`
- `output_reproduction_seed30/combined_results_summary.csv`
- `output_reproduction_seed30/combined_statistical_tests.csv`
- `output_reproduction_seed30/combined_ablation_detailed.csv`
- `output_reproduction_seed30/combined_ablation_summary.csv`
- `output_reproduction_seed30/figures/`
- `output_reproduction_seed30/zelda/`
- `output_reproduction_seed30/loderunner/`

The fair-budget main configuration uses:

- datasets: `zelda`, `loderunner`
- methods: `uniform_random`, `dataset_prior_random`, `positional_prior_random`, `quantum_inspired`, `genetic_algorithm`, `simulated_annealing`
- 500 generated levels per method per seed
- 30 seeds, seed range 42--71
- QI population 8, iterations 3, total 24 fitness evaluations
- GA population 8, generations 2, total 24 fitness evaluations
- SA steps 23, total 24 fitness evaluations
- statistical tests: 9,999 permutations
- ablation: 6 variants x 5 K values x 200 samples per cell x 2 datasets
- optional budget sweep: QI/GA/SA at 8, 16, 24, 32, and 64 fitness evaluations
- optional novelty sweep: QI/GA/SA at novelty weights 0, 25, 50, and 100
- reference configuration: `experiments/reproduction_config.json`

Content metrics are seeded and should be reproducible with the same dataset and
commit. `generation_time` is machine-dependent and should be compared as a
trend only. The runner includes optimized sampling and metric code needed for
the 30-seed Lode Runner run.

Smoke validation command:

```powershell
& 'C:\Users\ADMIN\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' experiments\run_experiments.py --out-dir experiments\output_reproduction_smoke --rooms-per-method 2 --seeds 1 --ablation-rooms-per-cell 1 --stat-permutations 19
& 'C:\Users\ADMIN\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' experiments\validate_outputs.py --out-dir experiments\output_reproduction_smoke --expected-generated 24 --expected-reference 111 --expected-ablation-rows 60 --expected-ablation-cell-n 1 --skip-paper
```

Full final run command:

```powershell
& 'C:\Users\ADMIN\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' experiments\run_experiments.py --datasets zelda,loderunner --rooms-per-method 500 --seeds 30 --ablation-rooms-per-cell 200 --stat-permutations 9999 --out-dir experiments\output_reproduction_seed30
```

Optional fair-budget and novelty-pressure sweeps:

```powershell
& 'C:\Users\ADMIN\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' experiments\run_experiments.py --datasets zelda,loderunner --seeds 30 --sweep-rooms-per-cell 200 --run-budget-sweep --run-novelty-sweep --sweep-only --out-dir experiments\output_reproduction_seed30
```

This writes:

- `output_reproduction_seed30/combined_budget_sweep_detailed.csv`
- `output_reproduction_seed30/combined_budget_sweep_summary.csv`
- `output_reproduction_seed30/combined_novelty_sweep_detailed.csv`
- `output_reproduction_seed30/combined_novelty_sweep_summary.csv`

Validate full output plus optional sweeps:

```powershell
& 'C:\Users\ADMIN\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' experiments\validate_outputs.py --out-dir experiments\output_reproduction_seed30 --expected-generated 180000 --expected-reference 111 --expected-ablation-rows 12000 --expected-ablation-cell-n 200 --expected-budget-sweep-rows 180000 --expected-novelty-sweep-rows 144000 --expected-sweep-cell-n 200 --expect-standard-config --skip-paper
```

Regenerate vector paper figures after a full run:

```powershell
& 'C:\Users\ADMIN\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' experiments\generate_vector_figures.py --out-dir experiments\output_reproduction_seed30 --paper-figures paper\figures
```

Full final validation command:

```powershell
& 'C:\Users\ADMIN\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' experiments\validate_outputs.py --out-dir experiments\output_reproduction_seed30 --expected-generated 180000 --expected-reference 111 --expected-ablation-rows 12000 --expected-ablation-cell-n 200 --expect-standard-config --skip-paper
```
