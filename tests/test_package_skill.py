import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from package_skill import build_zip  # noqa: E402


class PackageSkillTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.zip = build_zip(ROOT / "kr-council-skill", Path(self.tmp.name) / "out.zip")
        self.names = zipfile.ZipFile(self.zip).namelist()

    def tearDown(self):
        self.tmp.cleanup()

    def test_root_folder_is_skill_name_with_skill_md(self):
        self.assertIn("kr-council-skill/SKILL.md", self.names)
        self.assertTrue(all(n.startswith("kr-council-skill/") for n in self.names))

    def test_runtime_files_included(self):
        for need in ("scripts/render_report.py", "assets/report.html",
                     "references/advisors.md", "references/ko-context.md"):
            self.assertIn(f"kr-council-skill/{need}", self.names)

    def test_dev_files_excluded(self):
        for n in self.names:
            self.assertNotIn("/evals/", n)
            self.assertNotIn("__pycache__", n)
            self.assertFalse(n.endswith(".pyc"))

    def test_zip_is_reproducible(self):
        again = build_zip(ROOT / "kr-council-skill", Path(self.tmp.name) / "again.zip")
        self.assertEqual(Path(self.zip).read_bytes(), Path(again).read_bytes())

    def test_skill_md_has_license_field_and_repo_has_mit_license(self):
        head = (ROOT / "kr-council-skill" / "SKILL.md").read_text(encoding="utf-8").split("---", 2)[1]
        self.assertIn("license: MIT", head)
        text = (ROOT / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("MIT License", text)
        self.assertIn("Setynus", text)


if __name__ == "__main__":
    unittest.main()
