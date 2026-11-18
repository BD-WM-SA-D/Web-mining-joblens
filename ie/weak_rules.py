"""Luật làm sạch nhãn yếu WM2 bản v2, lấy từ guideline gán nhãn bản 0.4 (annotation/guideline_skill.md).

Chỉ dựa vào guideline và ví dụ trong guideline, KHÔNG dựa vào lỗi quan sát trên test `skill_test1`.
Ba việc:
1. EXTRA_FORMS: khái niệm guideline nói là kỹ năng nhưng nhãn yếu v1 hay thiếu (cụm tiếng Việt, sản phẩm thiết kế
   trung gian, nghiệp vụ ngành, loại kiểm thử, loại quản lý chính thức…) → thêm vào danh sách dò.
2. STOP_FORMS: thứ guideline nói KHÔNG gán (tài liệu BA, thiết bị hạ tầng, bảo mật chung chung, từ chung, động từ
   chung + việc) → bỏ span nếu khớp nguyên văn.
3. Tách span qua dấu "/" (`Maven / Gradle` → hai span), trừ tên vốn viết liền bằng "/" (CI/CD, UI/UX…);
   bỏ `AI`/`cloud` khi chỉ là bổ ngữ đứng trước danh từ tiếng Anh (`AI solutions`, `AI Engineer`) hoặc sau "giải pháp".
"""

from __future__ import annotations

from annotation.export_bio import TOKEN_RE
from ie.baseline_dict import spans

# Guideline 0.4 mục 1 bảng "là kỹ năng", quy tắc 2–6, 8–10 và các ví dụ có span.
EXTRA_FORMS = [
    # sản phẩm thiết kế trung gian (quy tắc 2)
    "wireframe",
    "wireframes",
    "prototype",
    "prototypes",
    "mockup",
    "mockups",
    "user flow",
    "user flows",
    "storyboard",
    "storyboards",
    "sitemap",
    "sitemaps",
    "process flow",
    "process flows",
    # cloud / AI đứng riêng (quy tắc 3)
    "cloud",
    "AI",
    "AI tools",
    "AI Agents",
    "AI Agent",
    # bảo mật cụ thể (quy tắc 4)
    "network security",
    "bảo mật web",
    "bảo mật dữ liệu",
    "tấn công xâm nhập",
    "pentest",
    "DDOS",
    "Top 10 OWASP",
    "OWASP",
    "SAST",
    "DAST",
    "nghiên cứu lỗ hổng bảo mật",
    # quản lý chính thức (quy tắc 5)
    "quản lý dự án",
    "quản lý rủi ro",
    "stakeholder management",
    "quản lý thay đổi",
    "quản lý cấu hình",
    "incident management",
    "quản lý lỗi",
    "test management",
    "Inventory Management",
    # nghiệp vụ ngành (quy tắc 6)
    "game mechanics",
    "core loop",
    "meta progression",
    "cân bằng game",
    "level design",
    "eKYC",
    "AML",
    "Goods Receipt",
    "Goods Issue",
    "Purchase Order",
    "Invoice Verification",
    "physical inventory",
    "SAP Transport",
    # môn chuyên môn (quy tắc 8)
    "thiết kế hệ thống",
    "phân tích thiết kế hệ thống",
    "system design",
    "solution architecture",
    # có từ làm rõ (quy tắc 9 và mục "từ quá chung")
    "REST API",
    "RESTful API",
    "tối ưu database",
    "tối ưu truy vấn",
    "sao lưu dữ liệu",
    "phục hồi dữ liệu",
    "kiểm thử phần mềm",
    "kiểm thử tự động",
    "kiểm thử end-to-end",
    "kiểm tra hồi quy",
    "kiểm thử hồi quy",
    "unit test",
    "integration test",
    "viết test case",
    "tạo kịch bản kiểm thử",
    "A/B Testing",
    "quy trình phát triển phần mềm",
    "multi-agent systems",
    "thiết kế UI/UX",
    "thiết kế phần mềm",
    "thiết kế luồng dữ liệu",
    "phân tích yêu cầu",
    "phân tích yêu cầu nghiệp vụ",
    "phân tích nghiệp vụ",
    "phân tích dữ liệu",
    "phân tích hành vi người dùng",
    "data mapping",
    "ảo hóa",
    "indexing",
    "partitioning",
    "sharding",
    "cấu trúc dữ liệu và giải thuật",
    "cơ sở dữ liệu quan hệ",
    "chuẩn hóa dữ liệu",
    "review code",
    "OOP",
    "ETL",
]

