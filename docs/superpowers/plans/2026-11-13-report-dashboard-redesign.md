# 보고서 대시보드 고도화 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** council 보고서 HTML을 결론 중심 대시보드(스티키 헤더, 큰 위원장 카드, 위원 소형 카드, 상성 지도, 다크모드, 인쇄)로 바꾼다.

**Architecture:** `render_report.py`가 지금처럼 HTML 전체를 만들고 위원 5명 상세를 모두 DOM에 넣는다(JS가 없어도 전부 보임). 정적 바닐라 JS는 표시 전환·스크롤·테마 토글·인쇄 호출만 맡고, council 데이터는 JS에 들어가지 않는다. 상성 지도는 Python이 인라인 SVG로 그린다.

**Tech Stack:** Python 3 표준 라이브러리만, `unittest`, 정적 HTML/CSS/JS 한 파일. 브라우저 확인은 이 환경의 Playwright(Chromium).

**Spec:** `docs/superpowers/specs/2026-11-13-report-dashboard-redesign-design.md`

## Global Constraints

- `tests/test_render_report.py`의 `html.count('class="advisor-card"') == 5`를 유지한다. 상세 패널만 `class="advisor-card"`(속성 문자열 그대로, 클래스 덧붙임 금지)를 쓰고 소형 카드는 `class="advisor-mini"`를 쓴다.
- 위원·질문·제목 텍스트는 모두 `_e()`로 이스케이프한다. `<script>`는 템플릿의 정적 코드만이며 council 데이터를 JS 문자열·JSON으로 심지 않는다. SVG의 `<text>`·`<title>`·`aria-label`도 `_e()`를 거친다.
- 템플릿 치환은 한 번의 `re.sub`로 끝낸다(값 안의 `{{...}}` 재치환 금지).
- `파파스머프`는 `render_report.py`의 상수 `CHAIR_NAME` 한 곳에서만 정의한다. SKILL.md, `references/`, JSON 규격, `validate` 규칙은 수정하지 않는다.
- 외부 리소스 금지: 렌더 결과에 `http://`·`https://` 리소스 로드(`src`, 스타일시트 `href`, `@import`, `url(...)`)가 없다. 외부 폰트·CDN 없음.
- 한계 문구(`DISCLAIMER`)와 실행 방식 배너는 JS 유무·전환 상태·인쇄와 무관하게 항상 보인다. `hidden` 속성이나 인라인 `display:none`을 쓰지 않는다.
- 점수·순위 같은 수치를 만들지 않는다. 상호 지지 쌍의 굵기 강조는 "점수가 아님"을 범례에 쓴다.
- `<html lang="ko">`, 한국어 폰트 스택, 기존 색 토큰 의미(`--accent` 등) 유지. 새 토큰은 추가 가능.
- 다크 테마는 `@media (prefers-color-scheme: dark)`(단 `:root[data-theme="light"]` 제외)와 `:root[data-theme="dark"]` 두 곳. `localStorage` 읽기·쓰기는 모두 try/catch. `prefers-reduced-motion: reduce`이면 이동 효과·부드러운 스크롤을 끈다.
- 인쇄는 헤더·버튼·소형 카드를 숨기고 밝은 테마로 고정하며 위원 상세와 검토 표를 모두 펼친다.
- 작업 브랜치는 `feat/dashboard-redesign`. `main` 직접 수정 금지. 커밋 메시지 끝에 다음 두 줄을 붙인다:
  `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>` / `Claude-Session: https://claude.ai/code/session_01MQoyt78EeFcMC8aWA3UK7B`
- 실행 환경: Python 3.9 이상(`str.removesuffix` 사용 중), 저장소 루트에서 `python -m unittest discover -s tests` 로 전체 테스트.

## Review Focus

