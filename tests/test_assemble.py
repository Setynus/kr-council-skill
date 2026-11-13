"""하위 에이전트가 저장한 원문 파일에서 council.json을 조립하는 `assemble`을 시험한다.

손으로 council.json을 옮겨 쓰다 원문과 다른 문장이 들어간 사례(2026-11-13, 평가가→이)를 막는 것이
목적이라, 조립 결과의 문장이 원문과 글자 하나까지 같은지를 본다.
"""
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "kr-council-skill" / "scripts" / "render_report.py"
SKILL_MD = ROOT / "kr-council-skill" / "SKILL.md"
sys.path.insert(0, str(ROOT / "kr-council-skill" / "scripts"))

from render_report import ADVISOR_IDS, ADVISOR_NAMES, assemble, validate  # noqa: E402

MAPPING = {"A": "contrarian", "B": "first_principles", "C": "expansionist",
           "D": "outsider", "E": "executor"}
# 실제 사고가 난 문장. 조립 과정에서 한 글자도 바뀌면 안 된다.
TRICKY = "시스템 폰트가 임베드되어 한글 깨짐 평가가 오히려 강화된다는 주장도 근거가 없습니다."


def write_raw(raw, drop=None, broken=None, extra=None):
    letter_of = {v: k for k, v in MAPPING.items()}
    ids = list(ADVISOR_IDS)
    files = {"meta.json": {"title": "시험", "question": "질문입니다", "created": "2026-11-13 18:00",
                           "mode": "parallel", "mapping": MAPPING}}
    for i in ids:
        files[f"advisor-{i}.json"] = {"position": f"{i}의 입장", "reasons": ["근거1", "근거2", TRICKY],
                                      "risk": "위험", "blindspot": "놓친 점"}
    for n, i in enumerate(ids):
        files[f"reviews/{letter_of[i]}.json"] = {"strongest": letter_of[ids[(n + 1) % 5]], "strongest_why": TRICKY,
                                     "weakest": letter_of[ids[(n + 2) % 5]], "weakest_why": "맥락 부족",
                                     "missed": "모두가 놓친 점"}
    files["verdict.json"] = {"agree": ["병행"], "clash": [{"point": "시점", "sides": "먼저 vs 나중"}],
                             "blindspots": ["미확인"], "recommendation": "병행하십시오.",
                             "first_action": "샘플로 PDF를 만든다.", "confidence": "보통", "minority_kept": False}
    (raw / "reviews").mkdir(exist_ok=True)
    for name, obj in files.items():
        if name == drop:
            continue
        if extra and name == extra:
            obj = dict(obj, 규격밖="들어오면 안 되는 필드")
        text = json.dumps(obj, ensure_ascii=False)
        if name == broken:
            text = text[:-2]  # 마지막 문자열이 닫히지 않은 끝
        (raw / name).write_text(text, encoding="utf-8")


class AssembleTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.raw = Path(self._tmp.name)

    def test_cli_repair_keeps_original_and_assemble_discloses_it_in_title(self):
        write_raw(self.raw, broken="reviews/C.json")
        target = self.raw / "reviews" / "C.json"
        original = target.read_text(encoding="utf-8")
        run = subprocess.run([sys.executable, str(SCRIPT), "repair", "review", str(target)],
                             capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual((self.raw / "reviews" / "C.before-repair.json").read_text(encoding="utf-8"), original)
        data, errors = assemble(self.raw)
        self.assertEqual(errors, [])
        self.assertIn("자동 보정 1건", data["title"])
        self.assertIn("reviews/C", data["title"])

    def test_cli_repair_refuses_content_damage_and_leaves_file_untouched(self):
        write_raw(self.raw)
        target = self.raw / "verdict.json"
        target.write_text(target.read_text(encoding="utf-8")[:20], encoding="utf-8")
        before = target.read_text(encoding="utf-8")
        run = subprocess.run([sys.executable, str(SCRIPT), "repair", "verdict", str(target)],
                             capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(run.returncode, 2)
        self.assertEqual(target.read_text(encoding="utf-8"), before)
        self.assertFalse((self.raw / "verdict.before-repair.json").exists())

    def test_assembles_valid_council_json_with_verbatim_text(self):
        write_raw(self.raw)
        data, errors = assemble(self.raw)
        self.assertEqual(errors, [])
        self.assertEqual(validate(data), [])
        self.assertEqual([a["id"] for a in data["advisors"]], list(ADVISOR_IDS))
        self.assertEqual(data["advisors"][0]["reasons"][2], TRICKY)
        self.assertEqual(data["reviews"][0]["strongest_why"], TRICKY)
        self.assertEqual(data["advisors"][0]["name"], ADVISOR_NAMES["contrarian"])
        self.assertEqual(data["title"], "시험")

    def test_extra_fields_are_dropped_not_copied(self):
        write_raw(self.raw, extra="advisor-contrarian.json")
        data, errors = assemble(self.raw)
        self.assertEqual(errors, [])
        self.assertNotIn("규격밖", data["advisors"][0])
        write_raw(self.raw, extra="reviews/A.json")
        data, _ = assemble(self.raw)
        self.assertNotIn("규격밖", " ".join(data["reviews"][0]))

    def test_review_files_are_named_by_letter_and_mapped_back_to_advisors(self):
        write_raw(self.raw)
        self.assertFalse(any("review-" in p.name for p in self.raw.rglob("*.json")))
        data, _ = assemble(self.raw)
        self.assertEqual([r["reviewer"] for r in data["reviews"]], list(ADVISOR_IDS))

    def test_unclosed_file_is_reported_by_name_and_nothing_is_built(self):
        write_raw(self.raw, broken="reviews/C.json")
        data, errors = assemble(self.raw)
        self.assertIsNone(data)
        self.assertIn("reviews/C.json", " ".join(errors))
        self.assertIn("JSON", " ".join(errors))

    def test_missing_file_is_reported_by_name(self):
        write_raw(self.raw, drop="advisor-outsider.json")
        data, errors = assemble(self.raw)
        self.assertIsNone(data)
        self.assertIn("advisor-outsider.json", " ".join(errors))

    def test_all_problems_are_listed_at_once(self):
        write_raw(self.raw, drop="verdict.json", broken="advisor-executor.json")
        _, errors = assemble(self.raw)
        text = " ".join(errors)
        self.assertIn("verdict.json", text)
        self.assertIn("advisor-executor.json", text)

    def test_bad_meta_is_caught_by_validate(self):
        write_raw(self.raw)
        meta = json.loads((self.raw / "meta.json").read_text(encoding="utf-8"))
        meta["mode"] = "serial"
        (self.raw / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        data, errors = assemble(self.raw)
        self.assertIsNone(data)
        self.assertIn("mode", " ".join(errors))


class Cli(unittest.TestCase):
    def test_assemble_then_render(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "raw"
            raw.mkdir()
            write_raw(raw)
            out_json = Path(tmp) / "council.json"
            out_html = Path(tmp) / "council.html"
            run = lambda *a: subprocess.run([sys.executable, str(SCRIPT), *a], capture_output=True)
            ok = run("assemble", str(raw), "--out", str(out_json))
            self.assertEqual(ok.returncode, 0, ok.stderr.decode("utf-8", "replace"))
            self.assertEqual(run("render", str(out_json), "--out", str(out_html)).returncode, 0)
            self.assertIn(TRICKY, out_html.read_text(encoding="utf-8"))

    def test_broken_input_exits_2_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "raw"
            raw.mkdir()
            write_raw(raw, broken="verdict.json")
            out_json = Path(tmp) / "council.json"
            bad = subprocess.run([sys.executable, str(SCRIPT), "assemble", str(raw), "--out", str(out_json)],
                                 capture_output=True)
            self.assertEqual(bad.returncode, 2)
            self.assertIn("verdict.json", bad.stderr.decode("utf-8", "replace"))
            self.assertFalse(out_json.exists())


class NamesMatchSkillMd(unittest.TestCase):
    def test_script_names_equal_the_table_in_skill_md(self):
        text = SKILL_MD.read_text(encoding="utf-8")
        rows = {k: v for k, v in re.findall(r"^\| `(\w+)` \| ([^|]+?) \|", text, re.M) if k in ADVISOR_IDS}
        self.assertEqual(rows, ADVISOR_NAMES)


if __name__ == "__main__":
    unittest.main()
