# 보고서 디자인 시스템 적용 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 위원회 보고서 HTML에 전북특별자치도 디자인 시스템, 상위·하위 탭, A4 1장 자동 맞춤 인쇄를 적용한다.

**Architecture:** 기존 구조 유지. Python(`render_report.py`)이 모든 내용을 HTML에 넣고(위원 문장은 한 글자도 바꾸지 않음), 템플릿의 정적 JS 하나가 `html.js` 클래스 아래에서 탭·하위 탭·인쇄 단계만 전환한다. JS가 없으면 모든 패널이 펼쳐져 보인다. 인쇄 스타일은 `body.print-mode` 한 벌로 쓰고, JS가 `beforeprint`/버튼에서 이 클래스를 붙여 화면에서 높이를 재 단계(1~3)를 정한다.

**Tech Stack:** Python 3.10+ 표준 라이브러리, 바닐라 JS, CSS 변수. 테스트는 `python -m unittest discover tests`. 브라우저 검증은 일회용 Playwright 스크립트(저장소에 커밋하지 않음).

**Spec:** `docs/superpowers/specs/2026-11-16-report-design-system-design.md`

**시각 기준(캔버스 사본):** `docs/superpowers/plans/assets/report-canvas-reference.dc.html` — Claude Design 캔버스의 최종본(읽기 전용 참고 자료. 브라우저에서 열어도 렌더되지 않는다. CSS 값·마크업 구조·문구·아이콘 path·`fs()` 분할 로직을 텍스트로 읽는 용도이며 저장소의 배포 파일이 아니다). 원본 링크 `https://claude.ai/artifact/XrX8Atnb74yqR1TSoBN8Sf`는 CLI에서 열 수 없다고 가정한다.

## 실행 환경 (이식 안내)

이 계획서는 Claude Code CLI(또는 다른 에이전트 플랫폼)에서 저장소만 체크아웃한 상태로 실행할 수 있게 쓴다. 특정 클라우드 세션·MCP·Artifact 도구에 의존하지 않는다.

- **작업 위치:** 저장소 루트(`kr-council-skill` 저장소를 클론한 폴더). 문서의 모든 경로는 저장소 루트 기준 상대 경로다. 저장소 안에 `kr-council-skill/` 하위 폴더(스킬 본체)가 있으니 `kr-council-skill/scripts/...`와 `scripts/...`를 혼동하지 않는다.
- **브랜치:** `feat/report-design-system`. 없으면 `git switch -c feat/report-design-system` 후 설계 문서·이 계획서가 포함된 커밋(`docs: 보고서 디자인 시스템 …`)을 가져온다(`git log --oneline origin/feat/report-design-system` 또는 사용자가 건넨 번들/패치).
- **필수:** Python 3.10 이상, git. 테스트는 `python -m unittest discover tests`(저장소 루트). 추가 패키지 없음.
- **선택(Task 8):** `pip install playwright` + `python -m playwright install chromium`. 설치할 수 없으면 Task 8의 브라우저 검증을 "미실시"로 기록하고 나머지를 끝낸다. 통과한 것처럼 쓰지 않는다.
- **푸시·PR:** `git push -u origin feat/report-design-system`, `gh pr create`. 인증이 없으면 푸시 직전까지 하고 사용자에게 알린다. 프록시 환경에서 푸시가 실패하면 `git -c push.negotiate=true push …`를 시도한다.
- **커밋 꼬리말:** 사용 중인 플랫폼의 기본 공동 저자 표기를 따른다(예: `Co-Authored-By: Claude <noreply@anthropic.com>`). 세션 URL 줄은 있을 때만 넣는다.
- **샘플 데이터:** 실제 보고서 JSON(`council-20261112-0748.json`)은 저장소에 없다. 작업 폴더의 `council-reports/`(gitignore)에 있으니 없으면 `tests/test_render_report.py`의 `sample()` 헬퍼로 만든 데이터를 임시 JSON으로 저장해 쓴다. 긴 보고서도 `sample()`의 문장을 3배로 이어 붙여 만든다.
- **언어:** 사용자 응답·PR 본문·커밋 메시지는 한국어. 코드 식별자는 영어.
- **사용자 확정 사항(2026-11-16):** `advisors.md`는 기존 "관점" 문장을 바꾸지 않고 `**화면 소개:**` 한 줄만 추가한다. 위원 프롬프트는 바뀌지 않는다(Task 1).