1. 위원이 자기 자신을 `weakest`로 고른 데이터(`validate`가 막지 않음) — 렌더가 실패하지 않고 노드의 점선 고리로 나온다 (Task 3).
2. 위원 이름·질문·제목에 `<script>`, `"`, `{{ADVISOR_CARDS}}` 같은 문자열 — 소형 카드·SVG·위원장 카드 어디에도 태그로 살아나지 않고 재치환되지 않는다 (Task 2, 3).
3. 같은 위원 쌍에 지지와 비판이 서로 겹침(A→B 지지, B→A 비판 또는 모두가 같은 위원을 지지) — 간선 10개가 모두 그려지고 서로 가려지지 않는다 (Task 3).
4. `localStorage`가 막혔거나 저장된 값이 `"light"`/`"dark"`가 아닌 쓰레기 값 — 시스템 설정으로 정상 표시되고 오류가 없다 (Task 4, 5).
5. 공백 없는 매우 긴 위원 문장·질문을 375px 폭에서 볼 때 — 가로 스크롤이 생기지 않는다(`overflow-wrap`). 다크가 저장된 상태에서 인쇄해도 밝은 테마다 (Task 4, 5).

---

### Task 1: 위원 프로필 표와 `CHAIR_NAME`

**Files:**
- Modify: `kr-council-skill/scripts/render_report.py:144-151` (`ADVISOR_NAMES` 정의부), `render()`의 `slots`
- Modify: `kr-council-skill/assets/report.html:67` (위원장 제목)
- Test: `tests/test_render_report.py`

**Interfaces:**
- Produces: `ADVISOR_PROFILE: dict[str, dict[str, str]]` — 키는 `ADVISOR_IDS`의 5개 id, 값은 `{"nick": str, "role": str, "blurb": str}`. 예: `ADVISOR_PROFILE["contrarian"] == {"nick": "투덜이 스머프", "role": "반대자", "blurb": "이 선택이 실패한다면 가장 그럴듯한 이유가 무엇인지 찾는다"}`.
- Produces: `ADVISOR_NAMES`는 `ADVISOR_PROFILE`에서 파생(`f"{nick}({role})"`), 값은 현재와 완전히 같다.
- Produces: `CHAIR_NAME = "파파스머프"`, 템플릿 슬롯 `{{CHAIR_NAME}}`.

- [ ] **Step 1: 실패하는 테스트 작성** (`RenderTests` 또는 새 `ProfileTests` 클래스)
  - `test_advisor_names_derived_from_profile`: `ADVISOR_NAMES == NAMES`(테스트 파일 상단의 기존 `NAMES`)이고 `set(ADVISOR_PROFILE) == set(ADVISOR_IDS)`.
  - `test_blurbs_are_sentences_from_advisors_md`: 각 `ADVISOR_PROFILE[i]["blurb"]`가 `kr-council-skill/references/advisors.md` 본문에 그대로 포함된다(`assertIn`).
  - `test_chair_name_comes_from_constant`: `render(sample(), template())`에 `CHAIR_NAME`이 있고, `template()` 원문에는 `"파파스머프"`가 없다.
- [ ] **Step 2: 실패 확인** — `python -m unittest tests.test_render_report -v` → 새 3개가 ImportError/FAIL.
- [ ] **Step 3: 구현** — `ADVISOR_PROFILE`을 `render_report.py`에 추가(소개 문구는 아래 표의 문자열을 그대로 사용, 모두 `advisors.md`의 "관점" 문장 부분 문자열), `ADVISOR_NAMES`를 파생으로 교체, `CHAIR_NAME` 상수와 `slots["CHAIR_NAME"] = _e(CHAIR_NAME)` 추가, 템플릿 h2를 `{{CHAIR_NAME}}(위원장)의 최종 검토 보고서`로 변경.

  | id | nick | role | blurb |
  |:---:|:---:|:---:|:---|
  | contrarian | 투덜이 스머프 | 반대자 | 이 선택이 실패한다면 가장 그럴듯한 이유가 무엇인지 찾는다 |
  | first_principles | 똘똘이 스머프 | 본질 탐구자 | 질문 뒤에 있는 진짜 목적을 묻는다 |
  | expansionist | 화가 스머프 | 확장가 | 다른 위원이 놓친 상승 여력과 인접 기회를 찾는다 |
  | outsider | 덜렁이 스머프 | 아웃사이더 | 배경지식이 전혀 없는 사람처럼, 눈앞의 내용만으로 반응한다 |
  | executor | 재주꾼 스머프 | 실행가 | 이것이 실제로 가능한지, 가장 빠른 길이 무엇인지만 본다 |

