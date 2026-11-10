"""council.json의 위원장 판정을 비교용 텍스트(마크다운)로 바꾼다. 사용: python tools/council_to_md.py <council.json> <출력.md>

기준선 중 orig-method가 의장 판정만 담으므로 같은 범위(판정)만 내보낸다. 형식 단서는 채점 전에 blind_pack이 가린다.
"""
import json
import sys
from pathlib import Path

CONFIDENCE_KO = {"high": "높음", "medium": "보통", "low": "낮음"}


def verdict_to_md(data):
    v = data["verdict"]
    lines = [f"## 위원회 판정: {data['title']}", "", "### 위원회가 동의하는 점"]
    lines += [f"- {x}" for x in v["agree"]]
    lines += ["", "### 충돌하는 점"]
    lines += [f"- {c['point']}: {c['sides']}" for c in v["clash"]]
    lines += ["", "### 놓치기 쉬운 점"] + [f"- {x}" for x in v["blindspots"]]
    lines += ["", "### 권고", v["recommendation"], "", "### 가장 먼저 할 한 가지", v["first_action"], "",
              f"신뢰도: {CONFIDENCE_KO.get(v['confidence'], v['confidence'])}"]
    return "\n".join(lines) + "\n"


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        print("사용: python tools/council_to_md.py <council.json> <출력.md>", file=sys.stderr)
        return 2
    data = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    Path(args[1]).write_text(verdict_to_md(data), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