## Global Constraints

- 단일 HTML, 외부 URL·폰트·CDN 없음, Python 표준 라이브러리만. `<script>`는 템플릿에 정적 블록 하나이고 council 텍스트가 들어가지 않는다(기존 `test_single_static_script_without_council_text` 유지).
- 모든 council·사용자 텍스트는 `_e()`로 이스케이프. 값 안의 `{{...}}`가 다시 치환되지 않는 단일 `re.sub` 유지.
- JS 없음/`init` 예외 시 `js` 클래스를 떼어 모든 내용이 보인다(`classList.remove('js')` 테스트 유지).
- 위원 문장은 요약·수정 금지. `s1`/`rest` span으로 나눠도 이어 붙이면 원문과 같아야 한다.
- council JSON 규격, `validate`, `SKILL.md` 본문은 바꾸지 않는다.
- 토큰(라이트/다크): 배경 `#f8f8f8`/`#0f1216`, 카드 `#ffffff`/`#1c2127`, 연한 면 `#eff5ff`/`#263142`, 글자 `#1d1d1d`/`#e9ebee`, 보조 `#555555`/`#adb1b8`, 선 `#d8d8d8`/`#3c4046`, 강조 `#246beb`/`#5b96ff`, 브랜드 `#034694`/`#4072b7`, 브랜드 위 글자 `#ffffff`/`#fcfcfc`, 경고 `#eb003b`/`#ff656c`. 인쇄 선 `#616174`. 굵기 400/700만. 호버 그림자·이동 없음. 포커스 링 2px `--primary` 오프셋 2px. 터치 대상 44px 이상.
- 글자 크기(화면): 32/28/21/19/17/15px. 인쇄: 21.33/16/12.67/12/10.67px. 폰트: `'Pretendard GOV','Apple SD Gothic Neo','Malgun Gothic','Noto Sans KR',sans-serif`(파일 포함 안 함).
- 커밋 메시지·PR 설명 끝의 공동 저자·생성 표기는 실행 플랫폼의 기본 규칙을 따른다(위 "실행 환경" 참고). 아래 Task의 `(끝 줄 규칙 포함)`은 이를 뜻한다.
- 작업 브랜치 `feat/report-design-system`(이미 존재, 설계 문서 2커밋 포함).

## Review Focus

1. 문장 끝 표시가 없거나 "3.5만 원"·"(1) …"처럼 마침표가 문장 중간에 있는 항목 → 잘못 자르지 않고 원문이 보존된다. (Task 2)
2. 위원 이름·응답에 `<script>`, `&`, `{{ADVISOR_CARDS}}`가 들어와도 새 슬롯(검토 카드, 탭 라벨, 지도 링크)에서 이스케이프되고 재치환되지 않는다. (Task 3, 4)
3. JS가 꺼진 상태에서 상위·하위 탭에 숨은 내용이 없다(모든 패널·카드가 DOM에 있고 `hidden`/`display:none` 인라인 없음). (Task 4, 5)
4. 항목 길이가 3배인 보고서에서도 인쇄 3단계가 1쪽에 들어가거나, 못 들어가면 2쪽으로 늘어나되 내용이 잘리지 않는다. (Task 7)
5. 저장된 테마값이 이상하거나 localStorage가 막혀도 라이트/시스템 설정으로 정상 표시된다(기존 동작 유지). (Task 6)

---

### Task 1: 위원 "맡은 관점" 문구 (README → 화면)

