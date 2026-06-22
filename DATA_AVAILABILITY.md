# Data and Artifact Availability

This repository does not include the VGLC dataset, generated experiment outputs,
paper files, paper figures, or internal review notes.

## Dataset

The experiments use processed text-grid levels from the Video Game Level Corpus
(VGLC):

```text
TheVGLC/
  The Legend of Zelda/Processed/
  Lode Runner/Processed/
```

Place the dataset at the project root before running experiments. The dataset is
intentionally ignored by Git.

Please cite VGLC when using these levels:

```bibtex
@inproceedings{summerville2016vglc,
  title={The VGLC: The Video Game Level Corpus},
  author={Summerville, Adam James and Snodgrass, Sam and Mateas, Michael and Onta{\~n}{\'o}n, Santiago},
  booktitle={Proceedings of the Workshop on Procedural Content Generation},
  year={2016}
}
```

## Generated Outputs

Generated outputs are local artifacts and are not committed. The current paper
configuration writes to:

```text
experiments/output_reproduction_seed30/
```

Expected validated counts:

```text
main generated rows: 180,000
held-out reference rows: 111
ablation rows: 12,000
budget sweep rows: 180,000
novelty-pressure sweep rows: 144,000
```

## Paper and Figures

Paper source, compiled PDFs, and paper figures are intentionally kept outside
the public GitHub repository. Figures for paper/report use should be regenerated
locally as vector PDF files with:

```powershell
python experiments\generate_vector_figures.py --out-dir experiments\output_reproduction_seed30 --paper-figures paper\figures
```
