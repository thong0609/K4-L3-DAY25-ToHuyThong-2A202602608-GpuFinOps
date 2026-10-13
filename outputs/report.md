# NimbusAI — GPU Cost Optimization Report

**Period:** monthly

**Baseline spend:** $27,133.62

**Optimized spend:** $14,950.62

**Projected savings:** $12,183.00  (**45%**; detailed: 44.90%)

## Savings by lever

| Lever | Savings (USD) |
|---|---|
| Inference (cascade/cache/batch) | $1,211.69 |
| Purchasing (spot/reserved) | $9,716.11 |
| Right-size util-lies | $655.20 |
| Kill idle GPUs | $600.00 |

## Sustainability

- Energy per query: 13.20 Wh
- Carbon per query: 5.015 gCO2e
- Cleanest region: europe-north1
- Cheapest electricity region in the lab catalog: us-east-wa

_Figures are June-2026 as-of snapshots; re-baseline before acting._

## Phạm vi và giả định kế toán

Dữ liệu tổng hợp seed=25, snapshot giá tháng 6/2026; đây là bài mô phỏng, không phải báo giá hiện hành.
M2 có 1 ngày request và được nhân 30 để ước lượng tháng. M3 giữ quy ước run-rate của lab:
mọi workload lặp lại 30 ngày; cột `days` chỉ được dùng trong extension carbon cho thời lượng job thực tế.
Reserved tính đủ 24 giờ/ngày theo giá 3 năm, với giả định đã có capacity cam kết phù hợp;
không diễn giải một job ngắn là lý do đủ để ký hợp đồng 3 năm.

Tổng trên dùng công thức M5 của lab: baseline = inference API + workload GPU; trừ bốn lever.
Dữ liệu không có khóa nối request → job → GPU. Vì vậy phải giả định hai hóa đơn độc lập và
idle/right-size chưa nằm trong purchasing. Đây là kịch bản tiềm năng, chưa khử trùng chi phí.
Không cộng hai extension vào tổng vì reasoning thay đổi sản lượng token và điện có thể đã nằm trong giá thuê GPU.
Nếu chỉ tính inference + purchasing, mức sau tối ưu là **$16,205.82/tháng**;
hai lever telemetry còn lại phải đối soát trước khi ghi nhận. MFU thấp không tự chứng minh GPU nhỏ hơn đáp ứng SLA.

## Kinh tế học inference — cùng sản lượng token

2,400 request/ngày, **7,533,027 token/ngày** (input + output, tính cả cached input một lần).
$/1M-token dưới đây chỉ dùng chi phí inference M2; không chia chi phí training cho token inference.

| Bước tích lũy | USD/ngày | USD/tháng | $/1M-token | Tiết kiệm tăng thêm USD/ngày |
|---|---:|---:|---:|---:|
| Baseline | 48.8742 | 1466.22 | 6.488 | 0.0000 |
| Cascade | 11.4756 | 344.27 | 1.523 | 37.3985 |
| Cache | 10.2792 | 308.38 | 1.365 | 1.1965 |
| Batch | 8.4846 | 254.54 | 1.126 | 1.7946 |

Inference giảm **82.6%**. Attribution tuần tự là cascade → cache → batch; đổi thứ tự có thể đổi phần đóng góp.
Cascade đóng góp lớn nhất trong M2 vì model nhỏ có giá input 0.20 so với 3.00 và output 0.40 so với 15.00 USD/1M-token.
Cache chỉ giảm giá phần input cache-hit; batch giảm 50% phần hóa đơn còn lại của request đủ điều kiện.
0.5 × 0.1 = 0.05 chỉ đúng cho phần input được cache 100%, không phải toàn bộ request có output.
Batch phù hợp eval offline, không phù hợp phản hồi chat đòi hỏi latency thấp. Chất lượng cascade cần được đánh giá trước khi áp dụng.

## M1 — GPU-Util lie và idle

| GPU bị gắn cờ | GPU-Util % | MFU | MBU |
|---|---:|---:|---:|
| gpu-h100-4 | 98.2 | 0.194 | 0.207 |
| gpu-a10g-1 | 96.9 | 0.268 | 0.302 |

