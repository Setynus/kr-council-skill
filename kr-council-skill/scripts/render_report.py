"""kr-council-skill 보고서 도구: A~E 셔플 매핑, council JSON 검증, HTML 렌더링.

표준 라이브러리만 쓴다. 모든 입출력은 UTF-8이다.
"""
import argparse
import html
import json
import random
import re
import sys
from pathlib import Path

DISCLAIMER = "같은 모델이 서로 다른 관점으로 낸 의견이며, 독립된 전문가 5인이 아닙니다."
MODE_BANNERS = {
    "parallel": "실행 방식: 병렬 — 위원 5명을 서로 격리된 하위 에이전트로 동시에 호출했습니다.",
    "prompt-pack": "실행 방식: 프롬프트 묶음 — 위원별 프롬프트를 별도 대화에서 실행해 결과를 가져왔습니다.",
    "single-session": ("실행 방식: 단일 세션 — 한 대화에서 차례로 작성했고, 앞선 위원의 답이 "
                       "뒤 위원에 영향을 줄 수 있어 독립성이 낮습니다."),
}
# 템플릿은 스크립트 위치 기준으로 찾는다. 사용자의 작업 폴더는 스킬 폴더와 다르기 때문이다.
TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "assets" / "report.html"
VALIDATION_ERROR_EXIT = 2

# 위원 ID는 SKILL.md, references/advisors.md와 같은 순서·철자를 쓴다.
ADVISOR_IDS = ("contrarian", "first_principles", "expansionist", "outsider", "executor")
MODES = ("parallel", "prompt-pack", "single-session")
CONFIDENCES = ("높음", "보통", "낮음")
LETTERS = "ABCDE"  # 익명 응답 이름. 위원 수(5)와 같아야 한다.
REASONS_COUNT = 3  # 위원 한 명이 내는 근거 개수(SKILL.md의 응답 JSON 규칙)


def make_mapping(seed=None):
    """A~E를 위원 5명에 무작위로 1:1 대응시킨다. LLM은 난수를 만들지 못하므로 여기서 한다."""
    ids = list(ADVISOR_IDS)
    random.Random(seed).shuffle(ids)
    return dict(zip(LETTERS, ids))


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _require(obj, keys, where, errors):
    """obj가 dict이고 keys가 모두 비어 있지 않은 문자열인지 본다. 아니면 오류를 모은다."""
    if not isinstance(obj, dict):
        errors.append(f"{where}: 객체(dict)여야 합니다")
        return False
    for key in keys:
        if key not in obj:
            errors.append(f"{where}: 필드 '{key}'가 없습니다")
        elif not _text(obj[key]):
            errors.append(f"{where}: 필드 '{key}'가 비어 있거나 문자열이 아닙니다")
    return True


def _check_reasons(adv, where, errors):
    reasons = adv.get("reasons")
    if not isinstance(reasons, list) or len(reasons) != REASONS_COUNT or not all(_text(r) for r in reasons):
        errors.append(f"{where}: 'reasons'는 비어 있지 않은 문자열 {REASONS_COUNT}개여야 합니다")


def _check_letters(rv, where, errors):
    for field in ("strongest", "weakest"):
        if rv.get(field) not in tuple(LETTERS):
            errors.append(f"{where}: '{field}'는 {LETTERS} 중 하나여야 합니다(받은 값: {rv.get(field)!r})")
    if rv.get("strongest") == rv.get("weakest") and rv.get("strongest") in tuple(LETTERS):
        errors.append(f"{where}: 가장 강한 응답과 가장 약한 응답이 같은 글자({rv['strongest']})입니다")


def _check_verdict(verdict, errors):
    if _require(verdict, ("recommendation", "first_action"), "verdict", errors):
        for key in ("agree", "blindspots"):
            items = verdict.get(key)
            if not isinstance(items, list) or not all(_text(x) for x in items):
                errors.append(f"verdict: '{key}'는 비어 있지 않은 문자열의 목록이어야 합니다")
        if isinstance(verdict.get("agree"), list) and not verdict["agree"]:
            errors.append("verdict: 'agree'에는 항목이 하나 이상 있어야 합니다")
        clash = verdict.get("clash")
        if not isinstance(clash, list) or not all(
                isinstance(c, dict) and _text(c.get("point")) and _text(c.get("sides")) for c in clash):
            errors.append("verdict: 'clash'는 point와 sides(둘 다 문자열)가 있는 항목의 목록이어야 합니다")
        elif verdict.get("minority_kept") is True and not clash:
            errors.append("verdict: 'minority_kept'가 true이면 'clash'에 충돌이 하나 이상 있어야 합니다")
        if verdict.get("confidence") not in CONFIDENCES:
            errors.append(f"verdict: 'confidence'는 {', '.join(CONFIDENCES)} 중 하나여야 합니다")
        if not isinstance(verdict.get("minority_kept"), bool):
            errors.append("verdict: 'minority_kept'는 true/false여야 합니다")


