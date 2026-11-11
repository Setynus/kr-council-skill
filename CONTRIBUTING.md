# 기여 안내

버그 신고와 제안은 GitHub Issues로, 변경은 Pull Request로 보내 주세요.

## 개발 환경
Python 3.10 이상이면 됩니다. 외부 패키지는 필요 없습니다.

```
python -m unittest discover tests     # 전체 테스트
python tools/package_skill.py         # claude.ai 업로드용 zip (dist/)
```

## 작업 방식
- 새 동작이나 버그 수정은 **실패하는 테스트를 먼저** 쓰고, 통과시킨 뒤 커밋합니다.
- 스킬 폴더(`kr-council-skill/`)는 실행에 필요한 것만 둡니다. 폴더 안에 `README.md`를 만들지 않고, 개발용 파일은 `tests/`, `tools/`, `comparison/`, `docs/`에 둡니다.
- `SKILL.md`는 공식 규칙을 지킵니다: `name`은 폴더 이름과 같은 kebab-case, `description` 1,024자 이하·`<` `>` 없음, 본문 500줄 미만, 중요한 규칙은 맨 위 `## 중요`에. 이 규칙들은 `tests/test_skill_md.py`가 검사합니다.
- 위원 문장은 요약하거나 고쳐 쓰지 않고 그대로 옮기는 것이 이 스킬의 규칙입니다.
- 사용자에게 보이는 변화는 `CHANGELOG.md`의 `[Unreleased]`에 적습니다.

## 릴리스
[docs/RELEASE-CHECKLIST.md](docs/RELEASE-CHECKLIST.md)를 따릅니다.

## 개인정보
이슈나 PR에 실제 결정 내용, 개인정보, 비밀번호, API 키를 올리지 마세요. 재현에는 가상의 예시를 쓰세요.
