"""Reproducible Vietnamese analysis and write-up from mission results."""
from finops import pricing


def analysis(r1, r2, r3, r4, carbon, baseline, optimized, levers):
    stages = r2["stages_daily"]
    reason = r2["reasoning"]
    strict = r2["reasoning_strict"]
    groups = reason["groups"]
    rg = groups["reasoning"]
    total_wh = reason["energy_before_wh"]
    total_cost = reason["cost_before_usd"]
    n = r2["request_count"]
    lines = [
        "## Phạm vi và giả định kế toán",
        "",
        "Dữ liệu tổng hợp seed=25, snapshot giá tháng 6/2026; đây là bài mô phỏng, không phải báo giá hiện hành.",
        "M2 có 1 ngày request và được nhân 30 để ước lượng tháng. M3 giữ quy ước run-rate của lab:",
        "mọi workload lặp lại 30 ngày; cột `days` chỉ được dùng trong extension carbon cho thời lượng job thực tế.",
        "Reserved tính đủ 24 giờ/ngày theo giá 3 năm, với giả định đã có capacity cam kết phù hợp;",
        "không diễn giải một job ngắn là lý do đủ để ký hợp đồng 3 năm.",
        "",
        "Tổng trên dùng công thức M5 của lab: baseline = inference API + workload GPU; trừ bốn lever.",
        "Dữ liệu không có khóa nối request → job → GPU. Vì vậy phải giả định hai hóa đơn độc lập và",
        "idle/right-size chưa nằm trong purchasing. Đây là kịch bản tiềm năng, chưa khử trùng chi phí.",
        "Không cộng hai extension vào tổng vì reasoning thay đổi sản lượng token và điện có thể đã nằm trong giá thuê GPU.",
        f"Nếu chỉ tính inference + purchasing, mức sau tối ưu là **${baseline-levers['Inference (cascade/cache/batch)']-levers['Purchasing (spot/reserved)']:,.2f}/tháng**;",
        "hai lever telemetry còn lại phải đối soát trước khi ghi nhận. MFU thấp không tự chứng minh GPU nhỏ hơn đáp ứng SLA.",
        "",
        "## Kinh tế học inference — cùng sản lượng token",
        "",
        f"{n:,} request/ngày, **{r2['total_tokens']:,} token/ngày** (input + output, tính cả cached input một lần).",
        "$/1M-token dưới đây chỉ dùng chi phí inference M2; không chia chi phí training cho token inference.",
        "",
        "| Bước tích lũy | USD/ngày | USD/tháng | $/1M-token | Tiết kiệm tăng thêm USD/ngày |",
        "|---|---:|---:|---:|---:|",
    ]
    previous = stages["Baseline"]
    for name, cost in stages.items():
        lines.append(f"| {name} | {cost:.4f} | {cost*30:.2f} | {pricing.dollars_per_million(cost, r2['total_tokens']):.3f} | {previous-cost:.4f} |")
        previous = cost
    lines += [
        "",
        f"Inference giảm **{r2['savings_pct']:.1f}%**. Attribution tuần tự là cascade → cache → batch; đổi thứ tự có thể đổi phần đóng góp.",
        "Cascade đóng góp lớn nhất trong M2 vì model nhỏ có giá input 0.20 so với 3.00 và output 0.40 so với 15.00 USD/1M-token.",
        "Cache chỉ giảm giá phần input cache-hit; batch giảm 50% phần hóa đơn còn lại của request đủ điều kiện.",
        "0.5 × 0.1 = 0.05 chỉ đúng cho phần input được cache 100%, không phải toàn bộ request có output.",
        "Batch phù hợp eval offline, không phù hợp phản hồi chat đòi hỏi latency thấp. Chất lượng cascade cần được đánh giá trước khi áp dụng.",
        "",
        "## M1 — GPU-Util lie và idle",
        "",
        "| GPU bị gắn cờ | GPU-Util % | MFU | MBU |",
        "|---|---:|---:|---:|",
    ]
    for row in r1["lies"]:
        lines.append(f"| {row['gpu_id']} | {row['gpu_util_pct']} | {row['mfu']:.3f} | {row['mbu']:.3f} |")
    lines += [
        "",
        "GPU-Util đo thời gian có kernel hoạt động, không đo tỷ lệ FLOPs hữu ích. Kernel có thể hoạt động nhưng",
        "bị giới hạn bởi truy cập bộ nhớ hoặc thiếu song song. Telemetry này chỉ gắn cờ triệu chứng, chưa xác nhận nguyên nhân.",
        "Với inference decode, MFU thấp có thể bình thường; cần xem MBU, VRAM, throughput và p95 latency trước khi đổi GPU.",
        f"Idle dưới 10% util lãng phí **${r1['idle_waste_daily']:.2f}/ngày = ${r1['idle_waste_daily']*30:.2f}/tháng**,",
        f"bằng {r1['idle_waste_daily']*30/baseline:.2%} baseline tổng hợp. Tiềm năng right-size theo map lab: **${levers['Right-size util-lies']:.2f}/tháng**.",
        "",
        "## M3 — Purchasing",
        "",
        "| Job | GPU | Tier | On-demand USD/tháng | Optimized USD/tháng |",
        "|---|---|---|---:|---:|",
    ]
    for row in r3["recommendations"]:
        lines.append(f"| {row['job_id']} | {row['gpu_type']} | {row['tier']} | {row['on_demand']:.2f} | {row['optimized']:.2f} |")
    lines += [
        "",
        f"Purchasing: **${r3['on_demand_monthly']:,.2f} → ${r3['optimized_monthly']:,.2f}**, giảm {r3['savings_pct']:.1f}%.",
        "Spot dành cho job interruptible: số GPU-giờ hiệu dụng = giờ hữu ích × (1 + 0.03 + 0.05 × 0.5) = 1.055×.",
        "Phần tăng là checkpoint và rework. Reserved trả đủ 24h/ngày kể cả idle; policy mặc định dùng ngưỡng duty cycle 55%.",
        "Job infer-search chỉ chạy 18h/ngày: cần xác nhận tải ổn định và so cả giá 1 năm, 3 năm với rủi ro cam kết trước khi mua.",
        "",
        "## M4 — Allocation",
        "",
        "| Team | USD/ngày | Tỷ trọng |",
        "|---|---:|---:|",
    ]
    for team, cost in sorted(r4["by_team_exact"].items(), key=lambda item: -item[1]):
        lines.append(f"| {team} | {cost:.2f} | {cost/total_cost:.2%} |")
    lines += [
        "",
        f"Coverage đủ cả team/project: **{r4['tag_coverage']:.1%}**, qua gate 80% của lab; chargeback-ready = {r4['chargeback_ready']}.",
        "Cần đưa request thiếu project vào nhóm chờ đối soát thay vì tự suy diễn chủ sở hữu.",
        "`focus_export.csv` xuất toàn bộ 2,400 request. Đây là schema FOCUS-style tối thiểu của bài lab,",
        "không phải chứng nhận tuân thủ đầy đủ FOCUS. Chuẩn hóa cột chi phí giúp đối chiếu nhiều provider cùng một mô hình.",
        "",
        "## Extension 4 — Ngân sách reasoning",
        "",
        "| Traffic | Requests | Tokens | USD/ngày sau M2 | Wh/ngày ước lượng |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, g in groups.items():
        lines.append(f"| {name} | {g['requests']} | {g['tokens']} | {g['cost_usd']:.4f} | {g['energy_wh']:.2f} |")
    lines += [
        "",
        f"Reasoning chiếm **{rg['requests']/n:.2%} traffic**, **{rg['cost_usd']/total_cost:.2%} chi phí** và **{rg['energy_wh']/total_wh:.2%} năng lượng**.",
        "Năng lượng dùng 0.30 Wh/1K-token, reasoning nhân 80 theo giả định trong `sustainability.py`.",
        "Generator còn nhân output reasoning 6 lần; vì thế tỷ lệ năng lượng/request giữa hai nhóm không chỉ là 80×.",
        "Đây là mô hình minh họa, không phải số đo GPU hay khẳng định mọi reasoning model đều tiêu thụ 80×.",
        "",
        "| Trần reasoning | Request chuyển sang thường | USD/ngày sau cap | Wh/ngày sau cap | USD tiết kiệm/ngày | Wh tiết kiệm/ngày |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for cap in (reason, strict):
        lines.append(f"| {cap['cap_fraction']:.0%} | {cap['downgraded_requests']} | {cap['cost_after_usd']:.4f} | {cap['energy_after_wh']:.2f} | {cap['savings_usd']:.4f} | {cap['savings_wh']:.2f} |")
    lines += [
        "",
        "Trần 10% không đổi kết quả vì traffic đã dưới ngưỡng; trần 5% là sensitivity scenario bổ sung.",
        "Mô phỏng giữ request reasoning dài nhất, chuyển phần vượt ngân sách sang output/6 và bỏ hệ số năng lượng 80×,",
        "giữ nguyên input, model tier, cache và batch. Không xóa request. Độ dài chỉ là proxy do dataset không có confidence/quality.",
        "Quy tắc triển khai đề xuất: chỉ escalation khi confidence model nhỏ < 0.7 và còn quota reasoning;",
        "khi hết quota thì đưa tác vụ khó vào hàng chờ review. Ngưỡng 0.7 cần calibration, không được coi là kết quả đo.",
        "Chưa chứng minh chất lượng sau cap tương đương; vì output thay đổi, không dùng scenario này để báo giảm $/1M-token cùng sản lượng.",
        "",
        "## Extension 5 — Carbon-aware scheduling",
        "",
        "Chỉ chuyển job interruptible, dùng `hours_per_day × days × num_gpus × watts` (Wh).",
        "Giữ nguyên hardware/runtime giữa các vùng, PUE=1, chưa gồm checkpoint/rework, CPU, cooling và transfer.",
        "",
        "| Job | GPU-giờ | kWh | kgCO2e us-east-1 | kgCO2e vùng sạch nhất | kgCO2e giảm |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for j in carbon["jobs"]:
        lines.append(f"| {j['job_id']} | {j['gpu_hours']:.0f} | {j['energy_wh']/1000:.2f} | {j['carbon_before_g']/1000:.2f} | {j['carbon_after_g']/1000:.2f} | {j['carbon_saved_g']/1000:.2f} |")
    lines += [
        "",
        "| Vùng | USD/kWh | gCO2e/kWh | Điện USD | Carbon kgCO2e | Điểm cân bằng (thấp tốt) |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for reg in carbon["regions"]:
        lines.append(f"| {reg['region']} | {reg['usd_kwh']:.3f} | {reg['g_kwh']} | {reg['electricity_usd']:.2f} | {reg['carbon_g']/1000:.2f} | {reg['balanced_score']:.4f} |")
    lines += [
        "",
        f"Tổng **{carbon['energy_wh']/1000:.2f} kWh**. Rẻ nhất: **{carbon['cheapest']}**; sạch nhất: **{carbon['cleanest']}**; cân bằng: **{carbon['balanced']}**.",
        "Điểm cân bằng = 0.5 × (giá vùng / giá us-east-1 + carbon vùng / carbon us-east-1). Trọng số 50/50 là lựa chọn chính sách minh bạch.",
        f"Chuyển sang vùng sạch nhất giảm **{carbon['carbon_saved_g']/1000:.2f} kgCO2e**. Giá điện sạch nhất không thấp nhất:",
        "us-east-wa rẻ hơn europe-north1. Đây là chi phí điện thành phần, không phải giá thuê GPU theo vùng.",
        "Job training/offline chịu latency tốt hơn chat; trước di chuyển phải xét data residency, thời gian truyền dataset, egress và GPU availability.",
        "",
        "## Ba hành động ưu tiên cho NimbusAI",
        "",
        "1. Chốt owner/tag và nối request–job–GPU; đặt lịch tắt GPU idle, profile hai GPU bị gắn cờ và benchmark SLA trước right-size.",
        "2. Đưa job checkpointable lên spot; đối chiếu mức dùng thực tế với capacity reserved hiện có. Purchasing là lever lớn nhất theo USD trong kịch bản này.",
        "3. A/B test cascade → cache → batch theo quality/p95 latency; theo dõi $/1M-token, quota reasoning, rồi thí điểm chuyển training offline sang vùng sạch.",
        "",
        "## Tái lập",
        "",
        "```powershell",
        "python data/generate.py",
        "python missions/run_all.py",
        "python verify.py",
        "python -m pytest -q",
        "python -m pytest -q extension_checks.py",
        "```",
        "",
        "M5 tự tạo lại report.md, writeup.md, savings.png và extension_results.json; M4 tạo focus_export.csv.",
    ]
    return "\n".join(lines)


def writeup(r1, r2, r3, carbon, baseline, optimized, levers):
    reason, strict = r2["reasoning"], r2["reasoning_strict"]
    rg = reason["groups"]["reasoning"]
    lies = ", ".join(f"{r['gpu_id']} (util {r['gpu_util_pct']}%, MFU {r['mfu']:.3f})" for r in r1["lies"])
    return f"""# Bài viết ngắn — Lab 25 GPU FinOps

## Kết quả baseline và optimized

Pipeline dùng dữ liệu tổng hợp seed=25, 2,400 request/ngày. Kịch bản M5 có baseline
**${baseline:,.2f}/tháng**, optimized **${optimized:,.2f}/tháng**, tiết kiệm
**${baseline-optimized:,.2f} ({(1-optimized/baseline)*100:.2f}%)**.
Riêng inference, cùng {r2['total_tokens']:,} token/ngày, chi phí giảm từ
**${r2['baseline_per_m']:.3f} xuống ${r2['optimized_per_m']:.3f}/1M-token**, tương đương **{r2['savings_pct']}%**.
Không gán chi phí training vào mẫu số token inference.

## Đóng góp từng đòn bẩy

- Inference cascade/cache/batch: **${levers['Inference (cascade/cache/batch)']:,.2f}/tháng**.
- Purchasing spot/reserved: **${levers['Purchasing (spot/reserved)']:,.2f}/tháng**.
- Right-size theo map của lab: **${levers['Right-size util-lies']:,.2f}/tháng**, chưa kiểm chứng SLA.
- Tắt idle: **${levers['Kill idle GPUs']:,.2f}/tháng**, suy từ một ngày telemetry.

Purchasing đóng góp USD lớn nhất vì hóa đơn GPU chiếm phần lớn baseline. Trong inference,
cascade lớn nhất vì chênh lệch giá model; cache chỉ giảm phần input cache-hit và batch giảm
50% hóa đơn còn lại cho request đủ điều kiện. Bảng attribution đầy đủ có trong report.md.
Reserved đã sửa để tính cả 24h/ngày thay vì chỉ giờ chạy, tránh đánh giá thấp chi phí commit.

## GPU-Util lie và ý nghĩa tài chính

Các GPU bị gắn cờ: **{lies}**. GPU-Util cao cho biết có kernel hoạt động,
nhưng kernel có thể chờ bộ nhớ hoặc khai thác song song kém. MFU mới so FLOPs đạt được với peak;
MBU cần thiết khi đánh giá decode memory-bound. Đây là tín hiệu cần profile, chưa đủ kết luận
thay GPU nhỏ hơn sẽ giữ throughput. Idle đo được là **${r1['idle_waste_daily']:.2f}/ngày**.

## Hai extension đã triển khai và đo lường

**Ngân sách reasoning:** nhóm reasoning có {rg['requests']} request
({rg['requests']/r2['request_count']:.2%} traffic), tốn ${rg['cost_usd']:.4f}/ngày
({rg['cost_usd']/reason['cost_before_usd']:.2%} chi phí) và {rg['energy_wh']:.2f} Wh/ngày
({rg['energy_wh']/reason['energy_before_wh']:.2%} năng lượng ước lượng).
Cap 10% không đổi kết quả vì traffic đã dưới 10%. Cap 5% chuyển {strict['downgraded_requests']}
request sang chế độ thường, tiết kiệm **${strict['savings_usd']:.4f}/ngày và {strict['savings_wh']:.2f} Wh/ngày**.
Mô phỏng đảo hệ số output ×6 của generator và bỏ hệ số năng lượng ×80; chưa xác nhận chất lượng tương đương.
Routing đề xuất: escalation khi confidence <0.7, còn quota, và có đánh giá chất lượng;
không áp ngưỡng này như một thực tế đã được dataset chứng minh.

**Carbon-aware scheduling:** dùng đúng `days` của từng job interruptible, tổng năng lượng
**{carbon['energy_wh']/1000:.2f} kWh**. Vùng rẻ nhất là **{carbon['cheapest']}**, sạch nhất
**{carbon['cleanest']}**, cân bằng 50/50 cost và carbon là **{carbon['balanced']}**.
Chuyển sang vùng sạch nhất giảm **{carbon['carbon_saved_g']/1000:.2f} kgCO2e**.
So sánh đủ 5 vùng và từng job nằm trong report.md. Điện được ước lượng từ watts catalog,
PUE=1, chưa tính cooling, egress hay overhead spot. Không cộng điện lần nữa vào hóa đơn thuê GPU.

## Khuyến nghị và giới hạn

1. Chuẩn hóa tags, nối request–job–GPU, tắt idle và benchmark GPU bị gắn cờ trước khi right-size.
2. Ưu tiên spot cho job có checkpoint; dùng reserved khi dự báo tải và thời hạn cam kết phù hợp.
3. A/B test cascade/cache/batch theo chất lượng và latency; áp quota reasoning rồi thử chuyển training offline sang vùng sạch.

Tổng M5 là kịch bản công thức lab, không phải savings đã thực hiện: dữ liệu chưa nối các hóa đơn
nên chưa loại trừ khả năng overlap purchasing với idle/right-size hoặc API với self-hosted inference.
M3 là run-rate 30 ngày, còn carbon dùng thời lượng job thực tế. Hai extension được báo riêng.
Mọi giá và hệ số là snapshot minh họa của lab, không phải giá hiện hành.
"""