**Files:**
- Modify: `kr-council-skill/references/advisors.md` (각 위원 절에 `**화면 소개:**` 한 줄 추가. 기존 `관점:` 문장은 건드리지 않는다. 위원 프롬프트에는 관점·질문·금지사항만 들어가므로(SKILL.md 52행) 동작이 바뀌지 않는다)
- Modify: `kr-council-skill/scripts/render_report.py` (`ADVISOR_PROFILE[*]["blurb"]`)
- Modify: `tests/test_render_report.py` (`test_blurbs_are_sentences_from_advisors_md`, `test_mini_cards_one_per_advisor_with_blurb`)

**Interfaces:**
- Produces: `ADVISOR_PROFILE[id]["blurb"]: str` — README "위원 소개" 표의 두 줄을 `"\n"`으로 이은 문자열. 줄 수는 위원마다 1~2줄.

- [ ] **Step 1: 실패하는 테스트로 고친다** — `test_blurbs_are_sentences_from_advisors_md`는 `blurb.split("\n")`의 모든 줄이 advisors.md에 있어야 통과하도록, `test_mini_cards_one_per_advisor_with_blurb`는 각 줄이 HTML에 있어야 통과하도록 바꾼다. 기대값: 반대자 `뭐든 싫다며 문제부터 짚는다` / `선택이 실패할 때를 대비한 가장 그럴듯한 이유를 찾는다`; 본질 탐구자 `진짜 목적이 뭔지, 선택지가 맞는 질문인지 부터 묻는다`(README 원문 그대로, 띄어쓰기도 유지); 확장가 `큰 그림과 가능성을 그린다` / `잘 풀렸을 때의 상승 여력과 인접 기회를 본다`; 아웃사이더 `배경지식 없는 사람의 순진한 시각으로 당연한 것을 묻는다`; 실행가 `일단 만들어 본다` / `가장 작은 검증 단계를 본다`.
- [ ] **Step 2:** `python -m unittest tests.test_render_report.ProfileTests tests.test_render_report.DashboardStructureTests -v` → 두 테스트 FAIL.
- [ ] **Step 3:** advisors.md 각 위원 절에 `**화면 소개:** <줄1> / <줄2>` 한 줄을 추가하고(사용자 확정: 기존 `관점:` 문장·질문·금지사항은 한 글자도 바꾸지 않는다. 각 줄이 문자열로 존재하기만 하면 된다), `ADVISOR_PROFILE`의 `blurb`를 위 문구로 교체한다. HTML 쪽 줄바꿈 표시는 Task 3에서 한다.
- [ ] **Step 4:** 같은 명령 → PASS. `python -m unittest discover tests` 전체 통과(다른 테스트에 영향 없음).
- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: 위원 맡은 관점을 README 위원 소개 문구로 통일"` (끝 줄 규칙 포함)

### Task 2: 첫 문장 분리 함수 (캔버스 사본의 `fs()`는 JS 자르기이므로 따르지 않고 이 Task의 정규식 규칙을 쓴다)

**Files:**
- Modify: `kr-council-skill/scripts/render_report.py`
- Test: `tests/test_render_report.py` (새 클래스 `SentenceSplitTests`)

**Interfaces:**
- Produces: `split_first_sentence(text: str) -> tuple[str, str]` — 첫 문장과 나머지. `a + b == text`(공백 포함 그대로)여야 한다. `_sent(text: str) -> str` — `<span class="s1">…</span><span class="rest">…</span>`(둘 다 `_e()` 적용, 나머지가 빈 문자열이면 `rest` span 생략).

- [ ] **Step 1: 테스트** — 모두 `a + b == text`를 확인하고 각각:
  `"A는 B다. C도 D다."` → `("A는 B다.", " C도 D다.")`; `"끝 표시 없음"` → `("끝 표시 없음", "")`; `"가격은 2.7만 원이다. 다음 문장."` → 첫 문장이 `"가격은 2.7만 원이다."`; `"(1) 청구액이 3만 원 이상이다. (2) 정지가 발생했다."` → 첫 문장이 `"(1) 청구액이 3만 원 이상이다."`; `_sent("<b>x</b>. y")` 결과에 `&lt;b&gt;`가 있고 `<b>`가 없다.
