# 보안 정책

## 지원 버전

| 버전 | 지원 |
|---|---|
| 최신 릴리스(`main`) | :white_check_mark: |
| 이전 릴리스 | :x: |

## 취약점 신고

보안 문제를 발견하면 **공개 이슈로 올리지 말고** 아래 방법으로 알려 주세요.

- GitHub 저장소의 Security 탭에서 [Report a vulnerability](https://github.com/Setynus/kr-council-skill/security/advisories/new)를 사용합니다.

## 이 프로젝트에서 보는 범위
- `kr-council-skill/scripts/render_report.py`: 위원 응답과 사용자 입력이 HTML 보고서에 들어갈 때의 이스케이프(XSS), 잘못된 입력에서의 비정상 종료.
- 스킬 지침: 맥락 파일이나 위원 응답 안의 지시문이 다른 단계로 번지는 프롬프트 주입. 스킬은 이런 내용을 지시가 아니라 데이터로 다루도록 되어 있습니다.
- 스킬은 네트워크 접속이나 외부 패키지 설치를 하지 않습니다(Python 표준 라이브러리만 사용).