- [ ] **Step 4: 통과 확인** — `python -m unittest discover -s tests` 전체 통과(`test_assemble`의 `ADVISOR_NAMES` 비교 포함).
- [ ] **Step 5: 커밋** — `git commit -m "refactor: 위원 프로필 표와 위원장 이름 상수화"`

---

### Task 2: 소형 카드, 위원장 카드 구조, 위원 상세 패널

**Files:**
- Modify: `kr-council-skill/scripts/render_report.py` (`_cards`, 새 `_mini_cards`, `render`의 `slots`)
- Modify: `kr-council-skill/assets/report.html` (본문 구조만. 스타일·JS는 Task 4)
- Test: `tests/test_render_report.py`

**Interfaces:**
- Consumes: `ADVISOR_PROFILE`, `CHAIR_NAME`, `_e` (Task 1, 기존).
- Produces: `_mini_cards(data: dict) -> str` — 위원 5명 각각 `<a class="advisor-mini" href="#advisor-<id>" data-advisor="<id>">`(이름 `adv["name"]`과 `ADVISOR_PROFILE[id]["blurb"]` 포함). 클래스 속성에 다른 클래스를 덧붙이지 않는다.
- Produces: `_cards(data)`의 각 `<article class="advisor-card" ...>`에 `id="advisor-<id>"` 추가(기존 `data-advisor` 유지, 클래스 속성 문자열은 그대로).
- Produces: 슬롯 `{{MINI_CARDS}}`.
- Produces(템플릿 DOM 계약, Task 4가 사용): 위원장 카드 `<section class="verdict hero" id="report">` 안에 `<div class="pane pane-report" data-pane="report">`(위원장 보고서)와 `<div class="pane pane-advisors" data-pane="advisors">`(`{{ADVISOR_CARDS}}`)를 이 순서로 둔다. 본문 순서: 질문(`id="question"`) → 위원장 카드 → 위원 소형 카드 섹션(`id="advisors"`, `{{MINI_CARDS}}`) → 상성 지도 섹션(`id="affinity"`, 슬롯은 Task 3) → 검토 표 섹션(`id="reviews"`).

- [ ] **Step 1: 실패하는 테스트 작성**
  - `test_mini_cards_one_per_advisor_with_blurb`: 렌더 결과에서 `class="advisor-mini"` 5개, 각 `href="#advisor-<id>"`와 해당 blurb 포함, `class="advisor-card"`는 여전히 정확히 5개.
  - `test_detail_panels_have_anchor_ids`: 5개 id 모두 `id="advisor-<id>"`로 존재.
  - `test_mini_cards_escape_advisor_name`: `sample()`의 한 위원 `name`을 `"<script>alert(1)</script>{{ADVISOR_CARDS}}"`로 바꾸면(렌더 전 `validate` 통과 확인) 결과에 원문 `<script>alert(1)</script>`가 없고 `&lt;script&gt;`가 있으며, 치환되지 않은 `{{ADVISOR_CARDS}}`가 이름 텍스트로만 남고 카드가 중복 생성되지 않는다(`class="advisor-card"` 5개).
  - `test_sections_order`: 렌더 결과에서 `id="question"`, `id="report"`, `id="advisors"`, `id="affinity"`, `id="reviews"` 위치가 이 순서다(`affinity`는 Task 3 전까지 빈 섹션으로 존재하게 한다).
- [ ] **Step 2: 실패 확인** — 새 테스트 FAIL.
- [ ] **Step 3: 구현** — 위 인터페이스대로 `_mini_cards` 추가, `_cards`에 id 추가, 템플릿 본문 재배치, `slots["MINI_CARDS"]` 추가. 슬롯이 늘어도 `re.sub` 한 번 치환을 유지한다.
- [ ] **Step 4: 통과 확인** — `python -m unittest discover -s tests` 전체 통과.
- [ ] **Step 5: 커밋** — `git commit -m "feat: 위원장 카드 구조와 위원 소형 카드 추가"`

---

### Task 3: 상성 지도(SVG)

**Files:**
- Modify: `kr-council-skill/scripts/render_report.py` (새 `_affinity_edges`, `_affinity_map`, `render`의 `slots`)
- Modify: `kr-council-skill/assets/report.html` (`{{AFFINITY_MAP}}` 슬롯을 `id="affinity"` 섹션에 연결, 섹션 제목 "상성 지도")
- Test: `tests/test_render_report.py`