- [ ] **Step 2:** `python -m unittest tests.test_render_report.SentenceSplitTests -v` → FAIL(함수 없음).
- [ ] **Step 3:** `re.search(r"(?<=[.!?])\s", text)` 첫 일치 위치에서 자른다. 구분 공백은 `rest`의 맨 앞에 둔다.
- [ ] **Step 4:** 같은 명령 → PASS.
- [ ] **Step 5: Commit** — `feat: 위원 문장을 보존한 채 첫 문장 span으로 나누는 함수 추가`

### Task 3: 위원장 보고서·위원 카드·검토 카드 마크업

**Files:**
- Modify: `kr-council-skill/scripts/render_report.py` (`_verdict`, `_cards`, `_mini_cards`, `_review_table` → `_review_cards`, 슬롯 표)
- Modify: `tests/test_render_report.py`

**Interfaces:**
- Consumes: `_sent`, `_e`, `ADVISOR_PROFILE`.
- Produces(마크업 계약, Task 5·6이 사용):
  - `_verdict(data)`: `<div class="chips">`(신뢰도·소수 의견), `<div class="rec-grid">`에 `<div class="rec">`(권고, 첫 문장은 `.rec-first`, 나머지 `.rec-rest`)와 `<div class="first">`(가장 먼저 할 한 가지, `_sent` 적용), 이어서 `<div class="subtabs js-only" role="group" aria-label="최종 보고서 하위 구역">` 안에 `<button type="button" data-sub="agree|blind|clash">`, 이어서 `<div class="sub" data-sub-panel="agree|blind|clash">` 세 개(동의하는 점·사각지대 목록 항목과 충돌 항목의 `point`/`sides`는 `_sent` 적용). 구역 제목은 기존 `<h3>` 텍스트 그대로.
  - `_cards(data)`: `<article class="advisor-card" id="advisor-<id>" data-advisor="<id>">`에 이름 `<h3>`, 관점 `<p class="role">`(blurb 줄마다 `<span>`), 구분선, `<div class="position-box">`, `<ol>`, 위험·놓치기 쉬운 점 `<div class="note">`. 기존 `class="advisor-card"` 개수 5 유지.
  - `_mini_cards(data)`: 하위 탭 역할. `<a class="advisor-mini" href="#advisor-<id>" data-advisor="<id>">`(내용: `role`만. blurb는 카드에 있다). 기존 5개·`href` 유지.
  - `_review_cards(data) -> str`: `<article class="review-card" id="review-<id>" data-reviewer="<id>">` 5개. 안에 검토자 이름 `<h3>`, 관점 blurb, `.strong`(가장 강한 응답: `A · 이름` + 사유), `.weak`(가장 큰 사각지대), `.missed`(모두가 놓친 것). 라벨 문구는 캔버스와 같이 "가장 강한 응답", "가장 큰 사각지대", "모두가 놓친 것". `_review_table`은 삭제하고 `_review_mini(data)`(`<a class="review-mini" href="#review-<id>" data-reviewer="<id>">역할 검토</a>` 5개)를 추가한다.
  - 슬롯: `REVIEW_TABLE` 제거, `REVIEW_CARDS`·`REVIEW_MINI` 추가.

- [ ] **Step 1: 테스트** — (a) `class="review-card"` 5개, `id="review-<id>"` 존재, 검토 카드 안에 `화가 스머프(확장가)` 이름 존재(기존 `test_review_table_shows_advisor_names_not_only_letters`를 `review-card` 기준으로 교체: `html.split('id="reviews"',1)[1]`에 이름 포함). (b) `_sent` 결과가 verdict에 쓰였는지: sample의 `agree[0]`가 한 문장이므로 `class="s1">세트 중심</span>`이 HTML에 있고 `class="rest"`는 그 항목에 없다. 두 문장 항목을 넣은 데이터에서는 `rest` 존재. (c) 이스케이프: 검토자 `name`에 `<script>…</script>{{REVIEW_CARDS}}`를 넣어도(validate 통과) `<script>alert` 없음, `review-card` 5개 유지. (d) `data-sub-panel` 세 개와 `data-sub` 버튼 세 개 존재. (e) 기존 `test_verdict_*` 두 개는 통과 유지.
- [ ] **Step 2:** `python -m unittest tests.test_render_report -v` → 새 테스트 FAIL.
- [ ] **Step 3:** 위 시그니처대로 구현한다. 템플릿 쪽 치환 자리는 Task 5에서 바꾸므로 이 Task에서는 `render()`의 슬롯 dict와 함수만 바꾸고, 임시로 `report.html`의 `{{REVIEW_TABLE}}`을 `{{REVIEW_CARDS}}`로, `{{MINI_CARDS}}` 옆에 `{{REVIEW_MINI}}`를 최소로 바꿔 테스트가 돌게 한다.
- [ ] **Step 4:** `python -m unittest discover tests` 전체 PASS(`test_sections_order`·`test_chair_card_comes_before_advisor_minis` 포함).
- [ ] **Step 5: Commit** — `feat: 보고서 마크업을 하위 탭·카드 구조로 변경`

