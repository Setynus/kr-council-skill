# 출처와 저작권 고지

## 방법론
이 스킬은 Andrej Karpathy가 공개한 "llm-council" 방식(여러 관점의 자문 → 익명 상호 검토 → 의장 종합)을 따른다. 방식은 아이디어이며, 이 저장소의 코드·문장은 모두 처음부터 새로 썼다.

## 영감을 준 저장소
`aiwithremy/claude-skills-llm-council`에서 영감을 얻었다. 그 저장소에는 라이선스가 없어 **문장·프롬프트·구조 문서를 복사하지 않았다.** 확인한 방법:
- `tests/test_skill_md.py`가 원본 영어 문구 일부가 SKILL.md에 들어가지 않았는지 검사한다.
- `kr-council-skill/references/advisors.md`와 위원장 절을 한국어로 새로 쓴 문장으로 작성했다. 위원 5종의 관점 이름(반대자·제1원리·확장가·아웃사이더·실행가)은 같은 방법론의 일반적인 구분이다.

## 비교 기준선의 ecc 출력
`comparison/baselines/*.ecc-council.md`는 ecc(Everything Claude Code) 2.2.3의 `ecc:council` 스킬을 실행해 얻은 **출력만** 담는다. 스킬 본문은 복사하지 않았다. ecc는 MIT License(Copyright (c) 2026 Affaan Mustafa)이다.

## 이 저장소의 라이선스
LICENSE 파일을 참고한다(공개 여부와 함께 소유자가 정한다).
