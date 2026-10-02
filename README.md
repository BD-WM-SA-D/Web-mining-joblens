# Web-mining-joblens (joblens-mining)

Phần khai phá dữ liệu web của dự án JobLens VN: thu thập và khử trùng tin tuyển dụng (WM1), trích xuất kỹ năng (WM2), khai phá quan điểm theo khía cạnh trên review công ty (WM3), mở rộng sang tìm kiếm/gợi ý/đồ thị kỹ năng (WM4–WM6).

> **Phạm vi đánh giá – môn Web Mining (<mã môn>, học kỳ 20261)**
>
> Dự án JobLens dùng chung hạ tầng dữ liệu với môn Big Data Storage and Processing và Phân tích thiết kế hệ thống (đã được giảng viên đồng ý ngày <dd/mm/yyyy>). Repo này chỉ chứa và đề nghị đánh giá các phần sau:
> - Spider, parser, crawl lịch sự, dedup (thuật toán và đánh giá).
> - Tập gán nhãn và guideline gán nhãn.
> - Các mô hình IE/ABSA/IR/RecSys/Graph, cùng thí nghiệm và metric mô hình.
>
> Các phần sau thuộc môn khác, nằm ở repo riêng và chỉ được nhắc tới để làm rõ bối cảnh:
> - Topic Kafka, bảng Iceberg, dbt/GX/Airflow, hạ tầng Kubernetes: môn Big Data.
> - Ca sử dụng, UML và cổng JobLens: môn Phân tích thiết kế hệ thống.

## Thành viên phụ trách

| Thành viên | MSSV | Vai trò trong repo này |
|---|---|---|
| <Họ tên> | <MSSV> | <…> |

## Chạy nhanh (không cần các repo khác)

```bash
# 1. Cài hợp đồng dữ liệu (pin version)
pip install git+https://github.com/BD-WM-SA-D/joblens@v<x.y.z>

# 2. Cấu hình
cp .env.example .env

# 3. Train/đánh giá trên VietJobs + fixtures, không cần Kafka/K8s
<lệnh chạy>
```

## Cấu trúc thư mục

```
crawler/       spiders, parser, dedup, producer ghi vào Kafka
ie/            WM2 – trích xuất kỹ năng (từ điển + regex → PhoBERT)
absa/          WM3 – khai phá quan điểm theo khía cạnh
retrieval/     WM4 – BM25, hybrid
recsys/        WM5 – gợi ý việc làm
graph/         WM6 – đồ thị kỹ năng
annotation/    guideline gán nhãn, chỉ số κ (không commit dữ liệu crawl thô hay file export nhãn)
experiments/   notebook (đã xóa output) + kết quả, ghi rõ snapshot Iceberg đã dùng
images/        Dockerfile cho job mô hình (skill-extractor, absa-scorer…)
models.yaml    danh mục model đã train: version, đường dẫn S3, metric, snapshot dữ liệu
docs/          nguồn báo cáo Web Mining
docs/adr/      ADR
```

## Tài liệu

- Báo cáo môn: [`docs/`](docs/)
- Quyết định kiến trúc: [`docs/adr/`](docs/adr/)
- Thuật ngữ: [`glossary.md` trong repo joblens](https://github.com/BD-WM-SA-D/joblens/blob/main/glossary.md)

## Phụ thuộc (chỉ để tham khảo, không thuộc phần chấm)

| Repo | Vai trò | Version đang dùng |
|---|---|---|
| [`joblens`](https://github.com/BD-WM-SA-D/joblens) (joblens-contracts) | Schema message/bảng, fixtures, glossary | v<x.y.z> |
| [`Big-Data-Storage-and-Processing-joblens`](https://github.com/BD-WM-SA-D/Big-Data-Storage-and-Processing-joblens) (joblens-platform) | Kafka, bảng Iceberg, Airflow chạy image mô hình | v<x.y.z> |

## Chốt số liệu cho báo cáo

| Tag | Ngày | Iceberg tag / snapshot | Ghi chú |
|---|---|---|---|
| `report-wm-v1` | <dd/mm/yyyy> | <…> | <version model> |

## Dữ liệu và giấy phép

Repo không chứa dữ liệu crawl, tập nhãn hay file model, những thứ này nằm trong `s3://joblens/…`. Crawler phải tôn trọng robots.txt, giới hạn ≤ 1 request/giây/domain và không truy cập trang cần đăng nhập. Dữ liệu mẫu nằm trong fixtures của repo `joblens`. Nếu dùng VietJobs (Pham Dinh et al., LREC 2026) thì phải trích dẫn theo giấy phép của dataset.
