"""하위 에이전트가 낸 답(위원·검토·위원장)이 끝까지 닫힌 JSON인지 기계로 확인하는 `check`를 시험한다.

끝 형태 네 가지는 실제 실행(2026-11-13)에서 하위 에이전트가 낸 것이다. 사람이 눈으로 보면
`"}`가 있는 것처럼 보여 닫힌 답으로 잘못 판정했던 형태를 그대로 픽스처로 둔다.
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "kr-council-skill" / "scripts" / "render_report.py"
sys.path.insert(0, str(ROOT / "kr-council-skill" / "scripts"))

from render_report import check_answer, repair_ending  # noqa: E402

ADVISOR = {"position": "병행이 맞습니다.", "reasons": ["근거1", "근거2", "근거3"],
           "risk": "위험", "blindspot": "놓친 점"}
REVIEW = {"strongest": "A", "strongest_why": "구체적", "weakest": "C", "weakest_why": "근거 약함",
          "missed": "아무도 코드를 열어 보지 않았습니다."}
VERDICT = {"agree": ["병행"], "clash": [{"point": "시점", "sides": "먼저 vs 나중"}],
           "blindspots": ["미확인"], "recommendation": "병행하십시오.", "first_action": "샘플로 PDF를 만든다.",
           "confidence": "보통", "minority_kept": False}


def dumped(obj):
    return json.dumps(obj, ensure_ascii=False)


class EndShapes(unittest.TestCase):
    """같은 검토 답을 끝 형태만 바꿔 넣는다. 닫힌 것만 통과해야 한다."""

    def test_closed_answer_passes(self):
        self.assertEqual(check_answer("review", dumped(REVIEW)), [])

    def test_closed_answer_with_trailing_newline_passes(self):
        # 본질 탐구자·아웃사이더·실행가 검토: 답 끝에 줄바꿈만 붙은 형태
        self.assertEqual(check_answer("review", dumped(REVIEW) + "\n"), [])

    def test_escaped_newline_inside_last_string_passes(self):
        review = dict(REVIEW, missed="마지막 문장입니다.\n")
        self.assertEqual(check_answer("review", dumped(review)), [])

    def test_missing_closing_quote_and_brace_fails(self):
        # 확장가 검토: 마지막 문자열이 닫히지 않고 끝남
        errors = check_answer("review", dumped(REVIEW)[:-2])
        self.assertTrue(errors)
        self.assertIn("JSON", errors[0])

    def test_escaped_quote_then_brace_fails(self):
        # 반대자 검토(원호출·재호출 모두): 닫는 따옴표 자리에 이스케이프된 따옴표가 옴
        broken = dumped(REVIEW)[:-2] + '\\"}'
        errors = check_answer("review", broken)
        self.assertTrue(errors)
        self.assertIn("JSON", errors[0])

    def test_brace_only_missing_fails(self):
        self.assertTrue(check_answer("review", dumped(REVIEW)[:-1]))


class Repair(unittest.TestCase):
    """끝 경계만 보정한다. 실제로 나온 불량 두 형태는 보정되고, 정상·내용 손상은 건드리지 않는다."""

    def test_valid_answers_are_left_alone(self):
        self.assertIsNone(repair_ending("review", dumped(REVIEW)))
        self.assertIsNone(repair_ending("review", dumped(REVIEW) + "\n"))

    def test_missing_closing_quote_and_brace_is_repaired_without_touching_content(self):
        broken = dumped(REVIEW)[:-2]
        fixed = repair_ending("review", broken)
        self.assertEqual(json.loads(fixed), REVIEW)
        self.assertTrue(fixed.startswith(broken))  # 덧붙이기만 했다

    def test_escaped_quote_then_brace_is_repaired(self):
        broken = dumped(REVIEW)[:-2] + '\\"}'
        self.assertEqual(json.loads(repair_ending("review", broken)), REVIEW)

    def test_brace_only_missing_is_repaired(self):
        self.assertEqual(json.loads(repair_ending("review", dumped(REVIEW)[:-1])), REVIEW)

    def test_verdict_missing_final_brace_is_repaired(self):
        self.assertEqual(json.loads(repair_ending("verdict", dumped(VERDICT)[:-1])), VERDICT)

    def test_damage_outside_the_ending_is_refused(self):
        self.assertIsNone(repair_ending("review", dumped(REVIEW)[:30]))  # 중간에서 끊김
        self.assertIsNone(repair_ending("review", "JSON이 아닙니다"))
        two_reasons = dict(ADVISOR, reasons=["근거1", "근거2"])
        self.assertIsNone(repair_ending("advisor", dumped(two_reasons)[:-2]))  # 끝을 닫아도 규격 위반


class Fields(unittest.TestCase):
    def test_advisor_needs_exactly_three_reasons(self):
        self.assertEqual(check_answer("advisor", dumped(ADVISOR)), [])
        two = dict(ADVISOR, reasons=["근거1", "근거2"])
        self.assertTrue(check_answer("advisor", dumped(two)))

    def test_advisor_missing_field_named_in_error(self):
        no_risk = {k: v for k, v in ADVISOR.items() if k != "risk"}
        self.assertIn("risk", " ".join(check_answer("advisor", dumped(no_risk))))

    def test_review_letters_must_be_a_to_e_and_differ(self):
        self.assertTrue(check_answer("review", dumped(dict(REVIEW, strongest="F"))))
        self.assertTrue(check_answer("review", dumped(dict(REVIEW, weakest="A"))))

    def test_verdict_valid_and_invalid(self):
        self.assertEqual(check_answer("verdict", dumped(VERDICT)), [])
        self.assertTrue(check_answer("verdict", dumped(dict(VERDICT, confidence="매우 높음"))))
        self.assertTrue(check_answer("verdict", dumped(dict(VERDICT, minority_kept="false"))))

    def test_unknown_kind_and_non_object(self):
        self.assertTrue(check_answer("memo", dumped(ADVISOR)))
        self.assertTrue(check_answer("advisor", "[1, 2, 3]"))

    def test_extra_fields_do_not_force_a_retry(self):
        # 규격 밖 필드는 재호출 사유가 아니다. 비용만 늘기 때문이며, assemble이 버린다.
        self.assertEqual(check_answer("advisor", dumped(dict(ADVISOR, confidence="높음"))), [])


class Cli(unittest.TestCase):
    def run_check(self, kind, text):
        return subprocess.run([sys.executable, str(SCRIPT), "check", kind, "-"], input=text.encode("utf-8"),
                              capture_output=True)

    def test_exit_codes(self):
        ok = self.run_check("advisor", dumped(ADVISOR))
        self.assertEqual(ok.returncode, 0)
        bad = self.run_check("advisor", dumped(ADVISOR)[:-2])
        self.assertEqual(bad.returncode, 2)
        self.assertIn("JSON", bad.stderr.decode("utf-8", "replace"))


if __name__ == "__main__":
    unittest.main()