GPU-Util đo thời gian có kernel hoạt động, không đo tỷ lệ FLOPs hữu ích. Kernel có thể hoạt động nhưng
bị giới hạn bởi truy cập bộ nhớ hoặc thiếu song song. Telemetry này chỉ gắn cờ triệu chứng, chưa xác nhận nguyên nhân.
Với inference decode, MFU thấp có thể bình thường; cần xem MBU, VRAM, throughput và p95 latency trước khi đổi GPU.
Idle dưới 10% util lãng phí **$20.00/ngày = $600.00/tháng**,
bằng 2.21% baseline tổng hợp. Tiềm năng right-size theo map lab: **$655.20/tháng**.

## M3 — Purchasing

| Job | GPU | Tier | On-demand USD/tháng | Optimized USD/tháng |
|---|---|---|---:|---:|
| job-train-llm | H100 | spot | 12000.00 | 7596.00 |
| job-train-embed | A100 | spot | 2148.00 | 1392.60 |
| job-finetune | H100 | spot | 900.00 | 569.70 |
| job-infer-chat | A10G | reserved | 4320.00 | 2592.00 |
| job-infer-rag | A100 | reserved | 3866.40 | 2160.00 |
| job-infer-search | L4 | reserved | 1728.00 | 1296.00 |
| job-dev-sandbox | A10G | spot | 480.00 | 202.56 |
| job-batch-eval | H100 | spot | 225.00 | 142.43 |

Purchasing: **$25,667.40 → $15,951.29**, giảm 37.9%.
Spot dành cho job interruptible: số GPU-giờ hiệu dụng = giờ hữu ích × (1 + 0.03 + 0.05 × 0.5) = 1.055×.
Phần tăng là checkpoint và rework. Reserved trả đủ 24h/ngày kể cả idle; policy mặc định dùng ngưỡng duty cycle 55%.
Job infer-search chỉ chạy 18h/ngày: cần xác nhận tải ổn định và so cả giá 1 năm, 3 năm với rủi ro cam kết trước khi mua.

## M4 — Allocation

| Team | USD/ngày | Tỷ trọng |
|---|---:|---:|
| assistant | 2.59 | 30.55% |
| search | 2.49 | 29.39% |
| eval | 1.79 | 21.15% |
| rag | 1.60 | 18.91% |

Coverage đủ cả team/project: **91.8%**, qua gate 80% của lab; chargeback-ready = True.
Cần đưa request thiếu project vào nhóm chờ đối soát thay vì tự suy diễn chủ sở hữu.
`focus_export.csv` xuất toàn bộ 2,400 request. Đây là schema FOCUS-style tối thiểu của bài lab,
không phải chứng nhận tuân thủ đầy đủ FOCUS. Chuẩn hóa cột chi phí giúp đối chiếu nhiều provider cùng một mô hình.

## Extension 4 — Ngân sách reasoning

| Traffic | Requests | Tokens | USD/ngày sau M2 | Wh/ngày ước lượng |
|---|---:|---:|---:|---:|
| reasoning | 201 | 1241156 | 1.3965 | 29787.74 |
| ordinary | 2199 | 6291871 | 7.0882 | 1887.56 |

Reasoning chiếm **8.38% traffic**, **16.46% chi phí** và **94.04% năng lượng**.
Năng lượng dùng 0.30 Wh/1K-token, reasoning nhân 80 theo giả định trong `sustainability.py`.
Generator còn nhân output reasoning 6 lần; vì thế tỷ lệ năng lượng/request giữa hai nhóm không chỉ là 80×.
Đây là mô hình minh họa, không phải số đo GPU hay khẳng định mọi reasoning model đều tiêu thụ 80×.

| Trần reasoning | Request chuyển sang thường | USD/ngày sau cap | Wh/ngày sau cap | USD tiết kiệm/ngày | Wh tiết kiệm/ngày |
|---|---:|---:|---:|---:|---:|
| 10% | 0 | 8.4846 | 31675.31 | 0.0000 | 0.00 |
| 5% | 81 | 8.2585 | 23795.67 | 0.2261 | 7879.63 |