### Task 4: 상성 지도 이동 링크와 푸터 안내 문구

**Files:**
- Modify: `kr-council-skill/scripts/render_report.py` (`_affinity_map`, 상수, 슬롯)
- Modify: `tests/test_render_report.py`

**Interfaces:**
- Produces: `_affinity_map`의 역할 라벨 `<text>`를 `<a class="affinity-link" href="#review-<id>" data-reviewer="<id>">`(SVG 네임스페이스 `<a>`)로 감싼다. 상수 `NOTICE_ABOUT`·`NOTICE_CAUTION`: `list[tuple[str, str, str]]` = (제목, 24px 아이콘 path `d`, 본문). `_notices(items) -> str`은 항목마다 `<div class="notice-item"><svg …><path d="…"/></svg><div><b>제목</b><span>본문</span></div></div>`. 슬롯 `NOTICE_ABOUT`, `NOTICE_CAUTION`.
- 문구(캔버스 그대로): ABOUT = 실행 방식(= `MODE_BANNERS[mode]`에서 `실행 방식:\s*` 접두어 제거), 한계 사항(`DISCLAIMER + " 위원은 같은 모델이 낸 의견이라 모델 편향을 공유합니다. 보고서의 제도·수치에 붙은 \"확인 필요\" 표시는 공식 자료로 확인하십시오."`), 출력 방식(`인쇄 아이콘을 누르면 위원장의 최종 검토 보고서만 A4 1장으로 출력합니다. 분량이 많으면 항목별 핵심만 싣습니다.`). CAUTION = 조언 아님(`이 보고서는 세무·법률·투자 조언이 아닙니다.`), 개인 정보(`비밀번호, API 키, 주민등록번호 같은 정보는 질문에 넣지 마십시오. 질문과 맥락은 하위 에이전트에게 전달됩니다.`), 저장 위치(`보고서는 작업 폴더의 council-reports/ 에 만들어집니다. 민감한 내용이 있으면 공유 전에 지우십시오.`). 아이콘 path 여섯 개는 `docs/superpowers/plans/assets/report-canvas-reference.dc.html`의 `noticeA`/`noticeB` 배열(376행 부근) `d` 값을 그대로 복사한다.

- [ ] **Step 1: 테스트** — (a) 지도 SVG 안에 `class="affinity-link"` 5개와 `href="#review-` 5개. (b) 역할 라벨 이스케이프 테스트(`test_affinity_map_escapes_labels`) 유지. (c) HTML에 `한계 사항`, `출력 방식`, `개인 정보`, `조언 아님`, `저장 위치` 문구 존재, `class="banner"`·`class="disclaimer"` 존재(기존 계약 `test_no_hidden_content_without_js`).
- [ ] **Step 2:** 실행 → FAIL. **Step 3:** 구현(banner/disclaimer 요소는 푸터 안에 두되 클래스명 유지). **Step 4:** 전체 PASS.
- [ ] **Step 5: Commit** — `feat: 상성 지도 이동 링크와 푸터 안내 문구 추가`

### Task 5: 템플릿 구조와 디자인 토큰 CSS (화면)

**Files:**
- Modify: `kr-council-skill/assets/report.html` (마크업 골격, `<style>`)
- Test: `tests/test_render_report.py`