# 하위 에이전트가 내는 답의 필드. SKILL.md의 응답 JSON 틀과 같아야 한다.
ANSWER_FIELDS = {
    "advisor": ("position", "reasons", "risk", "blindspot"),
    "review": ("strongest", "strongest_why", "weakest", "weakest_why", "missed"),
    "verdict": ("agree", "clash", "blindspots", "recommendation", "first_action", "confidence", "minority_kept"),
}


def check_answer(kind, text):
    """하위 에이전트의 답 원문이 끝까지 닫힌 JSON이고 규격에 맞는지 본다. 오류 문장 목록을 돌려준다.

    사람이 눈으로 `"}`를 확인하면 `\\"}`나 닫힘 없는 끝을 놓친다. 그래서 파서가 판정한다.
    """
    if kind not in ANSWER_FIELDS:
        return [f"kind: {', '.join(ANSWER_FIELDS)} 중 하나여야 합니다(받은 값: {kind!r})"]
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        return [f"JSON이 끝까지 닫히지 않았거나 깨졌습니다({exc}). 직접 고치지 말고 재호출 규칙대로 다시 받으세요"]
    if not isinstance(obj, dict):
        return ["최상위 값이 객체(dict)가 아닙니다"]
    errors = []  # 규격 밖 필드는 재호출 사유가 아니다(비용만 늘어난다). assemble이 버린다.
    if kind == "verdict":
        _check_verdict(obj, errors)
    elif kind == "advisor":
        _require(obj, ("position", "risk", "blindspot"), kind, errors)
        _check_reasons(obj, kind, errors)
    else:
        _require(obj, ("strongest_why", "weakest_why", "missed"), kind, errors)
        _check_letters(obj, kind, errors)
    return errors


# 보고서 카드에 쓰는 위원 호칭. SKILL.md의 위원 이름 표와 같아야 한다(테스트가 비교한다).
ADVISOR_NAMES = {
    "contrarian": "투덜이 스머프(반대자)",
    "first_principles": "똘똘이 스머프(본질 탐구자)",
    "expansionist": "화가 스머프(확장가)",
    "outsider": "덜렁이 스머프(아웃사이더)",
    "executor": "재주꾼 스머프(실행가)",
}


def assemble(raw_dir):
    """원문 파일(meta.json, advisor-<id>.json, reviews/<글자>.json, verdict.json)로 council 데이터를 만든다.

    문장은 파일의 JSON을 그대로 옮기므로 손으로 옮기다 생기는 오기가 없다. (데이터 또는 None, 오류 목록)을 돌려준다.
    """
    raw = Path(raw_dir)
    errors = []

    def load(kind, name):
        try:
            text = (raw / name).read_text(encoding="utf-8")
        except OSError:
            errors.append(f"{name}: 파일을 읽을 수 없습니다")
            return None
        found = check_answer(kind, text) if kind else []
        if not kind:
            try:
                obj = json.loads(text)
            except json.JSONDecodeError as exc:
                found = [f"JSON이 끝까지 닫히지 않았거나 깨졌습니다({exc})"]
            else:
                found = [] if isinstance(obj, dict) else ["최상위 값이 객체(dict)가 아닙니다"]
        errors.extend(f"{name}: {line}" for line in found)
        return None if found else json.loads(text)

    keep = lambda obj, kind: {k: obj[k] for k in ANSWER_FIELDS[kind] if k in obj}  # 규격 밖 필드는 버린다
    meta = load(None, "meta.json")
    advisors = [load("advisor", f"advisor-{i}.json") for i in ADVISOR_IDS]
    verdict = load("verdict", "verdict.json")
    # 검토 파일은 위원 id가 아니라 익명 글자로 저장돼 있다(검토자 프롬프트에 id가 드러나지 않게). 매핑으로 되찾는다.
    mapping = (meta or {}).get("mapping")
    if isinstance(mapping, dict) and sorted(mapping.values()) == sorted(ADVISOR_IDS):
        letter_of = {v: k for k, v in mapping.items()}
        reviews = [load("review", f"reviews/{letter_of[i]}.json") for i in ADVISOR_IDS]
    else:
        reviews = []
        if meta is not None:
            errors.append("meta.json: 'mapping'이 A~E와 위원 5명의 1:1 대응이어야 검토 파일을 찾을 수 있습니다")
    if errors:
        return None, errors
    data = dict(meta)
    data["advisors"] = [{"id": i, "name": ADVISOR_NAMES[i], **keep(a, "advisor")}
                        for i, a in zip(ADVISOR_IDS, advisors)]
    data["reviews"] = [{"reviewer": i, **keep(r, "review")} for i, r in zip(ADVISOR_IDS, reviews)]
    data["verdict"] = keep(verdict, "verdict")
    errors = validate(data)
    return (None if errors else data), errors


