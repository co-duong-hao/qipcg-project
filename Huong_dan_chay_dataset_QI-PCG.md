# Hướng dẫn cho thành viên nhóm chạy dataset

## Summary

Thành viên trong nhóm có thể chạy lại pipeline từ thư mục project `quantum`.
Nên chạy theo 2 bước:

1. **Smoke test trước** để kiểm tra máy đọc được dataset, code chạy được, output sinh đúng.
2. **Full experiment** chỉ chạy khi cần tái tạo kết quả trong paper.

Dataset cần có sẵn trong project:

```text
TheVGLC/
  The Legend of Zelda/Processed/
  Lode Runner/Processed/
```

## Cách chạy

### 1. Mở PowerShell tại thư mục project

```powershell
cd "C:\Users\ADMIN\OneDrive\Desktop\New folder (2)\quantum"
```

Nếu chạy trên máy khác, thay path trên bằng thư mục project của máy đó.

## Smoke test trước

Smoke test dùng để kiểm tra code + dataset + output có chạy được không. Chạy nhanh hơn full run.

### Nếu dùng Python bundled trên máy hiện tại

```powershell
& 'C:\Users\ADMIN\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' experiments\zelda_pcg_experiment.py --out-dir experiments\output_fisat_fair_smoke --rooms-per-method 2 --seeds 1 --ablation-rooms-per-cell 1 --stat-permutations 19
```

Validate smoke output:

```powershell
& 'C:\Users\ADMIN\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' experiments\validate_q2_outputs.py --out-dir experiments\output_fisat_fair_smoke --expected-generated 24 --expected-reference 111 --expected-ablation-rows 60 --expected-ablation-cell-n 1 --skip-paper
```

### Nếu máy khác không có Python bundled

Dùng Python đã cài trên máy:

```powershell
python experiments\zelda_pcg_experiment.py --out-dir experiments\output_fisat_fair_smoke --rooms-per-method 2 --seeds 1 --ablation-rooms-per-cell 1 --stat-permutations 19
python experiments\validate_q2_outputs.py --out-dir experiments\output_fisat_fair_smoke --expected-generated 24 --expected-reference 111 --expected-ablation-rows 60 --expected-ablation-cell-n 1 --skip-paper
```

Nếu lệnh `python` không chạy, thử:

```powershell
py experiments\zelda_pcg_experiment.py --out-dir experiments\output_fisat_fair_smoke --rooms-per-method 2 --seeds 1 --ablation-rooms-per-cell 1 --stat-permutations 19
```

## Full run

Chỉ chạy khi smoke test pass. Full run có thể mất lâu.
File cấu hình chuẩn để đối chiếu nằm ở:

```text
experiments/fisat_main_config.json
```

```powershell
python experiments\zelda_pcg_experiment.py --datasets zelda,loderunner --rooms-per-method 500 --seeds 10 --ablation-rooms-per-cell 200 --stat-permutations 999 --out-dir experiments\output_fisat_main
```

Sau đó sinh lại ảnh vector PDF cho paper:

```powershell
python experiments\make_vector_figures.py --out-dir experiments\output_fisat_main --paper-figures paper\q2_figures
```

Validate full output:

```powershell
python experiments\validate_q2_outputs.py --out-dir experiments\output_fisat_main --expected-generated 60000 --expected-reference 111 --expected-ablation-rows 12000 --expected-ablation-cell-n 200 --expect-standard-config --skip-paper
```

## Optional: fair-budget sweep và novelty-pressure sweep

Phần này dùng khi muốn kiểm tra sâu hơn yêu cầu so sánh công bằng QI/GA/SA theo nhiều ngân sách fitness. Không cần chạy nếu chỉ smoke test dataset.

Chạy riêng sweep, không chạy lại main experiment và ablation:

```powershell
python experiments\zelda_pcg_experiment.py --datasets zelda,loderunner --seeds 10 --sweep-rooms-per-cell 200 --run-budget-sweep --run-novelty-sweep --sweep-only --out-dir experiments\output_fisat_main
```

Kết quả bổ sung:

```text
combined_budget_sweep_detailed.csv
combined_budget_sweep_summary.csv
combined_novelty_sweep_detailed.csv
combined_novelty_sweep_summary.csv
```

Budget sweep dùng `8,16,24,32,64` fitness evaluations cho QI/GA/SA. Novelty sweep dùng `novelty_weight = 0,25,50,100` tại 24 evaluations.

Validate full output kèm sweep:

```powershell
python experiments\validate_q2_outputs.py --out-dir experiments\output_fisat_main --expected-generated 60000 --expected-reference 111 --expected-ablation-rows 12000 --expected-ablation-cell-n 200 --expected-budget-sweep-rows 60000 --expected-novelty-sweep-rows 48000 --expected-sweep-cell-n 200 --expect-standard-config --skip-paper
```

## Kết quả cần kiểm tra

Sau full run, các file quan trọng nằm ở:

```text
experiments/output_fisat_main/
```

Cần có:

```text
combined_results_detailed.csv
combined_results_summary.csv
combined_statistical_tests.csv
combined_ablation_detailed.csv
combined_ablation_summary.csv
figures/*.pdf
zelda/
loderunner/
```

Paper dùng ảnh ở:

```text
paper/q2_figures/*.pdf
```

## Python dependencies

Nếu chạy trên máy khác, cần có các thư viện tối thiểu:

```text
numpy
pandas
Pillow
reportlab
pypdf
```

Cài bằng:

```powershell
pip install numpy pandas Pillow reportlab pypdf
```

## Khi nào dùng smoke test và full run?

| Nhu cầu | Lệnh nên dùng |
|---|---|
| Kiểm tra máy đọc được dataset không | Smoke test |
| Kiểm tra code có lỗi dependency không | Smoke test |
| Tái tạo số liệu trong paper | Full run |
| Sinh lại ảnh vector cho paper | `make_vector_figures.py` |
| Kiểm tra output có đủ rows/files không | `validate_q2_outputs.py` |
| Kiểm tra đúng cấu hình paper không | `validate_q2_outputs.py --expect-standard-config` |

## Lưu ý

- Không cần dùng raw image data; pipeline dùng VGLC processed text-grid.
- Không đổi tên folder `TheVGLC`, `The Legend of Zelda`, hoặc `Lode Runner`.
- Nếu chỉ muốn xem kết quả hiện có, không cần chạy full run lại; mở `experiments/output_fisat_main/`.
- Nếu full run bị dừng giữa chừng, nên chạy lại với `--out-dir` mới để tránh lẫn output cũ.
- Các metric nội dung có seed cố định nên có thể tái lập nếu cùng dataset, cùng commit, cùng command.
- `generation_time` phụ thuộc CPU/môi trường máy, nên không so khớp tuyệt đối giữa các máy.
