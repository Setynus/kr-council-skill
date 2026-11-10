# kr-council-skill

선택지가 갈리는 결정을 위원 5명이 따로 분석하고, 익명으로 서로 검토한 뒤, 위원장이 하나의 권고로 정리하는 한국어 Claude 스킬입니다. 결과는 위원별 판단 카드와 위원장 보고서가 담긴 HTML 대시보드입니다.

## 쓰는 법
Claude에게 "위원회 열어줘", "자문단 소집", "council 돌려줘"라고 말하고 결정 상황을 알려 주면 됩니다. 하위 호출이 11개(자문 5 + 검토 5 + 위원장 1) 들어갑니다.

## 설치
스킬 폴더는 `kr-council-skill/` 입니다. 이 폴더 전체를 Claude의 스킬 폴더에 둡니다.
- **Claude Code**: `~/.claude/skills/kr-council-skill`에 복사하거나 링크합니다(Windows는 `mklink /J`로 디렉터리 정션).
- **claude.ai**: `kr-council-skill/` 폴더를 zip으로 묶어 설정의 스킬 업로드로 올립니다. 병렬 호출이 없으면 "프롬프트 묶음"이나 "단일 세션" 방식으로 동작합니다.
- 보고서 생성에 Python 3이 필요합니다(표준 라이브러리만 사용).

## 구성
- `kr-council-skill/` 스킬 본체(SKILL.md, 렌더러, HTML 템플릿, 참고 문서, 평가 케이스)
- `tests/`, `tools/` 개발용 테스트와 도구(`python -m unittest discover tests`)
- `comparison/` 다른 위원회 스킬과의 블라인드 비교 질문·기준선·결과(`comparison/results/`)
- `docs/` 설계서·구현 계획·공개 전환 점검 목록

## 한계와 주의
- 위원 5명은 같은 모델이 관점만 바꿔 낸 의견이며, 독립된 전문가 5인이 아닙니다.
- 출력은 세무·법률·투자 조언이 아닙니다. 보고서의 제도·수치는 "확인 필요" 표시를 보고 공식 자료로 확인하세요.
- 비교 결과는 질문 3개의 일화적 비교입니다. 자세한 한계는 `comparison/results/`의 보고서를 보세요.

## 출처
`NOTICE.md`를 보세요.
