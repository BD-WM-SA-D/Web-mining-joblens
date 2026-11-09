"""Danh mục kỹ năng cho mining-service: alias (ie/resources/skill_alias.csv) → skill_id, và trích span bằng từ điển.

skill_id theo contract silver.job_skills: ESCO URI nếu có, không thì 'joblens:<slug>'.
Cùng luật dò với baseline WM2 (annotation/preannotate_dict.py): bỏ nhóm "quá chung", alias ≤ 3 ký tự phân biệt hoa
thường, khớp dài nhất trước.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from annotation.preannotate_dict import ALIAS_CSV, SKIP_ALIASES, SKIP_NOTE_PREFIX, build_matcher

DICT_CONFIDENCE = 0.9  # từ điển không có xác suất; dùng một mức cố định để app lọc được bằng min_confidence


def slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.replace("đ", "d").replace("Đ", "D"))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = s.replace("+", "plus").replace("#", "sharp")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


@dataclass(frozen=True)
class Skill:
    skill_id: str
    label: str


class SkillCatalog:
    def __init__(self, path: Path = ALIAS_CSV) -> None:
        with path.open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        too_generic = {r["canonical"] for r in rows if (r.get("note") or "").startswith(SKIP_NOTE_PREFIX)}
        esco = {r["canonical"]: r["esco_uri"].strip() for r in rows if (r.get("esco_uri") or "").strip()}
        self.exact: dict[str, Skill] = {}  # alias ≤ 3 ký tự, giữ hoa thường
        self.folded: dict[str, Skill] = {}  # alias dài hơn, so khớp không phân biệt hoa thường
        for r in rows:
            canon = r["canonical"].strip()
            if canon in too_generic:
                continue
            skill = Skill(esco.get(canon) or f"joblens:{slug(canon)}", canon)
            for form in (r["alias"].strip(), canon):
                if form and form not in SKIP_ALIASES:
                    if len(form) <= 3:
                        self.exact[form] = skill
                    else:
                        self.folded[form.lower()] = skill
        forms = sorted({*self.exact, *(k for k in self.folded)}, key=lambda s: (-len(s), s))
        self.matcher = build_matcher(forms)

    def lookup(self, form: str) -> Skill | None:
        return self.exact.get(form) or self.folded.get(form.lower())

    def extract(self, text: str) -> list[tuple[int, int, str, Skill]]:
        out = []
        for m in self.matcher.finditer(text):
            skill = self.lookup(m.group())
            if skill:
                out.append((m.start(), m.end(), m.group(), skill))
        return out

    def skill_ids(self, text: str) -> set[str]:
        return {s.skill_id for *_, s in self.extract(text)}