**Interfaces:**
- Consumes: Task 3·4의 마크업·슬롯.
- Produces(JS·인쇄 CSS가 사용): 골격 `header.site-header` → `main`(`h1`+`.meta`, `section#question.hero-card`, `nav.tabs.js-only`(`button[data-tab]` 4개 report/advisors/affinity/reviews), `section#report.verdict.hero[data-panel]`, `section#advisors[data-panel]`(서브탭 `.subtabs.js-only`: `.advisor-mini` 5개 + `button[data-all]` "전체 보기", 카드 `{{ADVISOR_CARDS}}`), `section#affinity[data-panel]`, `section#reviews[data-panel]`(`.subtabs.js-only`: `.review-mini` 5개 + "전체 보기", 카드 `{{REVIEW_CARDS}}`)) → `footer#notice`(2열: "보고서 안내" `{{NOTICE_ABOUT}}`, "스킬 사용 시 주의 사항" `{{NOTICE_CAUTION}}`, 그리고 `.banner`·`.disclaimer`). 숨김 규칙은 `.js [data-panel]:not(.is-active)`, `.js .sub:not(.is-active)`, `.js .advisor-card:not(.is-active)`(전체 보기가 아닐 때만, `main[data-advisor-all]`이면 모두 표시), 검토 카드도 동일. JS 없으면 아무것도 숨기지 않는다.

- [ ] **Step 1: 테스트** — (a) 토큰 변수 존재: `--primary`, `--brand`, `--on-brand`, `--neg`, `--line` 선언과 값 `#246beb`·`#034694`·`#5b96ff`·`#4072b7`가 CSS에 있다. (b) 외부 리소스 0(`test_no_external_resources` 유지). (c) `font-weight` 값이 400·700 외 없다(`re.findall(r"font-weight:\s*(\d+)")` 집합 ⊆ {400,700}). (d) `box-shadow`가 CSS에 없다. (e) 구조 순서: `class="site-header"` < `id="question"` < `data-tab="report"` < `id="report"` < `id="advisors"` < `id="affinity"` < `id="reviews"` < `id="notice"`.
- [ ] **Step 2:** 실행 → FAIL. **Step 3:** 구현. 헤더는 브랜드 배경·밝은 글자, 날짜 `.meta`는 헤더 안(칩 없음), 다크 모드는 `role="switch"` 버튼(`#theme-toggle`, 기존 id 유지)+인쇄 아이콘 버튼(`#print-btn`, `aria-label="인쇄"`). 다크 값은 기존 `prefers-color-scheme`+`[data-theme]` 구조에 얹는다. 카드·상자 모양·CSS 값은 `docs/superpowers/plans/assets/report-canvas-reference.dc.html`의 `<style>`과 마크업을 따른다(판단 의견=연한 파랑+왼쪽 막대, 위험·놓친 점=테두리, 가장 강한 응답=파랑 막대, 가장 큰 사각지대=빨강 막대 `--neg`)를 따른다.
- [ ] **Step 4:** 전체 PASS. 브라우저 육안 확인은 Task 8에서 한다.
- [ ] **Step 5: Commit** — `feat: 보고서 화면에 디자인 시스템 토큰과 탭 구조 적용`

### Task 6: 정적 JS — 탭·하위 탭·지도 이동·테마

**Files:**
- Modify: `kr-council-skill/assets/report.html` (`<script>`)
- Test: `tests/test_render_report.py`

**Interfaces:**
- Consumes: Task 5의 `data-tab`, `data-panel`, `data-sub`, `data-sub-panel`, `.advisor-mini`, `.review-mini`, `.affinity-link`, `[data-all]`.
- Produces: 함수 `showTab(name)`, `showSub(name)`, `pickAdvisor(id|'all')`, `pickReviewer(id|'all')`. 규칙: 첫 화면은 report 탭·agree 하위 탭·첫 위원·첫 검토자. `.affinity-link`·`.review-mini` 클릭은 `preventDefault` 후 `showTab('reviews')`·`pickReviewer(id)`·`#reviews`로 스크롤(`prefers-reduced-motion`이면 `auto`). 탭 버튼 `aria-pressed`, 선택 하위 탭 `aria-current`. 모든 DOM 읽기는 `data-*`·id만(council 텍스트를 읽거나 쓰지 않음). 예외 시 기존 `catch`에서 `classList.remove('js')`.

