# Mini Human Study Protocol

This folder contains the materials for an optional blinded mini human study for
the QI-PCG project. The goal is to collect subjective ratings from 15--20
participants on a small set of generated levels, comparing:

- `quantum_inspired`
- `genetic_algorithm`
- `positional_prior_random`
- `uniform_random`

The study is intentionally blind: participants should see only stimulus IDs,
dataset names, and level grids. They must not see generator names or automatic
metrics until after the study is complete.

Before sharing files, use `sharing_checklist.md` to separate public materials
from private method keys.

## Recommended Design

- Participants: 15--20 people.
- Stimuli: 2 datasets x 4 methods x 3 levels = 24 levels per participant.
- Rating dimensions:
  - Playability: whether the level appears playable/reachable.
  - Style consistency: whether the level looks like it belongs to the target
    game domain.
  - Novelty: whether the level looks distinct from the other shown levels while
    still being coherent.
  - Overall quality: optional but useful for summary reporting.
- Scale: 1--5 Likert scale.
- Estimated time: 15--25 minutes per participant.

## Generate a Blinded Study Pack

Run this from the project root after `experiments/output_reproduction_seed30`
exists:

```powershell
python experiments\create_human_study_pack.py --input-csv experiments\output_reproduction_seed30\combined_results_detailed.csv --out-dir human_study\study_pack_seed2026
```

Bundled Python example:

```powershell
& 'C:\Users\ADMIN\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' experiments\create_human_study_pack.py --input-csv experiments\output_reproduction_seed30\combined_results_detailed.csv --out-dir human_study\study_pack_seed2026
```

The output pack contains:

- `stimuli/`: text files shown to participants.
- `README_FOR_FORM_BUILDER.md`: safe setup instructions for the person
  building the survey.
- `stimuli_manifest_blinded.csv`: safe to share with the person building the
  Google Form.
- `rating_sheet_template.csv`: template for collected responses.
- `survey_questions.md`: text to paste into Google Forms or Microsoft Forms.
- `coordinator_notes_private.md`: private protocol notes with method balance.
- `answer_key_private.csv`: private mapping from stimulus IDs to methods and
  metrics. Do not share this file with participants.

Validate the pack before sharing any public files:

```powershell
python experiments\validate_human_study.py --study-pack human_study\study_pack_seed2026
```

Optional self-contained HTML form:

```powershell
python experiments\build_human_study_form.py --study-pack human_study\study_pack_seed2026
python experiments\validate_human_study.py --study-pack human_study\study_pack_seed2026
```

The HTML route writes `survey_form.html`. Participants can open it in a browser,
complete all ratings, and download a response CSV to send back to the study
coordinator.

## Analyze Responses

After collecting responses, export them as CSV and run:

```powershell
python experiments\validate_human_study.py --study-pack human_study\study_pack_seed2026 --responses human_study\responses.csv
```

```powershell
python experiments\analyze_human_study.py --responses human_study\responses.csv --answer-key human_study\study_pack_seed2026\answer_key_private.csv --out-dir human_study\results_seed2026
```

The analysis writes:

- `human_study_cleaned_responses.csv`
- `human_study_summary.csv`
- `human_study_pairwise_tests.csv`

The tests use participant-level means and paired permutation tests comparing
QI against each baseline. Holm-Bonferroni adjusted p-values are included.

## Reporting Rule

Do not add human-study results to the paper until actual participants have
completed the study and the response CSV has been analyzed. Until then, this
folder is a protocol and replication material only.
