"""council-kr 보고서 도구: A~E 셔플 매핑, council JSON 검증, HTML 렌더링.

표준 라이브러리만 쓴다. 모든 입출력은 UTF-8이다.
"""
import random

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
                reasons = adv.get("reasons")
                if not isinstance(reasons, list) or len(reasons) != REASONS_COUNT \
                        or not all(_text(r) for r in reasons):
                    errors.append(f"{where}: 'reasons'는 비어 있지 않은 문자열 {REASONS_COUNT}개여야 합니다")
        if sorted(map(str, seen)) != sorted(ADVISOR_IDS):
            errors.append(f"위원 id가 {list(ADVISOR_IDS)}와 일치해야 합니다(받은 값: {seen})")

    mapping = data.get("mapping")
    mapping_ok = (isinstance(mapping, dict) and set(mapping) == set(LETTERS)
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
            for field in ("strongest", "weakest"):
                if rv.get(field) not in tuple(LETTERS):
                    errors.append(f"{where}: '{field}'는 {LETTERS} 중 하나여야 합니다(받은 값: {rv.get(field)!r})")
            if mapping_ok and rv.get("strongest") in tuple(LETTERS) \
                    and mapping[rv["strongest"]] == rv.get("reviewer"):
                errors.append(f"{where}: 자기 자신의 응답({rv['strongest']})을 가장 강한 응답으로 골랐습니다")
        if sorted(map(str, reviewers)) != sorted(ADVISOR_IDS):
            errors.append(f"reviews: 검토자 id가 위원 5명과 일치해야 합니다(받은 값: {reviewers})")

    verdict = data.get("verdict")
    if _require(verdict, ("recommendation", "first_action"), "verdict", errors):
        for key in ("agree", "blindspots"):
            if not isinstance(verdict.get(key), list):
                errors.append(f"verdict: '{key}'는 목록이어야 합니다")
        clash = verdict.get("clash")
        if not isinstance(clash, list) or not all(
                isinstance(c, dict) and _text(c.get("point")) and _text(c.get("sides")) for c in clash):
            errors.append("verdict: 'clash'는 point·sides가 있는 항목의 목록이어야 합니다")
        if verdict.get("confidence") not in CONFIDENCES:
            errors.append(f"verdict: 'confidence'는 {', '.join(CONFIDENCES)} 중 하나여야 합니다")
        if not isinstance(verdict.get("minority_kept"), bool):
            errors.append("verdict: 'minority_kept'는 true/false여야 합니다")
    return errors
