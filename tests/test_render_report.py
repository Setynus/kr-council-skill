import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "council-kr" / "scripts" / "render_report.py"
TEMPLATE = (ROOT / "council-kr" / "assets" / "report.html")
sys.path.insert(0, str(ROOT / "council-kr" / "scripts"))

from render_report import ADVISOR_IDS, make_mapping, render, validate  # noqa: E402

DISCLAIMER = "같은 모델이 서로 다른 관점으로 낸 의견이며, 독립된 전문가 5인이 아닙니다."

NAMES = {
    "contrarian": "반대자",
    "first_principles": "제1원리 사색가",
    "expansionist": "확장가",
    "outsider": "아웃사이더",
    "executor": "실행가",
}
MAPPING = {"A": "contrarian", "B": "first_principles", "C": "expansionist",
           "D": "outsider", "E": "executor"}


def sample():
    """정상 council.json 한 벌. 테스트가 이 값을 복사해 일부만 망가뜨린다."""
    letter_of = {v: k for k, v in MAPPING.items()}
    ids = list(ADVISOR_IDS)
    advisors = [
        {"id": i, "name": NAMES[i], "position": f"{NAMES[i]}의 입장",
         "reasons": ["근거1", "근거2", "근거3"], "risk": "위험", "blindspot": "놓친 점"}
        for i in ids
    ]
    reviews = []
    for n, rid in enumerate(ids):
        reviews.append({
            "reviewer": rid,
            "strongest": letter_of[ids[(n + 1) % 5]], "strongest_why": "근거가 구체적",
            "weakest": letter_of[ids[(n + 2) % 5]], "weakest_why": "맥락 부족",
            "missed": "모두가 놓친 점",
        })
    return {
        "title": "수제 쿠키 가격 결정", "question": "낱개와 세트 중 무엇에 집중할까?",
        "mode": "parallel", "created": "2026-11-10 20:00",
        "advisors": advisors, "mapping": dict(MAPPING), "reviews": reviews,
        "verdict": {
            "agree": ["세트 중심"], "clash": [{"point": "광고", "sides": "찬성 대 반대"}],
            "blindspots": ["배송비"], "recommendation": "세트에 집중한다",
            "first_action": "택배비 포함 원가표를 만든다",
            "confidence": "보통", "minority_kept": True,
        },
    }


class MappingTests(unittest.TestCase):
    def test_make_mapping_is_bijection(self):
        for _ in range(20):
            m = make_mapping()
            self.assertEqual(set(m), set("ABCDE"))
            self.assertEqual(set(m.values()), set(ADVISOR_IDS))

    def test_make_mapping_seed_reproducible(self):
        self.assertEqual(make_mapping(1), make_mapping(1))


class ValidateTests(unittest.TestCase):
    def test_validate_ok(self):
        self.assertEqual(validate(sample()), [])

    def test_validate_fewer_than_five_advisors(self):
        d = sample()
        d["advisors"].pop()
        self.assertTrue(any("위원" in e for e in validate(d)))

    def test_validate_missing_field(self):
        d = sample()
        del d["advisors"][2]["risk"]
        errors = validate(d)
        self.assertTrue(errors)
        self.assertTrue(any("risk" in e for e in errors))

    def test_validate_review_unknown_letter(self):
        d = sample()
        d["reviews"][0]["strongest"] = "F"
        self.assertTrue(validate(d))

    def test_validate_review_picks_own_response(self):
        d = sample()
        own = next(k for k, v in d["mapping"].items() if v == d["reviews"][0]["reviewer"])
        d["reviews"][0]["strongest"] = own
        self.assertTrue(any("자기" in e for e in validate(d)))

    def test_validate_bad_confidence(self):
        d = sample()
        d["verdict"]["confidence"] = "아주높음"
        self.assertTrue(validate(d))

    def test_validate_bad_mode(self):
        d = sample()
        d["mode"] = "x"
        self.assertTrue(validate(d))

    def test_validate_collects_all_errors(self):
        d = copy.deepcopy(sample())
        d["mode"] = "x"
        d["verdict"]["confidence"] = "?"
        self.assertGreaterEqual(len(validate(d)), 2)


def template():
    return TEMPLATE.read_text(encoding="utf-8")


class RenderTests(unittest.TestCase):
    def test_render_contains_five_cards_and_korean(self):
        html = render(sample(), template())
        self.assertEqual(html.count('class="advisor-card"'), 5)
        self.assertIn("반대자", html)
        self.assertIn(DISCLAIMER, html)
        self.assertIn('<meta charset="utf-8">', html)

    def test_render_escapes_html(self):
        d = sample()
        d["question"] = "<script>alert(1)</script> & \"따옴표\""
        html = render(d, template())
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_render_invalid_raises(self):
        d = sample()
        d["advisors"].pop()
        with self.assertRaises(ValueError):
            render(d, template())

    def test_mode_banner_single_session(self):
        d = sample()
        d["mode"] = "single-session"
        self.assertIn("독립성이 낮습니다", render(d, template()))
        self.assertNotIn("독립성이 낮습니다", render(sample(), template()))

    def test_verdict_shows_minority_and_confidence(self):
        d = sample()
        d["verdict"]["minority_kept"] = True
        d["verdict"]["confidence"] = "낮음"
        html = render(d, template())
        self.assertIn("소수 의견 유지됨", html)
        self.assertIn("신뢰도", html)
        self.assertIn("낮음", html)

    def test_review_table_shows_advisor_names_not_only_letters(self):
        html = render(sample(), template())
        self.assertIn("확장가", html.split("상호 검토", 1)[1])


class CliTests(unittest.TestCase):
    def _run(self, args, cwd=None, env=None):
        return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=cwd, env=env,
                              capture_output=True, text=True, encoding="utf-8", errors="replace")

    def _write_json(self, tmp, data):
        path = Path(tmp) / "council.json"
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return path

    def test_cli_cp949_env(self):
        d = sample()
        d["question"] += " 😀"
        env = dict(os.environ, PYTHONUTF8="0", PYTHONIOENCODING="cp949")
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "r.html"
            r = self._run(["render", str(self._write_json(tmp, d)), "--out", str(out)], env=env)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("반대자", out.read_text(encoding="utf-8"))

    def test_cli_invalid_exit_code_2(self):
        d = sample()
        d["advisors"].pop()
        with tempfile.TemporaryDirectory() as tmp:
            r = self._run(["render", str(self._write_json(tmp, d)), "--out", str(Path(tmp) / "r.html")])
            self.assertEqual(r.returncode, 2)
            self.assertTrue(r.stderr.strip())

    def test_cli_runs_from_other_cwd(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as elsewhere:
            out = Path(tmp) / "r.html"
            r = self._run(["render", str(self._write_json(tmp, sample())), "--out", str(out)], cwd=elsewhere)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(out.exists())

    def test_cli_shuffle_prints_valid_mapping(self):
        r = self._run(["shuffle", "--seed", "3"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), make_mapping(3))

    def test_cli_creates_missing_output_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "council-reports" / "r.html"
            r = self._run(["render", str(self._write_json(tmp, sample())), "--out", str(out)])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(out.exists())


if __name__ == "__main__":
    unittest.main()