**Interfaces:**
- Consumes: `data["reviews"]`, `data["mapping"]`, `ADVISOR_IDS`, `ADVISOR_PROFILE` (Task 1), `_e`.
- Produces: `_affinity_edges(data: dict) -> list[dict]` — 길이 항상 10. 각 원소 `{"from": id, "to": id, "kind": "support" | "critique", "mutual": bool}`. 검토자 → `mapping[strongest]`는 `support`, → `mapping[weakest]`는 `critique`. `mutual`은 `support`이면서 반대 방향 `support`가 존재할 때만 True.
- Produces: `_affinity_map(data: dict) -> str` — `<svg role="img" aria-label=...>` 하나. 위원 id 순서(`ADVISOR_IDS`)로 5각형 꼭짓점에 노드를 놓고 라벨은 `ADVISOR_PROFILE[id]["role"]`. 지지는 실선, 비판은 점선(`stroke-dasharray`), 화살표 마커 포함, 상호 지지는 클래스 `mutual`. 같은 위원 쌍의 양방향 간선과 같은 대상에 몰린 간선이 서로 가리지 않도록 간선은 직선이 아닌 약한 곡선이거나 평행 오프셋으로 그린다. 간선 요소는 모두 `class="edge support|critique"`(+`mutual`)와 `data-from`·`data-to`를 가진다. 자기 자신을 대상으로 한 `critique`는 노드 옆 작은 점선 고리로 그리며 클래스에 `self`를 추가한다. SVG 아래에 범례(실선=지지, 점선=비판, 굵은 선=서로 지지, "점수가 아니라 이 질문에서의 검토 결과"). 슬롯 `{{AFFINITY_MAP}}`.

- [ ] **Step 1: 실패하는 테스트 작성**
  - `test_affinity_edges_has_ten_with_kinds`: `sample()`의 `_affinity_edges` 길이 10, `support` 5·`critique` 5.
  - `test_affinity_edges_marks_mutual_support`: `sample()`을 고쳐 두 위원이 서로를 `strongest`로 고르게 한 뒤(자기 지지는 `validate`가 막으므로 서로 다른 위원) 해당 두 간선만 `mutual=True`.
  - `test_affinity_map_renders_ten_edges_and_legend`: 렌더 결과의 `class="edge ` 포함 요소가 정확히 10개, `stroke-dasharray`가 있는 요소가 비판 개수와 같고, 범례 문구 "점수"가 있다.
  - `test_affinity_map_escapes_labels`: 한 위원 `name`에 `<b>x</b>`를 넣어도 SVG 안에 원문 `<b>x</b>`가 없다.
  - `test_affinity_map_survives_self_critique`: `weakest`가 검토자 자신인 데이터로 `render`가 예외 없이 성공하고 고리 요소(`class="edge critique self"`)가 있다. 간선 총 수는 여전히 10.
  - `test_affinity_map_hub_target_keeps_all_edges`: 5명 모두가 같은 위원(검토자 본인 제외)을 `strongest`로 고른 데이터에서도 간선 10개가 모두 출력된다.
- [ ] **Step 2: 실패 확인** — 새 테스트 FAIL.
- [ ] **Step 3: 구현** — 위 인터페이스대로. 5각형 좌표·곡률·화살표 크기는 구현자가 정한다(viewBox 기준 상대 좌표, 고정 폭 없이 `width:100%`로 줄어드는 SVG).
- [ ] **Step 4: 통과 확인** — `python -m unittest discover -s tests` 전체 통과.
- [ ] **Step 5: 커밋** — `git commit -m "feat: 상호 검토 상성 지도(SVG) 추가"`

---

### Task 4: 헤더·테마·전환 JS·호버·인쇄 (템플릿 스타일과 정적 스크립트)

**Files:**
- Modify: `kr-council-skill/assets/report.html` (스타일, 스티키 헤더, 정적 `<script>` 1개)
- Test: `tests/test_render_report.py`

