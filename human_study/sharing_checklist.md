# Human Study Sharing Checklist

Before sending anything out, run:

```powershell
python experiments\validate_human_study.py --study-pack human_study\study_pack_seed2026
```

## Safe To Share With Form Builder

- `README_FOR_FORM_BUILDER.md`
- `stimuli_manifest_blinded.csv`
- `stimuli/`
- `survey_questions.md`
- `rating_sheet_template.csv`
- `survey_form.html` if using the HTML route
- `consent_and_ethics.md`
- `participant_instructions.md`

## Keep Private Until Responses Are Complete

- `answer_key_private.csv`
- `coordinator_notes_private.md`
- any generated `human_study/results*/` folder
- any notes that mention generator names for specific stimulus IDs

## Before Analysis

Put the exported response CSV at:

```text
human_study/responses.csv
```

Then run:

```powershell
python experiments\validate_human_study.py --study-pack human_study\study_pack_seed2026 --responses human_study\responses.csv
python experiments\analyze_human_study.py --responses human_study\responses.csv --answer-key human_study\study_pack_seed2026\answer_key_private.csv --out-dir human_study\results_seed2026
```

Do not write paper claims from the human study until these commands pass on real
responses from 15--20 participants.
