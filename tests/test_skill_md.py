"""council-kr/SKILL.md가 공식 스킬 작성 규칙(설계 문서 §6.5)을 지키는지 검사한다."""
import re
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent / "council-kr"
SKILL_MD = SKILL_DIR / "SKILL.md"
DISCLAIMER = "같은 모델이 서로 다른 관점으로 낸 의견이며, 독립된 전문가 5인이 아닙니다."
FIRST_OR_SECOND_PERSON = ("나는", "내가", "당신", "너는", "제가", "저는", "I can", "You can")


def load():
    text = SKILL_MD.read_text(encoding="utf-8")
    match = re.match(r"---\n(.*?)\n---\n(.*)", text, re.S)
    assert match, "frontmatter(--- … ---)가 없습니다"
    front, body = match.groups()
    fields = {}
    for line in front.splitlines():
        m = re.match(r"([A-Za-z_-]+):\s*(.*)", line)
        if m:
            fields[m.group(1)] = m.group(2).strip()
    return text, fields, body


class SkillMdTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text, cls.fields, cls.body = load()

    def test_name_rules(self):
        name = self.fields.get("name", "")
        self.assertEqual(name, "council-kr")
        self.assertRegex(name, r"^[a-z0-9]+(-[a-z0-9]+)*$")
        self.assertLessEqual(len(name), 64)
        self.assertEqual(name, SKILL_DIR.name)
        for banned in ("claude", "anthropic"):
            self.assertNotIn(banned, name)

    def test_description_rules(self):
        desc = self.fields.get("description", "")
        self.assertTrue(desc)
        self.assertLessEqual(len(desc), 1024)
        self.assertNotIn("<", desc)
        self.assertNotIn(">", desc)
        self.assertRegex(desc, r"[가-힣]")
        self.assertIn("쓰지 않", desc)
        self.assertRegex(desc, r"다\.")
        for token in FIRST_OR_SECOND_PERSON:
            self.assertNotIn(token, desc)

    def test_distinct_triggers(self):
        desc = self.fields["description"]
        for phrase in ("위원회 열어줘", "자문단 소집", "council 돌려줘"):
            self.assertIn(phrase, desc)
        for sentence in re.split(r"(?<=\.)\s+", desc):
            if "검토해줘" in sentence:
                self.assertIn("않", sentence, "'검토해줘'는 쓰지 않는 경우 문장에서만 나와야 합니다")

    def test_frontmatter_has_compatibility_and_metadata(self):
        self.assertIn("compatibility", self.fields)
        self.assertIn("metadata:", self.text)

    def test_body_under_500_lines(self):
        self.assertLess(len(self.text.splitlines()), 500)

    def test_critical_section_on_top(self):
        headings = [l for l in self.body.splitlines() if l.startswith("## ")]
        self.assertTrue(headings)
        self.assertEqual(headings[0], "## 중요")
        section = self.body.split("## 중요", 1)[1].split("\n## ", 1)[0]
        for needle in ("한 번의 응답", "fork", "금지", "general-purpose", "11"):
            self.assertIn(needle, section)

    def test_three_modes_present(self):
        for mode in ("병렬", "프롬프트 묶음", "단일 세션"):
            self.assertIn(mode, self.body)

    def test_script_path_variable(self):
        self.assertIn("${CLAUDE_SKILL_DIR}/scripts/render_report.py", self.text)
        self.assertIn("이 SKILL.md가 있는 폴더", self.text)
        for line in self.text.splitlines():
            if "scripts" in line:
                self.assertNotIn("\\", line, f"역슬래시 경로: {line}")

    def test_output_path_and_disclaimer(self):
        self.assertIn("council-reports/", self.text)
        self.assertIn(DISCLAIMER, self.text)

    def test_references_one_level(self):
        links = re.findall(r"\]\((references/[^)#\s]+)\)", self.body)
        self.assertIn("references/advisors.md", links)
        self.assertIn("references/ko-context.md", links)
        for link in links:
            target = SKILL_DIR / link
            self.assertTrue(target.exists(), f"없는 참조: {link}")
            self.assertNotRegex(target.read_text(encoding="utf-8"), r"\]\([^)]*\.md",
                                f"{link}가 다른 파일을 다시 링크함(한 단계 깊이 규칙 위반)")

    def test_no_copied_original_phrases(self):
        for phrase in ("Lean fully into your assigned", "Don't hedge or try to be balanced",
                       "Always spawn all 5 advisors"):
            self.assertNotIn(phrase, self.text)

    def test_untrusted_marker(self):
        self.assertIn("UNTRUSTED", self.text)

    def test_no_readme_in_skill_folder(self):
        self.assertFalse((SKILL_DIR / "README.md").exists())


if __name__ == "__main__":
    unittest.main()