**Interfaces:**
- Consumes: Task 2의 DOM 계약(`#report`, `.pane[data-pane]`, `.advisor-mini[data-advisor]`, `#advisor-<id>`), Task 3의 `.edge[data-from][data-to]`.
- Produces(스크립트 계약): `<script>`는 템플릿에 **정확히 1개**, council 값 없음. `<html>`에 `js` 클래스를 붙이는 한 줄은 body 시작 직후 이 스크립트 첫머리에서 실행한다. 스크립트는 다음만 한다: (a) 소형 카드 클릭 → 그 `data-advisor`를 선택하고 위원장 카드로 스크롤, (b) 위원장 카드 상단의 전환 버튼(`.js-only`)으로 "보고서/위원 판단" 전환, (c) 테마 토글(`data-theme` 설정, `localStorage`는 try/catch, 저장값이 `"light"`/`"dark"`가 아니면 무시), (d) 인쇄 버튼 → `window.print()`, (e) 노드 hover/focus 시 상성 지도의 해당 간선 강조(선택 기능).
- Produces(CSS 계약): `.js`가 없으면 모든 `.pane`이 보이고 `.js-only`는 숨겨지며(`display:none`은 스타일시트에서만, 인라인 금지), `.js`가 있으면 선택된 위원 1명의 `.advisor-card`만 보인다. 헤더 앵커는 `scroll-margin-top`으로 가려지지 않는다.

- [ ] **Step 1: 실패하는 테스트 작성**
  - `test_single_static_script_without_council_text`: 렌더 결과에서 `<script` 출현이 정확히 1회이고, 그 블록 텍스트가 `template()`의 스크립트 블록과 같다. 질문에 `"</script><script>alert(1)</script>"`를 넣어 렌더해도 `<script` 출현은 여전히 1회.
  - `test_no_external_resources`: 렌더 결과에 `re.search(r'(src|href)="https?:|@import|url\(\s*[\'"]?https?:', html)`가 없다.
  - `test_no_hidden_content_without_js`: `re.search(r'<[^>]+\shidden[\s>]', html)`가 없고 `style="display:none`이 없다. `class="banner"`와 `class="disclaimer"`가 존재한다.
  - `test_theme_and_print_css_present`: `prefers-color-scheme: dark`, `data-theme="dark"`, `data-theme="light"`, `prefers-reduced-motion`, `@media print`가 모두 있다.
  - `test_chair_card_comes_before_advisor_minis`: `class="verdict hero"`가 `id="advisors"`보다 앞에 있다(구조 회귀 방지).
- [ ] **Step 2: 실패 확인** — 새 테스트 일부 FAIL(스크립트·CSS가 아직 없음).
- [ ] **Step 3: 구현** — 스티키 헤더(스킬 이름 `kr-council-skill`, 바로가기 `#question`·`#report`·`#advisors`·`#affinity`·`#reviews`, 테마·인쇄 버튼은 `.js-only`), 호버/포커스 효과(`translateY(-2px)`+그림자, `:focus-visible` 윤곽선), `overflow-wrap:anywhere`로 긴 문자열 줄바꿈, 모바일에서 소형 카드 1~2열, `@media print` 규칙(밝은 토큰을 `:root[data-theme]`보다 높은 특이성으로 강제, 헤더·`.js-only`·소형 카드 숨김, 모든 `.pane`과 `.advisor-card` 표시, `break-inside: avoid`). 기존 `@media (prefers-color-scheme: dark)` 블록은 `:root:not([data-theme="light"])`로 한정하고 `:root[data-theme="dark"]` 블록을 추가한다.
- [ ] **Step 4: 통과 확인** — `python -m unittest discover -s tests` 전체 통과.
- [ ] **Step 5: 커밋** — `git commit -m "feat: 스티키 헤더, 테마 토글, 위원 판단 전환, 인쇄 스타일 추가"`

---

### Task 5: 브라우저 검증, 문서, PR

**Files:**
- Create(저장소 밖, 임시): 스크래치패드의 `verify_report.js`와 샘플 JSON — **저장소에 커밋하지 않는다**
- Modify: `CHANGELOG.md` (`[Unreleased]`), `README.md` (보고서 설명이 있는 부분만 최소 수정)

**Interfaces:**
- Consumes: 위 모든 Task. 샘플 council JSON은 `tests/test_render_report.py`의 `sample()` 값을 `json.dumps(..., ensure_ascii=False)`로 내보내 쓴다(`python -c`로 한 번 생성).

