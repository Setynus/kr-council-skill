import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from blind_pack import blind_pack  # noqa: E402

OUTPUTS = {"kr-council-skill": "가 답변 본문", "ecc-council": "나 답변 본문", "single": "다 답변 본문"}


class BlindPackTests(unittest.TestCase):
    def test_blind_pack_hides_and_maps(self):
        items, key = blind_pack(OUTPUTS, seed=1)
        self.assertEqual(len(items), 3)
        for label, _text in items:
            for system in OUTPUTS:
                self.assertNotIn(system, label)
        self.assertEqual({key[label]: text for label, text in items}, OUTPUTS)

    def test_blind_pack_seed_reproducible(self):
        self.assertEqual(blind_pack(OUTPUTS, seed=7), blind_pack(OUTPUTS, seed=7))

    def test_labels_are_numbered(self):
        items, _ = blind_pack(OUTPUTS, seed=3)
        self.assertEqual([label for label, _ in items], ["응답1", "응답2", "응답3"])


if __name__ == "__main__":
    unittest.main()