- [ ] **Step 1: 테스트(정적 계약)** — 스크립트 문자열에 `showTab`, `showSub`, `pickAdvisor`, `pickReviewer`가 있고, 스크립트가 1개이며 council 텍스트가 없다(기존 두 테스트 유지), `catch (…) { … classList.remove('js') }` 정규식 유지.
- [ ] **Step 2:** 실행 → FAIL. **Step 3:** 구현(기존 `select`/`setView` 로직을 새 함수로 교체, 테마 저장·복원 코드는 그대로 둔다 — 잘못된 저장값은 무시하는 기존 동작 유지).
- [ ] **Step 4:** 전체 PASS.
- [ ] **Step 5: Commit** — `feat: 탭·하위 탭·상성 지도 이동 동작 추가`

### Task 7: 인쇄 — 위원장 보고서 A4 1장 자동 맞춤

**Files:**
- Modify: `kr-council-skill/assets/report.html` (`<style>` 인쇄 부분, `<script>`)
- Test: `tests/test_render_report.py`

**Interfaces:**
- Consumes: `.s1`/`.rest`(Task 2·3), `#report`, `.sub`, `#print-btn`.
- Produces: `fitPrint(): number`(1·2·3). `body.print-mode`가 붙으면 화면에서도 인쇄 배치(폭 794px, `#report`만 표시, 모든 `.sub` 표시, 안건·탭·헤더·푸터·다른 패널 숨김, 라이트 값, 구역 상자 테두리·제목 띠·왼쪽 막대, 위아래 중앙 정렬 `min-height:1120px`). `body[data-print-level="1|2|3"]`: 1=인쇄용 글자(본문 12.67px), 2=본문 12px·여백 8px, 3=2단계 + `.rest{display:none}` + 하단 안내 `.print-note` 표시(문구, 캔버스 사본의 `showNote` 블록과 동일: `※ 지면 관계로 항목별 핵심만 실었습니다. 인쇄에 포함되지 않은 자세한 내용은 원본 파일을 참고하십시오.`, 템플릿 상수). 측정 기준: `#report`의 `offsetHeight <= 1009`이면 해당 단계 채택. `beforeprint`에서 `print-mode` 추가→`fitPrint()`, `afterprint`에서 클래스·속성 제거. `#print-btn` 클릭은 `window.print()`만 호출. `@page { size: A4 portrait; margin: 0 }`, `print-color-adjust: exact`. JS가 실패했을 때의 `@media print`는 기존처럼 모든 내용을 펼쳐 인쇄한다.

- [ ] **Step 1: 테스트(정적 계약)** — CSS에 `@page`와 `size: A4`, `print-mode`, `data-print-level`이 있고 스크립트에 `beforeprint`·`afterprint`·`1009`가 있다. `.print-note` 문구가 HTML에 정확히 있다. `.rest`가 3단계에서만 숨겨진다는 규칙(`[data-print-level="3"] .rest`)이 있다.
- [ ] **Step 2:** 실행 → FAIL. **Step 3:** 구현.
- [ ] **Step 4:** 전체 PASS.
- [ ] **Step 5: Commit** — `feat: 위원장 보고서 A4 1장 자동 맞춤 인쇄 추가`

### Task 8: 실제 브라우저 검증과 릴리스 준비

**Files:**
- Modify: `CHANGELOG.md` (`[Unreleased]`)
- Create(커밋하지 않음): 저장소 밖 임시 폴더(예: `$TMPDIR/verify_report.py`, `$TMPDIR/out/`). `.gitignore`에 없는 경로를 저장소 안에 만들지 않는다