- [ ] **Step 1: 샘플 보고서 생성** — `python kr-council-skill/scripts/render_report.py render <샘플.json> --out <스크래치패드>/report.html` → 종료 코드 0과 `저장했습니다: ...`.
- [ ] **Step 2: Playwright로 다음을 확인하고 각 결과를 기록**(`require('playwright')`, `chromium.launch()`; 사람이 볼 스크린샷은 `deviceScaleFactor: 2`):
  1. 라이트/다크(`colorScheme` 에뮬레이션) 스크린샷 — 텍스트 대비 육안 확인, 콘솔 오류 0건.
  2. 폭 375px: `document.documentElement.scrollWidth <= window.innerWidth`(가로 스크롤 없음). 공백 없는 400자 위원 문장을 넣은 샘플로도 동일.
  3. `javaScriptEnabled: false`: 위원 5명 상세, 배너, 한계 문구가 모두 보이고(`isVisible`) 소형 카드 앵커가 점프한다.
  4. JS 켜짐: 소형 카드 클릭 → 해당 `#advisor-<id>`만 보이고 위원장 카드 상단이 뷰포트에 들어옴 + 헤더에 가려지지 않음. "보고서" 버튼으로 복귀.
  5. 테마 토글: `localStorage`에 `"dark"` 저장 후 새로고침해도 유지. `localStorage.setItem`이 던지는 컨텍스트와 저장값 `"junk"` 컨텍스트에서 오류 없이 시스템 설정으로 표시.
  6. `page.emulateMedia({ media: 'print' })` + 다크 저장 상태: 헤더·소형 카드 숨김, 배경 밝음(`getComputedStyle(document.body).backgroundColor`가 흰색 계열), 위원 상세 5개 모두 표시, 배너·한계 문구 표시.
  7. 상성 지도: SVG 안 `.edge` 10개, 노드 hover 시 해당 간선 강조 클래스.
- [ ] **Step 3: 문서** — `CHANGELOG.md`의 `[Unreleased]`에 "변경/추가"로 새 화면 구성·상성 지도·다크모드·인쇄·JS 없이도 읽힘을 기록하고, **수행하지 못한 확인은 "알려진 한계"에 미검증으로 적는다**(예: 실제 인쇄 미리보기는 Chromium 에뮬레이션만 확인). 버전 번호는 올리지 않는다. README는 보고서 설명이 있는 문장이 새 구조와 어긋날 때만 고친다.
- [ ] **Step 4: 전체 테스트** — `python -m unittest discover -s tests` 전체 통과, 출력의 `OK` 확인.
- [ ] **Step 5: 커밋·푸시·PR** — `git commit -m "docs: 보고서 대시보드 변경 이력 기록"`, `git -c push.negotiate=true push -u origin feat/dashboard-redesign`, 초안(draft) PR 생성(저장소에 PR 템플릿이 있으면 그 제목 구조를 따르고, 본문에는 Step 2에서 실제로 수행한 확인과 미검증 항목만 적는다).

---

## Self-Review 결과

- **스펙 커버리지**: 헤더·테마·인쇄(4.3)=Task 4, 위원장 카드·전환(4.1)=Task 2+4, 상성 지도(4.2)=Task 3, 호버·모션(4.4)=Task 4, 구현 제약 1~8(5절)=Global Constraints와 Task 1~4 테스트, 변경 범위(6절)=Task 5, 검증(7절)=Task 1~4 단위 테스트+Task 5 브라우저 확인. 빠진 항목 없음.
- **타입 일관성**: `ADVISOR_PROFILE`(Task 1)을 Task 2(`blurb`)·Task 3(`role`)이 같은 키로 사용. `_affinity_edges` 반환 키(`from`, `to`, `kind`, `mutual`)는 Task 3 내부와 테스트가 동일. DOM 계약(`#report`, `.pane[data-pane]`, `.advisor-mini`, `#advisor-<id>`, `.edge`)은 Task 2·3에서 만들고 Task 4·5가 사용.
- **스펙 대비 조정 1건**: 스펙에 없던 `.edge self` 클래스를 자기 비판 테스트용으로 정했다(구현 세부).
