# Blinded Playtest Protocol

This folder contains the replacement human-study workflow for a simplified
playable level test. It keeps the original blinding principle: participants see
only stimulus IDs, dataset labels, and playable tile boards. They must not see
generator names, automatic metrics, or `answer_key_private.csv`.

## Study Design

- Participants: target 15--20 people; report fewer than 15 as pilot evidence.
- Stimuli: 2 datasets x 4 methods x 3 levels = 24 levels per participant.
- Task: play each generated level in a simplified grid-navigation prototype.
- Completion: reach a goal tile `G`; if no `G` exists, reach a door tile `D`.
- Timeout: 90 seconds per level.
- Hazards: enemy `E` and trap `T` reset the player and increment failure count.
- Ratings after each level: difficulty, fun/engagement, and overall quality on a
  1--5 scale.

This is a proxy playtest, not a faithful implementation of the original Zelda
or Lode Runner rule sets. Paper wording should describe it as a simplified
grid-navigation playtest.

## Build The Playtest Form

Run from the project root after a blinded study pack exists:

```powershell
python experiments\build_playtest_form.py --study-pack human_study\study_pack_seed2026 --out-dir human_study_playtest\playtest_pack_seed2026
```

Validate that public files exist and do not leak method names:

```powershell
python experiments\validate_playtest_study.py --source-study-pack human_study\study_pack_seed2026 --playtest-pack human_study_playtest\playtest_pack_seed2026
```

Share `human_study_playtest/playtest_pack_seed2026/playtest_form.html` with
participants. Keep `human_study/study_pack_seed2026/answer_key_private.csv`
private until all responses are collected.

## Analyze Responses

After collecting one CSV per participant, combine them into one response CSV
with these columns:

```text
participant_id,stimulus_id,dataset_label,completed,time_seconds,moves,failures,restarts,timed_out,difficulty_rating,fun_rating,overall_rating,comment
```

Validate and analyze:

```powershell
python experiments\validate_playtest_study.py --source-study-pack human_study\study_pack_seed2026 --playtest-pack human_study_playtest\playtest_pack_seed2026 --responses human_study_playtest\responses.csv
python experiments\analyze_playtest_study.py --responses human_study_playtest\responses.csv --answer-key human_study\study_pack_seed2026\answer_key_private.csv --out-dir human_study_playtest\results_seed2026
```

The analysis writes:

- `playtest_cleaned_responses.csv`
- `playtest_summary.csv`
- `playtest_pairwise_tests.csv`

## Reporting Rule

Do not claim that this reproduces the original game mechanics. Report objective
playtest measures such as completion rate, time, moves, failures, and restarts
as results from a simplified playable proxy task.

