import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "kr-council-skill" / "scripts" / "render_report.py"
TEMPLATE = (ROOT / "kr-council-skill" / "assets" / "report.html")
sys.path.insert(0, str(ROOT / "kr-council-skill" / "scripts"))

from render_report import (  # noqa: E402
    ADVISOR_IDS, ADVISOR_NAMES, ADVISOR_PROFILE, CHAIR_NAME, make_mapping, render, validate)

DISCLAIMER = "같은 모델이 서로 다른 관점으로 낸 의견이며, 독립된 전문가 5인이 아닙니다."

NAMES = {
    "contrarian": "투덜이 스머프(반대자)",
    "first_principles": "똘똘이 스머프(본질 탐구자)",
    "expansionist": "화가 스머프(확장가)",
    "outsider": "덜렁이 스머프(아웃사이더)",
    "executor": "재주꾼 스머프(실행가)",
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

    def test_validate_mixed_type_mapping_is_an_error_not_a_crash(self):
        d = sample()
        d["mapping"] = {"A": 1, "B": "x", "C": {"k": 1}, "D": "z", "E": "w"}
        self.assertTrue(any("mapping" in e for e in validate(d)))

    def test_validate_agree_items_must_be_text(self):
        d = sample()
        d["verdict"]["agree"] = ["정상", None, 123]
        self.assertTrue(any("agree" in e for e in validate(d)))

    def test_validate_agree_must_not_be_empty(self):
        d = sample()
        d["verdict"]["agree"] = []
        self.assertTrue(any("agree" in e for e in validate(d)))

    def test_validate_blindspots_items_must_be_text(self):
        d = sample()
        d["verdict"]["blindspots"] = [{"x": "<b>"}]
        self.assertTrue(any("blindspots" in e for e in validate(d)))

    def test_validate_minority_kept_requires_a_clash(self):
        d = sample()
        d["verdict"]["clash"] = []
        d["verdict"]["minority_kept"] = True
        self.assertTrue(any("minority_kept" in e for e in validate(d)))

    def test_validate_strongest_and_weakest_must_differ(self):
        d = sample()
        d["reviews"][0]["weakest"] = d["reviews"][0]["strongest"]
        self.assertTrue(any("같은" in e for e in validate(d)))

    def test_validate_duplicate_advisor_names(self):
        d = sample()
        d["advisors"][1]["name"] = d["advisors"][0]["name"]
        self.assertTrue(any("이름" in e for e in validate(d)))

    def test_validate_clash_error_mentions_string_sides(self):
        d = sample()
        d["verdict"]["clash"] = [{"point": "광고", "sides": ["a", "b"]}]
        self.assertTrue(any("문자열" in e for e in validate(d)))

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
        self.assertIn("투덜이 스머프(반대자)", html)
        self.assertIn("파파스머프", html)
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

    def test_verdict_without_minority_says_none_not_ignored(self):
        d = sample()
        d["verdict"]["minority_kept"] = False
        html = render(d, template())
        self.assertIn("소수 의견 없음", html)
        self.assertNotIn("반영 안 됨", html)

    def test_review_table_shows_advisor_names_not_only_letters(self):
        html = render(sample(), template())
        self.assertIn("화가 스머프(확장가)", html.split("상호 검토", 1)[1])


class DashboardStructureTests(unittest.TestCase):
    def test_mini_cards_one_per_advisor_with_blurb(self):
        html = render(sample(), template())
        self.assertEqual(html.count('class="advisor-mini"'), 5)
        self.assertEqual(html.count('class="advisor-card"'), 5)
        for advisor_id, profile in ADVISOR_PROFILE.items():
            self.assertIn(f'href="#advisor-{advisor_id}"', html)
            self.assertIn(profile["blurb"], html)

    def test_detail_panels_have_anchor_ids(self):
        html = render(sample(), template())
        for advisor_id in ADVISOR_IDS:
            self.assertIn(f'id="advisor-{advisor_id}"', html)

    def test_mini_cards_escape_advisor_name(self):
        d = sample()
        d["advisors"][0]["name"] = "<script>alert(1)</script>{{ADVISOR_CARDS}}"
        self.assertEqual(validate(d), [])
        html = render(d, template())
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertEqual(html.count('class="advisor-card"'), 5)
        self.assertEqual(html.count('class="advisor-mini"'), 5)

    def test_sections_order(self):
        html = render(sample(), template())
        positions = [html.index(f'id="{name}"') for name in ("question", "report", "advisors", "affinity", "reviews")]
        self.assertEqual(positions, sorted(positions))


class ProfileTests(unittest.TestCase):
    def test_advisor_names_derived_from_profile(self):
        self.assertEqual(set(ADVISOR_PROFILE), set(ADVISOR_IDS))
        self.assertEqual(ADVISOR_NAMES, NAMES)

    def test_blurbs_are_sentences_from_advisors_md(self):
        advisors_md = (ROOT / "kr-council-skill" / "references" / "advisors.md").read_text(encoding="utf-8")
        for advisor_id, profile in ADVISOR_PROFILE.items():
            self.assertIn(profile["blurb"], advisors_md, advisor_id)

    def test_chair_name_comes_from_constant(self):
        self.assertIn(CHAIR_NAME, render(sample(), template()))
        self.assertNotIn("파파스머프", template())


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
            self.assertIn("투덜이 스머프(반대자)", out.read_text(encoding="utf-8"))

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

    def test_cli_lone_surrogate_exit_2_and_no_empty_file(self):
        d = sample()
        d["title"] = "제목 " + chr(0xD83D)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "r.html"
            path = Path(tmp) / "council.json"
            path.write_text(json.dumps(d), encoding="utf-8")
            r = self._run(["render", str(path), "--out", str(out)])
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertFalse(out.exists())

    def test_cli_output_path_is_a_folder_exit_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = self._run(["render", str(self._write_json(tmp, sample())), "--out", tmp])
            self.assertEqual(r.returncode, 2, r.stderr)


if __name__ == "__main__":
    unittest.main()
