# Mini Human Study Analysis Plan

## Research Question

Do human raters perceive levels from the quantum-inspired generator as more
playable, more stylistically consistent, more novel, or higher quality than
levels from GA, positional-prior sampling, and uniform random generation?

## Hypotheses

- H1: QI receives higher playability ratings than uniform random and
  positional-prior sampling.
- H2: QI receives style ratings competitive with GA and higher than uniform
  random.
- H3: QI may receive lower novelty ratings than GA or uniform random, matching
  the automatic novelty results.
- H4: Overall quality depends on the playability-style-novelty trade-off and
  should not be treated as proof of algorithmic dominance by itself.

## Unit of Analysis

The primary unit is the participant-level mean rating for each
dataset-method-metric cell. This avoids treating multiple ratings from the same
participant as independent samples.

## Statistical Tests

For each dataset and rating metric:

1. Compute participant-level means for each method.
2. Compare QI against each baseline using paired permutation tests when the
   same participant rated both methods.
3. Report mean difference, raw p-value, Holm-Bonferroni adjusted p-value, and
   Cliff's Delta over participant-level means.

## Reporting

Report mean +/- standard deviation by dataset, method, and metric. Interpret
the study as a small perceptual check, not a definitive user study. If
participant count is below 15, report it as pilot evidence only.
