# 변경 이력

이 문서는 [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/) 형식을 따르고, 버전은 [유의적 버전](https://semver.org/lang/ko/)을 따릅니다. 1.0 이전에는 입력 검증을 엄격하게 하는 변경도 마이너 버전(0.x.0)으로 올립니다.

## [Unreleased]

## [0.2.0] - 2026-11-11

### 추가
- `README.md` 머리말에 버전·라이선스·언어·테스트 배지와 버전 이력 절.
- `CHANGELOG.md`, `SECURITY.md`, `CONTRIBUTING.md`, 이슈·PR 템플릿, GitHub Actions 테스트(Windows·Linux, Python 3.10·3.12·3.13), `.gitattributes`.

### 변경
- 렌더러가 더 엄격하게 검사합니다. `agree`는 비어 있지 않은 문자열이 하나 이상, `blindspots`는 문자열 목록이어야 하고, `minority_kept`가 `true`이면 `clash`가 하나 이상 있어야 합니다. 검토에서 가장 강한 응답과 가장 약한 응답이 같은 글자이거나 위원 이름이 겹치면 오류입니다. (이전 버전에서 통과하던 부정확한 `council.json`이 이제 종료 코드 2로 거부됩니다.)
- 보고서 JSON은 `council-YYYYMMDD-HHMM.json`으로 저장해 이전 실행 결과를 덮어쓰지 않습니다.
- 맥락 안의 `<BEGIN_UNTRUSTED>`/`<END_UNTRUSTED>` 문자열을 무력화하는 규칙과, `python3` 대체 안내를 `## 중요`로 옮겼습니다.
- 저장소에서 구현 계획 문서를 제거하고 이력을 정리했습니다. 이 과정에서 `v0.1.0`, `v0.1.1` 태그와 릴리스를 삭제했습니다(내용은 0.2.0에 모두 포함).

## [0.1.1] - 2026-11-11

### 변경
- 위원 5종·세 가지 긴장 관계·검토 3질문·판정 5항목의 구성이 원본 저장소와 같다는 점을 `NOTICE.md`와 `README.md`에 명시. 위원 관점 문서 서문을 다시 씀.

## [0.1.0] - 2026-11-11

첫 공개 릴리스.

### 추가
- 위원 5명(투덜이·똘똘이·화가·덜렁이·재주꾼 스머프 비유)이 따로 분석 → 익명 상호 검토 → 위원장(파파스머프) 판정하는 한국어 스킬 `kr-council-skill`.
- 실행 방식 3가지(병렬, 프롬프트 묶음, 단일 세션), HTML 보고서 렌더러(`render_report.py`), 한국 맥락 체크리스트.
- 병렬·독립성 검사 도구(`tools/check_parallel.py`), 블라인드 비교 도구와 결과(`comparison/`), claude.ai 업로드용 zip 패키징(`tools/package_skill.py`).
- MIT 라이선스, `NOTICE.md`(출처와 스머프 상표 고지).

[Unreleased]: https://github.com/Setynus/kr-council-skill/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/Setynus/kr-council-skill/releases/tag/v0.2.0