# Guideline 0.4 quy tắc 1, 4, 7, 8, 9 (danh sách "không gán").
STOP_FORMS = [
    # tài liệu BA (quy tắc 1)
    "BRD",
    "SRS",
    "URD",
    "functional specification",
    "use case",
    "use cases",
    "user story",
    "user stories",
    "acceptance criteria",
    "test plan",
    "GDD",
    "Game Design Document",
    "SOP",
    "datasheet",
    "tài liệu kỹ thuật",
    "tài liệu đặc tả",
    "tài liệu thiết kế",
    "tài liệu hướng dẫn",
    # bảo mật chung chung (quy tắc 4)
    "bảo mật",
    "security",
    "an toàn thông tin",
    "ATTT",
    "an ninh mạng",
    "bảo mật hệ thống",
    "bảo mật thông tin",
    "Cybersecurity",
    # thiết bị hạ tầng (quy tắc 7)
    "switch",
    "switches",
    "router",
    "routers",
    "SAN switch",
    "NAS",
    "tủ Rack",
    "tủ đĩa",
    "camera",
    "Camera IP",
    "cáp mạng",
    "cáp quang",
    "Fiber",
    "máy chủ",
    "tape",
    "HPE StoreOnce",
    # động từ chung + việc (quy tắc 8)
    "viết phần mềm",
    "bảo trì phần mềm",
    "xử lý sự cố",
    "giám sát hệ thống",
    "bảo trì phần cứng",
    "quản trị hệ thống",
    "vận hành hệ thống",
    # từ chung đứng riêng (quy tắc 9)
    "test",
    "testing",
    "kiểm thử",
    "cơ sở dữ liệu",
    "API",
    "server",
    "storage",
    "network",
    "mạng",
    "mạng máy tính",
    "hệ thống mạng",
    "tự động hóa",
    "automation",
    "debug",
    "phần mềm",
    "phần cứng",
    "AI adoption",
]

# Tên vốn viết liền bằng "/" – không tách.
KEEP_SLASH = ["CI/CD", "UI/UX", "TCP/IP", "PL/SQL", "C/C++", "HTTP/2", "HTTP/1.1", "A/B Testing", "I/O", "TCP/UDP"]

_MODIFIED = {"ai", "cloud"}  # chỉ gán khi đứng riêng (quy tắc 3)
_CONNECT = {"và", "and", "or", "hoặc", "như", "trong", "với", "cho", "&"}


def _norm(s: str) -> str:
    return " ".join(TOKEN_RE.findall(s)).lower()


_STOP = {_norm(s) for s in STOP_FORMS}
_KEEP = {_norm(s).replace(" ", "") for s in KEEP_SLASH}


def _set(tags: list[str], a: int, b: int, value: bool) -> None:
    for i in range(a, b):
        tags[i] = ("B-SKILL" if i == a else "I-SKILL") if value else "O"


def refine(tokens: list[str], tags: list[str]) -> list[str]:
    """Áp luật v2 lên một câu đã gán nhãn yếu."""
    out = list(tags)
    split = False
    for a, b, text in spans(tokens, tags):
        key = _norm(text)
        if key in _STOP:
            _set(out, a, b, False)
            continue
        if key in _MODIFIED:
            nxt = tokens[b] if b < len(tokens) else ""
            prev = " ".join(tokens[max(0, a - 2) : a]).lower()
            if (nxt[:1].isalpha() and nxt.isascii() and nxt.lower() not in _CONNECT) or prev == "giải pháp":
                _set(out, a, b, False)
            continue
        if "/" in tokens[a:b] and key.replace(" ", "") not in _KEEP:
            split = True
            _set(out, a, b, False)
            start = a
            for i in range(a, b + 1):
                if i == b or tokens[i] == "/":
                    if i > start:
                        _set(out, start, i, True)
                    start = i + 1
    return refine(tokens, out) if split else out  # phần sau khi tách có thể khớp STOP
