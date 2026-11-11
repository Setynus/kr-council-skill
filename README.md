# kr-council-skill — 한국어 위원회 의사결정 스킬 for Claude

[![Version](https://img.shields.io/badge/version-0.2.0-blue.svg)](CHANGELOG.md)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Language](https://img.shields.io/badge/lang-한국어-red.svg)](#kr-council-skill--한국어-위원회-의사결정-스킬-for-claude)
[![Claude Skill](https://img.shields.io/badge/Claude-Skill-orange.svg)](https://claude.ai)
[![Python](https://img.shields.io/badge/python-3.10%2B-yellow.svg)](tools/package_skill.py)
[![test](https://github.com/Setynus/kr-council-skill/actions/workflows/test.yml/badge.svg)](https://github.com/Setynus/kr-council-skill/actions/workflows/test.yml)

<h2 align="center">⚠️ 이 스킬은 병렬 방식으로 한 번에 하위 호출 11개가 들어 토큰을 많이 씁니다. ⚠️</h2>
<h2 align="center">⚠️ 사소한 질문에는 쓰지 마세요. ⚠️</h2>

> 선택지가 갈리는 결정을 위원 5명이 따로 분석하고, 익명으로 서로 검토한 뒤, 위원장이 판정하는 Claude 스킬. 최근 변경은 [버전 이력](#버전-이력)을 보세요.

선택지가 갈리는 결정을 **위원 5명이 따로 분석하고, 익명으로 서로 검토한 뒤, 위원장이 하나의 권고로 정리**하는 한국어 Claude 스킬입니다. 결과는 위원별 판단 카드와 위원장 최종 보고서가 담긴 HTML 대시보드로 나옵니다.

Karpathy의 llm-council 방식(자문 → 익명 상호 검토 → 의장 종합)을 Claude 안에서 구현한 `aiwithremy/claude-skills-llm-council`의 구성(위원 5종, 검토 3질문, 판정 5항목)을 따라, 한국어와 한국 상황(원화, 세금, 전세, 스마트스토어, 개인정보보호법 등)에 맞게 문장과 코드를 처음부터 새로 썼습니다. 자세한 출처는 [NOTICE.md](NOTICE.md)를 보세요.

> 위원 5명은 같은 모델이 관점만 바꿔 낸 의견이며, 독립된 전문가 5인이 아닙니다. 출력은 세무·법률·투자 조언이 아닙니다.

## 위원 소개

<div align="center">

<table width="100%">
<thead>
<tr>
<th width="34%" align="center">호칭<img src="docs/spacer.png" width="356" height="1" align="left" alt=""></th>
<th width="66%" align="center">맡은 관점</th>
</tr>
</thead>
<tbody>
<tr><td>투덜이 스머프&nbsp;(반대자)</td><td>이 선택이 실패한다면 가장 그럴듯한 이유를 찾는다</td></tr>
<tr><td>똘똘이 스머프&nbsp;(본질 탐구자)</td><td>진짜 목적이 뭔지,<br>선택지가 맞는 질문인지부터 묻는다</td></tr>
<tr><td>&emsp;&nbsp;&nbsp;화가 스머프&nbsp;(확장가)</td><td>잘 풀렸을 때의 상승 여력과 인접 기회를 본다</td></tr>
<tr><td>덜렁이 스머프&nbsp;(아웃사이더)</td><td>배경지식 없는 사람의 눈으로 당연한 것을 묻는다</td></tr>
<tr><td>재주꾼 스머프&nbsp;(실행가)</td><td>내일 아침 첫 일과 가장 작은 검증 단계를 본다</td></tr>
<tr><td>&emsp;&nbsp;&nbsp;파파 스머프&nbsp;(위원장)</td><td>다섯 답과 다섯 검토를 읽고 하나의 권고로 판정한다</td></tr>
</tbody>
</table>

</div>

## 설치

스킬 폴더는 `kr-council-skill/` 하나입니다. 보고서를 만들 때 **Python 3**이 필요합니다(표준 라이브러리만 사용, 별도 설치 없음).

### Claude Code
1. [Releases](../../releases)에서 `kr-council-skill.zip`을 받아 압축을 풀거나, 저장소를 복제합니다.
2. `kr-council-skill/` 폴더를 `~/.claude/skills/`(Windows는 `%USERPROFILE%\.claude\skills\`) 아래에 둡니다. 개발용으로는 복사 대신 링크를 걸어도 됩니다.
   - macOS/Linux: `ln -s <저장소>/kr-council-skill ~/.claude/skills/kr-council-skill`
   - Windows(관리자 권한 불필요): `mklink /J "%USERPROFILE%\.claude\skills\kr-council-skill" "<저장소>\kr-council-skill"`
3. Claude Code를 다시 시작합니다.

### claude.ai (웹·데스크톱)
1. [Releases](../../releases)에서 `kr-council-skill.zip`을 받습니다. 압축을 풀지 않습니다.
2. 설정의 스킬(Skills) 메뉴에서 zip 파일을 업로드하고 스킬을 켭니다. 메뉴 이름과 지원 요금제는 바뀔 수 있으니 Anthropic의 스킬 사용 안내를 확인하세요.
3. 코드 실행이 꺼져 있으면 HTML 보고서를 만들 수 없어, 같은 구성의 마크다운 보고서를 대화에 씁니다.

zip을 직접 만들려면 `python tools/package_skill.py`를 실행하면 `dist/kr-council-skill.zip`이 생깁니다.

## 사용법

Claude에게 이렇게 말하고 결정 상황을 알려 주세요.

- "위원회 열어줘. 스마트스토어에서 쿠키 파는데 낱개 2,800원과 12개입 24,000원 중 뭐에 집중할까?"
- "자문단 소집. 공무원 시험 3년차를 계속할지 IT 회사 인턴으로 갈지 정해야 해."
- "council 돌려줘. 전세 대출 2억을 받을지 월세로 갈지 고민이야."

선택지가 갈리고 잘못 고르면 비용이 큰 결정(이직, 창업, 가격, 투자, 기술 선택)에 씁니다. 정답이 하나인 사실 질문, 코드 리뷰, 요약, 글쓰기에는 쓰지 않습니다.

### 진행 순서
1. 질문을 의견 없이 중립적으로 정리하고 비용을 한 줄로 알립니다.
2. 위원 5명이 서로 보지 못한 채 **동시에** 답합니다.
3. 답을 A~E로 익명화해(순서는 스크립트가 섞음) 위원이 서로 검토합니다.
4. 위원장이 합의·충돌·놓친 점·권고·**가장 먼저 할 한 가지**를 정리합니다.
5. `council-reports/` 폴더에 HTML 보고서(`council-YYYYMMDD-HHMM.html`)와 같은 이름의 JSON을 저장합니다.

### 실행 방식 3가지
<div align="center">

<table width="100%">
<thead>
<tr>
<th width="20%" align="center">방식<img src="docs/spacer.png" width="58" height="1" align="left" alt=""></th>
<th width="28%" align="center">언제</th>
<th width="52%" align="center">비용·독립성</th>
</tr>
</thead>
<tbody>
<tr><td>병렬</td><td>Agent 도구가 있을 때<br>(Claude Code)</td><td>하위 호출 11개<br>(자문 5 + 검토 5 + 위원장 1),<br>독립성 높음</td></tr>
<tr><td>프롬프트&nbsp;묶음</td><td>Agent 도구가 없고 진짜 독립을 원할 때</td><td>사용자가 새 대화 10개를 직접 열어 결과를 붙여 넣음,<br>독립성 높음</td></tr>
<tr><td>단일&nbsp;세션</td><td>그 외</td><td>한 대화에서 차례로 진행,<br>빠르지만 독립성 낮음<br>(신뢰도를 낮춤)</td></tr>
</tbody>
</table>

</div>

실행 방식은 보고서 상단에 표시됩니다.

## 주의사항
- **비용**: 병렬 방식은 한 번에 하위 호출 11개가 들어 토큰을 많이 씁니다. 사소한 질문에는 쓰지 마세요.
- **개인정보**: 비밀번호, API 키, 주민등록번호 같은 정보는 질문에 넣지 마세요. 질문과 맥락은 하위 에이전트에게 전달됩니다.
- **한계**: 위원은 같은 모델이 낸 의견이라 모델 편향을 공유합니다. 보고서의 제도·수치에는 "확인 필요" 표시가 붙으니 공식 자료로 확인하세요.
- **저장 위치**: 보고서는 작업 폴더의 `council-reports/`에 만들어집니다. 민감한 내용이 있으면 공유 전에 지우세요.
- **Windows 한글**: 스크립트는 UTF-8로 읽고 씁니다. 깨져 보이면 터미널 인코딩을 확인하세요.

## 구성

<div align="center">

<table width="100%">
<thead>
<tr>
<th width="30%" align="center">경로<img src="docs/spacer.png" width="343" height="1" align="left" alt=""></th>
<th width="70%" align="center">내용</th>
</tr>
</thead>
<tbody>
<tr><td><code>kr-council-skill/</code></td><td>스킬 본체<br>(SKILL.md, scripts/, assets/, references/, evals/)</td></tr>
<tr><td><code>tests/</code>,<br><code>tools/</code></td><td>개발용 테스트와 도구<br>(<code>python -m unittest discover tests</code>)</td></tr>
<tr><td><code>comparison/</code></td><td>다른 위원회 스킬과의 블라인드 비교 질문·기준선·결과</td></tr>
<tr><td><code>docs/</code></td><td>설계서, 릴리스 점검 목록</td></tr>
</tbody>
</table>

</div>

## 검증 결과 요약
- 단위 테스트 70여 개(`python -m unittest discover tests`).
- 병렬 호출이 한 번의 응답에 묶였는지, 독립성이 깨지지 않았는지를 대화 기록으로 검사하는 도구(`tools/check_parallel.py`)가 있습니다.
- 다른 위원회 스킬과 질문 3개를 블라인드 비교했습니다(25점 만점 평균: 이 스킬 22.3, 단일 답변 17.3). 질문 수가 적고 같은 모델이 채점해 **일화적 비교**일 뿐입니다. 자세한 한계는 [`comparison/results/`](comparison/results/)의 보고서를 보세요.

## 버전 이력

<div align="center">

<table width="100%">
<thead>
<tr>
<th width="12%" align="center">버전<img src="docs/spacer.png" width="383" height="1" align="left" alt=""></th>
<th width="20%" align="center">날짜</th>
<th width="68%" align="center">핵심 변경</th>
</tr>
</thead>
<tbody>
<tr><td>0.2.0</td><td>2026&#8209;11&#8209;11</td><td>렌더러 입력 검증 강화,<br>JSON 시각별 저장,<br>프로젝트 문서·CI 정비</td></tr>
<tr><td>0.1.1</td><td>2026&#8209;11&#8209;11</td><td>출처 표기 정정<br>(원본과 구성이 같다는 점 명시)</td></tr>
<tr><td>0.1.0</td><td>2026&#8209;11&#8209;11</td><td>첫 공개 릴리스</td></tr>
</tbody>
</table>

</div>

전체 내용은 [CHANGELOG.md](CHANGELOG.md)를 보세요.

## 기여와 이슈
버그나 제안은 [GitHub Issues](https://github.com/Setynus/kr-council-skill/issues)로 남겨 주세요. 개발 방법은 [CONTRIBUTING.md](CONTRIBUTING.md), 보안 문제는 [SECURITY.md](SECURITY.md)를 보세요.

## 라이선스와 출처
MIT License ([LICENSE](LICENSE)). 방법론과 영감의 출처, 스머프 캐릭터 호칭에 대한 고지는 [NOTICE.md](NOTICE.md)를 보세요.
