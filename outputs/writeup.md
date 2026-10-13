# Bài viết ngắn — Lab 25 GPU FinOps

## Kết quả baseline và optimized

Pipeline dùng dữ liệu tổng hợp seed=25, 2,400 request/ngày. Kịch bản M5 có baseline
**$27,133.62/tháng**, optimized **$14,950.62/tháng**, tiết kiệm
**$12,183.00 (44.90%)**.
Riêng inference, cùng 7,533,027 token/ngày, chi phí giảm từ
**$6.488 xuống $1.126/1M-token**, tương đương **82.6%**.
Không gán chi phí training vào mẫu số token inference.

## Đóng góp từng đòn bẩy

- Inference cascade/cache/batch: **$1,211.69/tháng**.
- Purchasing spot/reserved: **$9,716.11/tháng**.
- Right-size theo map của lab: **$655.20/tháng**, chưa kiểm chứng SLA.
- Tắt idle: **$600.00/tháng**, suy từ một ngày telemetry.

Purchasing đóng góp USD lớn nhất vì hóa đơn GPU chiếm phần lớn baseline. Trong inference,
cascade lớn nhất vì chênh lệch giá model; cache chỉ giảm phần input cache-hit và batch giảm
50% hóa đơn còn lại cho request đủ điều kiện. Bảng attribution đầy đủ có trong report.md.
Reserved đã sửa để tính cả 24h/ngày thay vì chỉ giờ chạy, tránh đánh giá thấp chi phí commit.

## GPU-Util lie và ý nghĩa tài chính

Các GPU bị gắn cờ: **gpu-h100-4 (util 98.2%, MFU 0.194), gpu-a10g-1 (util 96.9%, MFU 0.268)**. GPU-Util cao cho biết có kernel hoạt động,
nhưng kernel có thể chờ bộ nhớ hoặc khai thác song song kém. MFU mới so FLOPs đạt được với peak;
MBU cần thiết khi đánh giá decode memory-bound. Đây là tín hiệu cần profile, chưa đủ kết luận
thay GPU nhỏ hơn sẽ giữ throughput. Idle đo được là **$20.00/ngày**.

## Hai extension đã triển khai và đo lường

**Ngân sách reasoning:** nhóm reasoning có 201 request
(8.38% traffic), tốn $1.3965/ngày
(16.46% chi phí) và 29787.74 Wh/ngày
(94.04% năng lượng ước lượng).
Cap 10% không đổi kết quả vì traffic đã dưới 10%. Cap 5% chuyển 81
request sang chế độ thường, tiết kiệm **$0.2261/ngày và 7879.63 Wh/ngày**.
Mô phỏng đảo hệ số output ×6 của generator và bỏ hệ số năng lượng ×80; chưa xác nhận chất lượng tương đương.
Routing đề xuất: escalation khi confidence <0.7, còn quota, và có đánh giá chất lượng;
không áp ngưỡng này như một thực tế đã được dataset chứng minh.

**Carbon-aware scheduling:** dùng đúng `days` của từng job interruptible, tổng năng lượng
**1789.00 kWh**. Vùng rẻ nhất là **us-east-wa**, sạch nhất
**europe-north1**, cân bằng 50/50 cost và carbon là **us-east-wa**.
Chuyển sang vùng sạch nhất giảm **626.15 kgCO2e**.
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
