import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "council-kr" / "scripts"))

from render_report import ADVISOR_IDS, make_mapping, validate  # noqa: E402

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


if __name__ == "__main__":
    unittest.main()