Trần 10% không đổi kết quả vì traffic đã dưới ngưỡng; trần 5% là sensitivity scenario bổ sung.
Mô phỏng giữ request reasoning dài nhất, chuyển phần vượt ngân sách sang output/6 và bỏ hệ số năng lượng 80×,
giữ nguyên input, model tier, cache và batch. Không xóa request. Độ dài chỉ là proxy do dataset không có confidence/quality.
Quy tắc triển khai đề xuất: chỉ escalation khi confidence model nhỏ < 0.7 và còn quota reasoning;
khi hết quota thì đưa tác vụ khó vào hàng chờ review. Ngưỡng 0.7 cần calibration, không được coi là kết quả đo.
Chưa chứng minh chất lượng sau cap tương đương; vì output thay đổi, không dùng scenario này để báo giảm $/1M-token cùng sản lượng.

## Extension 5 — Carbon-aware scheduling

Chỉ chuyển job interruptible, dùng `hours_per_day × days × num_gpus × watts` (Wh).
Giữ nguyên hardware/runtime giữa các vùng, PUE=1, chưa gồm checkpoint/rework, CPU, cooling và transfer.

| Job | GPU-giờ | kWh | kgCO2e us-east-1 | kgCO2e vùng sạch nhất | kgCO2e giảm |
|---|---:|---:|---:|---:|---:|
| job-train-llm | 2240 | 1568.00 | 595.84 | 47.04 | 548.80 |
| job-train-embed | 200 | 80.00 | 30.40 | 2.40 | 28.00 |
| job-finetune | 36 | 25.20 | 9.58 | 0.76 | 8.82 |
| job-dev-sandbox | 352 | 52.80 | 20.06 | 1.58 | 18.48 |
| job-batch-eval | 90 | 63.00 | 23.94 | 1.89 | 22.05 |

| Vùng | USD/kWh | gCO2e/kWh | Điện USD | Carbon kgCO2e | Điểm cân bằng (thấp tốt) |
|---|---:|---:|---:|---:|---:|
| us-east-1 | 0.120 | 380 | 214.68 | 679.82 | 1.0000 |
| us-west-2 | 0.070 | 120 | 125.23 | 214.68 | 0.4496 |
| europe-north1 | 0.090 | 30 | 161.01 | 53.67 | 0.4145 |
| europe-central2 | 0.180 | 660 | 322.02 | 1180.74 | 1.6184 |
| us-east-wa | 0.055 | 90 | 98.39 | 161.01 | 0.3476 |

Tổng **1789.00 kWh**. Rẻ nhất: **us-east-wa**; sạch nhất: **europe-north1**; cân bằng: **us-east-wa**.
Điểm cân bằng = 0.5 × (giá vùng / giá us-east-1 + carbon vùng / carbon us-east-1). Trọng số 50/50 là lựa chọn chính sách minh bạch.
Chuyển sang vùng sạch nhất giảm **626.15 kgCO2e**. Giá điện sạch nhất không thấp nhất:
us-east-wa rẻ hơn europe-north1. Đây là chi phí điện thành phần, không phải giá thuê GPU theo vùng.
Job training/offline chịu latency tốt hơn chat; trước di chuyển phải xét data residency, thời gian truyền dataset, egress và GPU availability.

## Ba hành động ưu tiên cho NimbusAI

1. Chốt owner/tag và nối request–job–GPU; đặt lịch tắt GPU idle, profile hai GPU bị gắn cờ và benchmark SLA trước right-size.
2. Đưa job checkpointable lên spot; đối chiếu mức dùng thực tế với capacity reserved hiện có. Purchasing là lever lớn nhất theo USD trong kịch bản này.
3. A/B test cascade → cache → batch theo quality/p95 latency; theo dõi $/1M-token, quota reasoning, rồi thí điểm chuyển training offline sang vùng sạch.

## Tái lập

```powershell
python data/generate.py
python missions/run_all.py
python verify.py
python -m pytest -q
python -m pytest -q extension_checks.py
```

M5 tự tạo lại report.md, writeup.md, savings.png và extension_results.json; M4 tạo focus_export.csv.