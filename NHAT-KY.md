# Nhật ký thay đổi – Web-mining-joblens

Chỉ ghi sự kiện đáng nhớ: đổi hợp đồng hoặc file cấu hình chung, ghép hệ thống, chốt số liệu, quyết định quan trọng. Việc thường ngày đã có lịch sử git. Mục mới đặt trên cùng, vài dòng là đủ – xem [repo-routing](https://github.com/BD-WM-SA-D/joblens/blob/main/docs/repo-routing.md), mục Nhật ký.

## 2026-10-12 (2) · Hoang Le

- **Sự cố crawl:** TopCV trả HTTP 429 từ ~20:40; spider bản cũ thử lại → 5.507 request (4.673 bị 429). Đã sửa: gặp 429/403 dừng ngay, tối thiểu 3 giây/request, giới hạn thử lại. Không crawl lại trong ngày bị 429. Chi tiết: `experiments/results.md`.
- **Chốt số liệu đợt 1:** 304 tin IT TopCV (`data/crawl/topcv/2026-10-12/`, không commit).
- AI: Claude Code (Claude Opus 5.5) – chạy crawl, phân tích sự cố, sửa spider; <người kiểm tra> đã kiểm tra

## 2026-10-12 · Hoang Le

- **Quyết định dữ liệu:** tin crawl (TopCV, ITviec) là dữ liệu chính; VietJobs chỉ dùng cho nhãn yếu, từ điển alias, baseline (joblens docs/13).
- **WM2:** tập test (~1.000 câu, người gán) lấy từ tin TopCV đã crawl. Đợt `skill_batch1` (VietJobs) dừng ở ~300 câu, dùng làm dev set / luyện guideline.
- Thêm `ie/vietjobs.py` (tập IT cố định `it_v1`), `ie/skill_alias.py` + `ie/resources/skill_alias.csv` (bản nháp tự sinh, chưa xem tay), `annotation/sample_skill_batch.py`, `annotation/guideline_skill.md` (bản 0.2), `annotation/label_studio_skill.xml`, `experiments/results.md`.
- Việc mới từ ADR 0002 (joblens): `mining-service` + stub theo `schemas/api/mining.v1.yaml`; ghi `sentence_text` vào `silver.review_aspects`.
- AI: Claude Code (Claude Opus 5.5) – script chuẩn bị dữ liệu, guideline, nháp từ điển; <người kiểm tra> đã kiểm tra

## 2026-10-02 · Hoang Le · chưa có PR

- **Tạo:** –
- **Sửa:** `.env.example` (C – thêm biến đăng nhập S3/Trino, `JOBLENS_SEARCH_URL`, ADR 0001 D7); `AGENTS.md` (C – phạm vi repo theo ADR 0001); `.gitignore`, `.pre-commit-config.yaml` (C – chỉ đổi dòng chú thích đầu file)
- **Xóa:** –
- **Lý do:** đồng bộ file cấu hình chung sau khi repo `joblens` thêm hợp đồng dữ liệu và ADR 0001
- **Ảnh hưởng repo khác:** đồng bộ cùng lúc ở cả 4 repo – xem `joblens/NHAT-KY.md`
- **AI:** Claude Code (Claude Opus 5.5) – soạn schema, contract, script, sửa docs theo phương án đề xuất của ADR 0001; <người kiểm tra> đã kiểm tra

## 2026-10-02 · Hoang Le · chưa có PR

- **Tạo:** `AGENTS.md`, `CLAUDE.md`, `.cursor/rules/joblens.mdc` (C – đồng bộ từ joblens, có dòng `ĐỒNG BỘ TỪ`)
- **Sửa:** –
- **Xóa:** –
- **Lý do:** quy tắc làm việc cho AI agent (Codex, Claude Code, Cursor): tra repo-routing trước khi tạo file, ghi nhật ký, những việc không được làm, phạm vi riêng của repo này
- **Ảnh hưởng repo khác:** đồng bộ cùng lúc ở cả 4 repo – xem `joblens/NHAT-KY.md`
- **AI:** Claude Code (Claude Opus 5.5) – soạn quy tắc và script đồng bộ; <người kiểm tra> đã kiểm tra

## 2026-10-02 · Hoang Le · không qua PR (giai đoạn khởi tạo)

- **Tạo:** `NHAT-KY.md` (D)
- **Sửa:** `.gitignore`, `.pre-commit-config.yaml`, `.env.example`, `.gitattributes`, `CONTRIBUTING.md` (C – đồng bộ từ joblens, thêm dòng `ĐỒNG BỘ TỪ`; CONTRIBUTING thêm bước tra repo-routing và ghi nhật ký)
- **Xóa:** –
- **Lý do:** áp dụng quy ước file nào lên repo nào và nhật ký thay đổi
- **Ảnh hưởng repo khác:** đồng bộ cùng lúc ở cả 4 repo – xem `joblens/NHAT-KY.md`
- **AI:** Claude Code – dựng khung, soạn nội dung; <người kiểm tra> đã kiểm tra

## 2026-10-02 · Hoang Le · không qua PR (giai đoạn khởi tạo)

- **Tạo:** khung thư mục `crawler/`, `ie/`, `absa/`, `retrieval/`, `recsys/`, `graph/`, `annotation/`, `experiments/`, `images/`, `docs/adr/` (B); `models.yaml` (B); `README.md` (D); file cấu hình chung (C)
- **Sửa:** –
- **Xóa:** –
- **Lý do:** khởi tạo repo theo docs/project-plan/08; gộp commit "Initial commit" do GitHub tự sinh, giữ README của repo
- **Ảnh hưởng repo khác:** không
- **AI:** Claude Code – dựng khung, soạn nội dung; <người kiểm tra> đã kiểm tra