**Interfaces:**
- Consumes: 렌더 결과 HTML — `python kr-council-skill/scripts/render_report.py …` (인자 형식은 `--help`와 `tests/`의 호출 예로 확인). 입력 JSON: 실제 보고서 `council-20261112-0748.json`(있을 때)과 `sample()` 기반 보고서, 그리고 각각에서 위원 문장을 3배로 이어 붙여 만든 긴 보고서.

- [ ] **Step 1:** Playwright가 없으면 `pip install playwright --break-system-packages` 후 chromium 설치(실패하면 "렌더 검사 미실시"로 기록하고 중단). 검증 스크립트가 다음을 모두 확인하고 결과를 표로 낸다: 1280·768·360px × 라이트·다크 렌더에서 가로 넘침 없음·콘솔 오류 0, 탭·하위 탭·지도 클릭 이동 동작, JS 비활성에서 숨은 내용 0(위원 카드 5·검토 카드 5·하위 구역 3이 모두 보임), 외부 요청 0.
- [ ] **Step 2:** 인쇄 PDF(`page.pdf(format="A4", prefer_css_page_size=True)`와 `emulate_media("print")` + `beforeprint` 발생): 실제 보고서·긴 보고서 모두 쪽 수와 `data-print-level`을 기록한다. 기대: 실제 보고서 1쪽. 긴 보고서가 2쪽 이상이면 그 사실을 PR 본문 "알려진 한계"에 적고 내용 잘림이 없는지 확인한다. 흑백 변환(PDF→그레이스케일 이미지)에서 구역 경계가 보이는지 이미지를 직접 열어 확인한다.
- [ ] **Step 3:** CHANGELOG `[Unreleased]`에 `### 추가`(디자인 시스템·탭·하위 탭·A4 1장 인쇄·상성 지도 이동·푸터 안내)와 `### 변경`(위원 관점 문구, 검토 표 → 검토 카드, 위원 상세는 위원 5명 탭으로 이동, 인쇄는 위원장 보고서만)를 적는다. `SKILL.md`·버전은 건드리지 않는다.
- [ ] **Step 4:** `python -m unittest discover tests` 전체 PASS, `저장소의 패키징 스크립트(`CONTRIBUTING.md`·`docs/RELEASE-CHECKLIST.md`의 명령, 예: `python tools/package_skill.py`)`로 zip을 만들어 풀고 그 안의 `render_report.py`가 같은 JSON으로 동작하는지 확인.
- [ ] **Step 5: Commit & PR** — CHANGELOG 커밋 후 `git push -u origin feat/report-design-system`(필요하면 `-c push.negotiate=true`), `gh pr create`로 PR(본문: 변경 요약, 검증 표, 캔버스 링크, 알려진 한계: 다크 선택 탭 대비 약 2.9:1·Pretendard 미포함·상징 미포함·샘플 보고서의 영어 문장).

---

## Self-Review

- **설계 문서 §1–11 대응:** 토큰·헤더·푸터(Task 5), 탭·하위 탭(Task 3·5·6), 맡은 관점(Task 1), 검토 카드·지도 링크(Task 3·4), 푸터 안내(Task 4), 인쇄 3단계·Ctrl+P·중앙 정렬·안내 문구(Task 7), 첫 문장 span(Task 2), 검증·한계(Task 8). 누락 없음.
- **확정 결정 4가지:** ①Task 2·3·7, ②Task 7(`beforeprint`), ③Task 1, ④Task 3(검토 카드 blurb).
- **타입 일관성:** `_sent`, `split_first_sentence`, `_review_cards`, `_review_mini`, 슬롯 `REVIEW_CARDS`·`REVIEW_MINI`·`NOTICE_ABOUT`·`NOTICE_CAUTION`이 Task 3→5에서 같은 이름으로 쓰인다. `showTab`·`pickReviewer`는 Task 6에서만 정의되고 Task 7은 쓰지 않는다.
- **알려진 위험:** advisors.md 편집은 `화면 소개` 한 줄 추가로 한정해 위원 프롬프트("관점" 문장)를 바꾸지 않는다. README 원문의 `질문인지 부터` 띄어쓰기는 그대로 옮기며 별도 수정 대상이다.
