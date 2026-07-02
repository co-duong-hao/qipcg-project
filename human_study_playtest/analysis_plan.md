# Blinded Playtest Analysis Plan

## Research Question

When participants play generated levels in a goal-oriented grid-navigation task,
do levels from the quantum-inspired generator produce better completion,
efficiency, failure, difficulty, fun, or overall-quality outcomes than levels
from GA, positional-prior sampling, and uniform random generation?

## Primary Measures

- Completion rate (`completed`).
- Time to completion for completed levels (`time_seconds_completed`).
- Moves, failures, and restarts.
- Required collectibles, collected count, shortest safe path length, and
  movement-efficiency ratio.
- Post-level difficulty, fun/engagement, and overall quality ratings.

## Unit Of Analysis

The primary unit is the participant-level mean for each dataset-method-metric
cell. This avoids treating multiple levels from the same participant as fully
independent observations.

## Statistical Tests

For each dataset and metric:

1. Compute participant-level means for each method.
2. Compare QI against each baseline using paired permutation tests when the same
   participant has data for both methods.
3. Report mean difference, raw p-value, Holm-Bonferroni adjusted p-value, and
   Cliff's Delta.

## Interpretation

Interpret the results as a goal-oriented simplified playtest proxy. Strong
claims about the original commercial game rule sets require a faithful game
implementation or a separate study.
