"""시스템 이름을 가린 채점용 묶음을 만든다. 사용: python tools/blind_pack.py <질문ID> [--seed N]

comparison/baselines/<질문ID>.*.md 를 읽어 comparison/results/<질문ID>.pack.md(채점자용)와
<질문ID>.key.json(정답표, 채점자에게 주지 않는다)을 따로 쓴다.
"""
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def blind_pack(outputs, seed=None):
    """(라벨, 텍스트) 목록과 라벨→시스템키 정답표를 돌려준다."""
    systems = list(outputs)
    random.Random(seed).shuffle(systems)
    items = [(f"응답{i}", outputs[s]) for i, s in enumerate(systems, 1)]
    key = {f"응답{i}": s for i, s in enumerate(systems, 1)}
    return items, key


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if not args:
        print("사용: python tools/blind_pack.py <질문ID> [--seed N]", file=sys.stderr)
        return 2
    qid = args[0]
    seed = int(args[args.index("--seed") + 1]) if "--seed" in args else None
    base = ROOT / "comparison" / "baselines"
    outputs = {p.name[len(qid) + 1:-3]: p.read_text(encoding="utf-8") for p in sorted(base.glob(f"{qid}.*.md"))}
    items, key = blind_pack(outputs, seed)
    out = ROOT / "comparison" / "results"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{qid}.pack.md").write_text(
        "\n\n".join(f"# {label}\n\n{text}" for label, text in items), encoding="utf-8")
    (out / f"{qid}.key.json").write_text(json.dumps(key, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