def validate(data):
    """council.json을 검사해 오류 문장 목록을 돌려준다. 비어 있으면 유효하다."""
    errors = []
    if not isinstance(data, dict):
        return ["최상위 값이 객체(dict)가 아닙니다"]
    _require(data, ("title", "question", "created"), "최상위", errors)
    if data.get("mode") not in MODES:
        errors.append(f"mode: {', '.join(MODES)} 중 하나여야 합니다(받은 값: {data.get('mode')!r})")

    advisors = data.get("advisors")
    if not isinstance(advisors, list) or len(advisors) != len(ADVISOR_IDS):
        errors.append(f"위원은 {len(ADVISOR_IDS)}명이어야 합니다(받은 수: "
                      f"{len(advisors) if isinstance(advisors, list) else '목록 아님'})")
    else:
        seen = []
        for n, adv in enumerate(advisors, 1):
            where = f"위원 {n}번"
            if _require(adv, ("id", "name", "position", "risk", "blindspot"), where, errors):
                seen.append(adv.get("id"))
                _check_reasons(adv, where, errors)
        names = [a.get("name") for a in advisors if isinstance(a, dict)]
        if len(set(map(str, names))) != len(names):
            errors.append("위원 이름이 서로 달라야 합니다(중복된 이름이 있습니다)")
        if sorted(map(str, seen)) != sorted(ADVISOR_IDS):
            errors.append(f"위원 id가 {list(ADVISOR_IDS)}와 일치해야 합니다(받은 값: {seen})")

    mapping = data.get("mapping")
    mapping_ok = (isinstance(mapping, dict) and set(mapping) == set(LETTERS)
                  and all(isinstance(v, str) for v in mapping.values())
                  and sorted(mapping.values()) == sorted(ADVISOR_IDS))
    if not mapping_ok:
        errors.append("mapping: A~E가 위원 5명과 1:1로 대응해야 합니다")

    reviews = data.get("reviews")
    if not isinstance(reviews, list) or len(reviews) != len(ADVISOR_IDS):
        errors.append(f"reviews: 상호 검토는 {len(ADVISOR_IDS)}개여야 합니다")
    else:
        reviewers = []
        for n, rv in enumerate(reviews, 1):
            where = f"검토 {n}번"
            if not _require(rv, ("reviewer", "strongest_why", "weakest_why", "missed"), where, errors):
                continue
            reviewers.append(rv.get("reviewer"))
            _check_letters(rv, where, errors)
            if mapping_ok and rv.get("strongest") in tuple(LETTERS) \
                    and mapping[rv["strongest"]] == rv.get("reviewer"):
                errors.append(f"{where}: 자기 자신의 응답({rv['strongest']})을 가장 강한 응답으로 골랐습니다")
        if sorted(map(str, reviewers)) != sorted(ADVISOR_IDS):
            errors.append(f"reviews: 검토자 id가 위원 5명과 일치해야 합니다(받은 값: {reviewers})")

    _check_verdict(data.get("verdict"), errors)
    return errors


def _e(value):
    """모든 사용자·위원 텍스트는 HTML에 넣기 전에 이스케이프한다."""
    return html.escape(str(value), quote=True)


def _cards(data):
    out = []
    for adv in data["advisors"]:
        reasons = "".join(f"<li>{_e(r)}</li>" for r in adv["reasons"])
        out.append(
            f'    <article class="advisor-card" data-advisor="{_e(adv["id"])}">\n'
            f'      <h3>{_e(adv["name"])}</h3>\n'
            f'      <p class="position">{_e(adv["position"])}</p>\n'
            f'      <ol>{reasons}</ol>\n'
            f'      <p><span class="label">위험</span>{_e(adv["risk"])}</p>\n'
            f'      <p><span class="label">놓치기 쉬운 점</span>{_e(adv["blindspot"])}</p>\n'
            f'    </article>')
    return "\n".join(out)


def _review_table(data):
    names = {a["id"]: a["name"] for a in data["advisors"]}
    mapping = data["mapping"]

    def who(letter):
        return f"{_e(letter)} · {_e(names[mapping[letter]])}"

    rows = []
    for rv in data["reviews"]:
        rows.append(
            "      <tr>"
            f'<td>{_e(names[rv["reviewer"]])}</td>'
            f'<td>{who(rv["strongest"])}<br>{_e(rv["strongest_why"])}</td>'
            f'<td>{who(rv["weakest"])}<br>{_e(rv["weakest_why"])}</td>'
            f'<td>{_e(rv["missed"])}</td></tr>')
    return ("    <table>\n      <tr><th>검토한 위원</th><th>가장 강한 응답</th>"
            "<th>가장 큰 사각지대</th><th>모두가 놓친 것</th></tr>\n" + "\n".join(rows) + "\n    </table>")


