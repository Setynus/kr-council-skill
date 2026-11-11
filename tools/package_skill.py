"""스킬 폴더를 claude.ai 업로드용 zip으로 묶는다. 사용: python tools/package_skill.py [출력.zip]

zip 맨 위에 스킬 폴더(kr-council-skill/)가 하나 있고 그 안에 SKILL.md가 있어야 설치된다.
실행에 필요 없는 평가 케이스(evals/)와 캐시는 뺀다. 같은 입력이면 같은 바이트가 나오게 시각을 고정한다.
"""
import sys
import zipfile
from pathlib import Path

EXCLUDED_DIRS = {"evals", "__pycache__"}
FIXED_TIME = (2026, 1, 1, 0, 0, 0)


def build_zip(skill_dir, out_path):
    skill_dir, out_path = Path(skill_dir), Path(out_path)
    files = sorted(p for p in skill_dir.rglob("*")
                   if p.is_file() and not (set(p.relative_to(skill_dir).parts) & EXCLUDED_DIRS)
                   and p.suffix != ".pyc")
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in files:
            info = zipfile.ZipInfo(f"{skill_dir.name}/{p.relative_to(skill_dir).as_posix()}", FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, p.read_bytes().replace(b"\r\n", b"\n") if p.suffix in {".md", ".py", ".html"} else p.read_bytes())
    return out_path


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    root = Path(__file__).resolve().parent.parent
    out = Path(args[0]) if args else root / "dist" / "kr-council-skill.zip"
    out.parent.mkdir(parents=True, exist_ok=True)
    print(build_zip(root / "kr-council-skill", out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
