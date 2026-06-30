# Human Study Results Report Template

Use this after collecting real responses from 15--20 participants and running
`experiments/analyze_human_study.py`.

## Study Setup

- Participants: TODO
- Stimuli: 24 levels, 2 datasets x 4 methods x 3 levels
- Methods compared: QI evolving prior, GA, positional prior, uniform random
- Blinding: participants saw only stimulus IDs, dataset names, and level grids
- Rating scale: 1--5 Likert scale
- Metrics: playability, style consistency, novelty, overall quality

## Response Quality

- Completed responses: TODO
- Excluded responses: TODO
- Exclusion reasons: TODO

## Summary Results

Paste or summarize `human_study_summary.csv`.

Recommended table columns:

```text
dataset, method, playability_mean, style_mean, novelty_mean, overall_mean
```

## Statistical Tests

Paste or summarize `human_study_pairwise_tests.csv`.

Report participant-level paired permutation tests comparing QI against each
baseline. Include:

- mean difference,
- raw p-value,
- Holm-adjusted p-value,
- Cliff's Delta.

## Interpretation

Use cautious language:

- If QI scores higher on playability/style, say that human ratings support the
  structural metric findings.
- If QI scores lower on novelty, connect this to the automatic novelty trade-off.
- If results are mixed or non-significant, report them as pilot evidence and
  avoid dominance claims.

## Paper Text Draft

Example wording to adapt only after real data exist:

> In a blinded mini study with TODO participants, raters evaluated 24 generated
> levels from QI, GA, positional-prior, and uniform generators on 1--5
> playability, style, novelty, and overall-quality scales. Participant-level
> paired permutation tests showed TODO. These results should be interpreted as
> pilot perceptual evidence rather than a definitive user study.