def _verdict(data):
    v = data["verdict"]
    bullets = lambda items: "<ul>" + "".join(f"<li>{_e(i)}</li>" for i in items) + "</ul>"
    clash = "<ul>" + "".join(f'<li><strong>{_e(c["point"])}</strong> — {_e(c["sides"])}</li>'
                             for c in v["clash"]) + "</ul>"
    minority = "소수 의견 유지됨" if v["minority_kept"] else "소수 의견 없음"
    return (
        f'    <div class="chips"><span>신뢰도: {_e(v["confidence"])}</span><span>{minority}</span></div>\n'
        f'    <h3>위원회가 동의하는 점</h3>{bullets(v["agree"])}\n'
        f'    <h3>위원회가 충돌하는 점</h3>{clash}\n'
        f'    <h3>상호 검토에서 드러난 사각지대</h3>{bullets(v["blindspots"])}\n'
        f'    <h3>권고</h3><p class="rec">{_e(v["recommendation"])}</p>\n'
        f'    <h3>가장 먼저 할 한 가지</h3><p class="first">{_e(v["first_action"])}</p>')


def render(data, template):
    """검증을 통과한 council 데이터를 템플릿에 넣어 HTML 문자열을 만든다."""
    errors = validate(data)
    if errors:
        raise ValueError("\n".join(errors))
    slots = {
        "TITLE": _e(data["title"]), "CREATED": _e(data["created"]),
        "MODE_BANNER": _e(MODE_BANNERS[data["mode"]]), "DISCLAIMER": _e(DISCLAIMER),
        "QUESTION": _e(data["question"]), "ADVISOR_CARDS": _cards(data),
        "REVIEW_TABLE": _review_table(data), "VERDICT": _verdict(data),
    }
    # 한 번의 치환으로 끝낸다. 값 안의 '{{...}}'가 다시 치환되지 않게 하기 위해서다.
    return re.sub(r"\{\{([A-Z_]+)\}\}", lambda m: slots.get(m.group(1), m.group(0)), template)


def _main(argv=None):
    # Windows 기본 콘솔(cp949)에서 이모지 등을 출력하다 죽지 않게 한다.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(description="kr-council-skill 보고서 도구")
    sub = parser.add_subparsers(dest="cmd", required=True)
    shuffle = sub.add_parser("shuffle", help="A~E 익명 매핑을 JSON으로 출력")
    shuffle.add_argument("--seed", type=int, default=None)
    rend = sub.add_parser("render", help="council.json을 HTML 보고서로 변환")
    rend.add_argument("json_path")
    rend.add_argument("--out", required=True)
    chk = sub.add_parser("check", help="하위 에이전트의 답 원문이 끝까지 닫힌 JSON인지 확인")
    chk.add_argument("kind", choices=tuple(ANSWER_FIELDS))
    chk.add_argument("path", help="답을 저장한 파일. 표준 입력이면 -")
    asm = sub.add_parser("assemble", help="meta.json과 답 파일 11개로 council.json을 조립")
    asm.add_argument("raw_dir")
    asm.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    if args.cmd == "assemble":
        data, errors = assemble(args.raw_dir)
        if errors:
            print("council.json을 만들 수 없습니다:\n" + "\n".join(errors), file=sys.stderr)
            return VALIDATION_ERROR_EXIT
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"저장했습니다: {out}")
        return 0
    if args.cmd == "shuffle":
        print(json.dumps(make_mapping(args.seed), ensure_ascii=False))
        return 0
    if args.cmd == "check":
        raw = sys.stdin.buffer.read() if args.path == "-" else Path(args.path).read_bytes()
        errors = check_answer(args.kind, raw.decode("utf-8", errors="replace"))
        for line in errors:
            print(line, file=sys.stderr)
        if not errors:
            print("통과: 끝까지 닫힌 JSON이고 규격에 맞습니다")
        return VALIDATION_ERROR_EXIT if errors else 0
    try:
        data = json.loads(Path(args.json_path).read_text(encoding="utf-8"))
        payload = render(data, TEMPLATE_PATH.read_text(encoding="utf-8")).encode("utf-8")
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(payload)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"보고서를 만들 수 없습니다:\n{exc}", file=sys.stderr)
        return VALIDATION_ERROR_EXIT
    print(f"저장했습니다: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
