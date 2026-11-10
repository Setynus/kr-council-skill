"""대화 기록(JSONL)에서 kr-council-skill의 병렬·독립 규칙 위반을 찾는 개발 전용 도구.

사용: python tools/check_parallel.py <대화기록.jsonl>
하위 에이전트 안에서 스킬을 돌렸다면 <세션>/subagents/agent-*.jsonl을 넘긴다.
종료 코드 0이면 위반 없음, 1이면 위반 있음.

기록 형식(실측): 한 응답에 묶인 호출은 같은 message.id를 가진 여러 줄로 저장된다.
그래서 '한 응답에 5개'는 줄 수가 아니라 message.id별 Agent 호출 수로 센다.
"""
import json
import sys
from collections import OrderedDict
from pathlib import Path

AGENT_TOOL_NAMES = ("Agent", "Task")
BATCH_SIZE = 5       # 위원 수. 자문 묶음과 검토 묶음이 각각 이 크기여야 한다.
BATCHES_REQUIRED = 2  # 자문 5 + 검토 5
LEAK_PROBE_CHARS = 40  # 앞선 결과의 앞 40자가 프롬프트에 있으면 새어 든 것으로 본다.
LEAK_MIN_CHARS = 30    # 이보다 짧은 결과는 우연히 겹칠 수 있어 검사하지 않는다.


def load_jsonl(path):
    entries = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue  # 깨진 줄은 건너뛴다. 기록 일부가 잘려도 나머지는 검사한다.
    return entries


def _blocks(entry):
    content = (entry.get("message") or {}).get("content")
    return content if isinstance(content, list) else []


def _result_text(block):
    content = block.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(b.get("text", "") for b in content if isinstance(b, dict))
    return ""


def check_parallel(entries):
    """위반 문장 목록을 돌려준다. 비어 있으면 통과다."""
    uses = []      # {"idx", "msg", "id", "type", "prompt"}
    results = {}   # tool_use_id -> (idx, text)
    for idx, entry in enumerate(entries):
        for block in _blocks(entry):
            if entry.get("type") == "assistant" and block.get("type") == "tool_use" \
                    and block.get("name") in AGENT_TOOL_NAMES:
                inp = block.get("input") or {}
                uses.append({"idx": idx, "msg": (entry.get("message") or {}).get("id"),
                             "id": block.get("id"), "type": inp.get("subagent_type"),
                             "prompt": inp.get("prompt", "")})
            elif entry.get("type") == "user" and block.get("type") == "tool_result":
                results[block.get("tool_use_id")] = (idx, _result_text(block))

    errors = []
    groups = OrderedDict()
    for u in uses:
        groups.setdefault(u["msg"], []).append(u)
    batches = [g for g in groups.values() if len(g) >= BATCH_SIZE]

    if not batches:
        errors.append(f"Agent 호출이 한 응답에 {BATCH_SIZE}개 이상 묶여 있지 않습니다(순차 호출 의심)")
    elif len(batches) < BATCHES_REQUIRED:
        errors.append(f"자문 {BATCH_SIZE}개와 검토 {BATCH_SIZE}개, 두 묶음이 필요합니다(찾은 묶음: {len(batches)})")

    for u in uses:
        if u["type"] == "fork":
            errors.append(f"fork 유형 호출이 있습니다(호출 {u['id']}): 대화 전체를 물려받아 독립성이 깨집니다")
        elif not u["type"]:
            errors.append(f"subagent_type 미지정 호출이 있습니다(호출 {u['id']}): general-purpose로 명시해야 합니다")

    for n, batch in enumerate(batches, 1):
        last_launch = max(u["idx"] for u in batch)
        for u in batch:
            got = results.get(u["id"])
            if got and got[0] < last_launch:
                errors.append(f"{n}번째 묶음: 5개를 모두 시작하기 전에 결과를 읽었습니다(호출 {u['id']})")

    if batches:
        first = batches[0]
        first_idx = min(u["idx"] for u in first)
        batch_ids = {u["id"] for u in first}
        for u in uses:
            if u["id"] in batch_ids or u["id"] not in results or results[u["id"]][0] >= first_idx:
                continue
            text = results[u["id"]][1].strip()
            if len(text) < LEAK_MIN_CHARS:
                continue
            probe = text[:LEAK_PROBE_CHARS]
            for b in first:
                if probe in b["prompt"]:
                    errors.append(f"위원 프롬프트(호출 {b['id']})에 앞선 호출의 결과가 새어 들어갔습니다")
    return errors


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("사용: python tools/check_parallel.py <대화기록.jsonl>", file=sys.stderr)
        return 2
    errors = check_parallel(load_jsonl(args[0]))
    for e in errors:
        print(f"위반: {e}")
    if not errors:
        print("통과: 병렬·독립 규칙 위반이 없습니다")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
