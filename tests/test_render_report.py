import copy
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "kr-council-skill" / "scripts" / "render_report.py"
TEMPLATE = (ROOT / "kr-council-skill" / "assets" / "report.html")
sys.path.insert(0, str(ROOT / "kr-council-skill" / "scripts"))

from render_report import (  # noqa: E402
    ADVISOR_IDS, ADVISOR_NAMES, ADVISOR_PROFILE, CHAIR_NAME, _affinity_edges, _sent, make_mapping, render, split_first_sentence,
    validate)

DISCLAIMER = "같은 모델이 서로 다른 관점으로 낸 의견이며, 독립된 전문가 5인이 아닙니다."

NAMES = {
    "contrarian": "투덜이 스머프(반대자)",
    "first_principles": "똘똘이 스머프(본질 탐구자)",
    "expansionist": "화가 스머프(확장가)",
    "outsider": "덜렁이 스머프(아웃사이더)",
    "executor": "재주꾼 스머프(실행가)",
}
MAPPING = {"A": "contrarian", "B": "first_principles", "C": "expansionist",
           "D": "outsider", "E": "executor"}


def sample():
    """정상 council.json 한 벌. 테스트가 이 값을 복사해 일부만 망가뜨린다."""
    letter_of = {v: k for k, v in MAPPING.items()}
    ids = list(ADVISOR_IDS)
    advisors = [
        {"id": i, "name": NAMES[i], "position": f"{NAMES[i]}의 입장",
         "reasons": ["근거1", "근거2", "근거3"], "risk": "위험", "blindspot": "놓친 점"}
        for i in ids
    ]
    reviews = []
    for n, rid in enumerate(ids):
        reviews.append({
            "reviewer": rid,
            "strongest": letter_of[ids[(n + 1) % 5]], "strongest_why": "근거가 구체적",
            "weakest": letter_of[ids[(n + 2) % 5]], "weakest_why": "맥락 부족",
            "missed": "모두가 놓친 점",
        })
    return {
        "title": "수제 쿠키 가격 결정", "question": "낱개와 세트 중 무엇에 집중할까?",
        "mode": "parallel", "created": "2026-11-10 20:00",
        "advisors": advisors, "mapping": dict(MAPPING), "reviews": reviews,
        "verdict": {
            "agree": ["세트 중심"], "clash": [{"point": "광고", "sides": "찬성 대 반대"}],
            "blindspots": ["배송비"], "recommendation": "세트에 집중한다",
            "first_action": "택배비 포함 원가표를 만든다",
            "confidence": "보통", "minority_kept": True,
        },
    }


class MappingTests(unittest.TestCase):
    def test_make_mapping_is_bijection(self):
        for _ in range(20):
            m = make_mapping()
            self.assertEqual(set(m), set("ABCDE"))
            self.assertEqual(set(m.values()), set(ADVISOR_IDS))

    def test_make_mapping_seed_reproducible(self):
        self.assertEqual(make_mapping(1), make_mapping(1))


class ValidateTests(unittest.TestCase):
    def test_validate_ok(self):
        self.assertEqual(validate(sample()), [])

    def test_validate_fewer_than_five_advisors(self):
        d = sample()
        d["advisors"].pop()
        self.assertTrue(any("위원" in e for e in validate(d)))

    def test_validate_missing_field(self):
        d = sample()
        del d["advisors"][2]["risk"]
        errors = validate(d)
        self.assertTrue(errors)
        self.assertTrue(any("risk" in e for e in errors))

    def test_validate_review_unknown_letter(self):
        d = sample()
        d["reviews"][0]["strongest"] = "F"
        self.assertTrue(validate(d))

    def test_validate_review_picks_own_response(self):
        d = sample()
        own = next(k for k, v in d["mapping"].items() if v == d["reviews"][0]["reviewer"])
        d["reviews"][0]["strongest"] = own
        self.assertTrue(any("자기" in e for e in validate(d)))

    def test_validate_bad_confidence(self):
        d = sample()
        d["verdict"]["confidence"] = "아주높음"
        self.assertTrue(validate(d))

    def test_validate_bad_mode(self):
        d = sample()
        d["mode"] = "x"
        self.assertTrue(validate(d))

    def test_validate_mixed_type_mapping_is_an_error_not_a_crash(self):
        d = sample()
        d["mapping"] = {"A": 1, "B": "x", "C": {"k": 1}, "D": "z", "E": "w"}
        self.assertTrue(any("mapping" in e for e in validate(d)))

    def test_validate_agree_items_must_be_text(self):
        d = sample()
        d["verdict"]["agree"] = ["정상", None, 123]
        self.assertTrue(any("agree" in e for e in validate(d)))

    def test_validate_agree_must_not_be_empty(self):
        d = sample()
        d["verdict"]["agree"] = []
        self.assertTrue(any("agree" in e for e in validate(d)))

    def test_validate_blindspots_items_must_be_text(self):
        d = sample()
        d["verdict"]["blindspots"] = [{"x": "<b>"}]
        self.assertTrue(any("blindspots" in e for e in validate(d)))

    def test_validate_minority_kept_requires_a_clash(self):
        d = sample()
        d["verdict"]["clash"] = []
        d["verdict"]["minority_kept"] = True
        self.assertTrue(any("minority_kept" in e for e in validate(d)))

    def test_validate_strongest_and_weakest_must_differ(self):
        d = sample()
        d["reviews"][0]["weakest"] = d["reviews"][0]["strongest"]
        self.assertTrue(any("같은" in e for e in validate(d)))

    def test_validate_duplicate_advisor_names(self):
        d = sample()
        d["advisors"][1]["name"] = d["advisors"][0]["name"]
        self.assertTrue(any("이름" in e for e in validate(d)))

    def test_validate_clash_error_mentions_string_sides(self):
        d = sample()
        d["verdict"]["clash"] = [{"point": "광고", "sides": ["a", "b"]}]
        self.assertTrue(any("문자열" in e for e in validate(d)))

    def test_validate_collects_all_errors(self):
        d = copy.deepcopy(sample())
        d["mode"] = "x"
        d["verdict"]["confidence"] = "?"
        self.assertGreaterEqual(len(validate(d)), 2)


def template():
    return TEMPLATE.read_text(encoding="utf-8")


class RenderTests(unittest.TestCase):
    def test_render_contains_five_cards_and_korean(self):
        html = render(sample(), template())
        self.assertEqual(html.count('class="advisor-card"'), 5)
        self.assertIn("투덜이 스머프(반대자)", html)
        self.assertIn("파파스머프", html)
        self.assertIn(DISCLAIMER, html)
        self.assertIn('<meta charset="utf-8">', html)

    def test_render_escapes_html(self):
        d = sample()
        d["question"] = "<script>alert(1)</script> & \"따옴표\""
        html = render(d, template())
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_render_invalid_raises(self):
        d = sample()
        d["advisors"].pop()
        with self.assertRaises(ValueError):
            render(d, template())

    def test_mode_banner_single_session(self):
        d = sample()
        d["mode"] = "single-session"
        self.assertIn("독립성이 낮습니다", render(d, template()))
        self.assertNotIn("독립성이 낮습니다", render(sample(), template()))

    def test_verdict_shows_minority_and_confidence(self):
        d = sample()
        d["verdict"]["minority_kept"] = True
        d["verdict"]["confidence"] = "낮음"
        html = render(d, template())
        self.assertIn("소수 의견 유지됨", html)
        self.assertIn("신뢰도", html)
        self.assertIn("낮음", html)

    def test_verdict_without_minority_says_none_not_ignored(self):
        d = sample()
        d["verdict"]["minority_kept"] = False
        html = render(d, template())
        self.assertIn("소수 의견 없음", html)
        self.assertNotIn("반영 안 됨", html)

    def test_review_cards_show_advisor_names_not_only_letters(self):
        html = render(sample(), template())
        self.assertEqual(html.count('class="review-card"'), 5)
        self.assertIn("화가 스머프(확장가)", html.split('id="reviews"', 1)[1])
        for advisor_id in ADVISOR_IDS:
            self.assertIn(f'id="review-{advisor_id}"', html)

    def test_verdict_uses_first_sentence_spans(self):
        html = render(sample(), template())
        self.assertIn('class="s1">세트 중심</span>', html)
        d = sample()
        d["verdict"]["agree"] = ["첫째 문장이다. 둘째 문장이다."]
        html = render(d, template())
        self.assertIn('<span class="s1">첫째 문장이다.</span><span class="rest"> 둘째 문장이다.</span>', html)

    def test_review_slots_escape_and_do_not_resubstitute(self):
        d = sample()
        d["advisors"][0]["name"] = "<script>alert(1)</script>{{REVIEW_CARDS}}"
        self.assertEqual(validate(d), [])
        html = render(d, template())
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertEqual(html.count('class="review-card"'), 5)

    def test_sub_tabs_and_panels_present(self):
        html = render(sample(), template())
        for name in ("agree", "blind", "clash"):
            self.assertEqual(html.count(f'data-sub="{name}"'), 1)
            self.assertEqual(html.count(f'data-sub-panel="{name}"'), 1)


class DashboardStructureTests(unittest.TestCase):
    def test_mini_cards_one_per_advisor_with_blurb(self):
        html = render(sample(), template())
        self.assertEqual(html.count('class="advisor-mini"'), 5)
        self.assertEqual(html.count('class="advisor-card"'), 5)
        for advisor_id, profile in ADVISOR_PROFILE.items():
            self.assertIn(f'href="#advisor-{advisor_id}"', html)
            for line in profile["blurb"].split(chr(10)):
                self.assertIn(line, html)

    def test_detail_panels_have_anchor_ids(self):
        html = render(sample(), template())
        for advisor_id in ADVISOR_IDS:
            self.assertIn(f'id="advisor-{advisor_id}"', html)

    def test_mini_cards_escape_advisor_name(self):
        d = sample()
        d["advisors"][0]["name"] = "<script>alert(1)</script>{{ADVISOR_CARDS}}"
        self.assertEqual(validate(d), [])
        html = render(d, template())
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertEqual(html.count('class="advisor-card"'), 5)
        self.assertEqual(html.count('class="advisor-mini"'), 5)

    def test_sections_order(self):
        html = render(sample(), template())
        positions = [html.index(f'id="{name}"') for name in ("question", "report", "advisors", "affinity", "reviews")]
        self.assertEqual(positions, sorted(positions))


class DashboardBehaviorContractTests(unittest.TestCase):
    """JS 없이도 읽히고, 스크립트에 위원 텍스트가 들어가지 않으며, 외부 리소스가 없다는 계약."""

    @staticmethod
    def script_blocks(text):
        return re.findall(r"<script>.*?</script>", text, flags=re.S)

    def test_single_static_script_without_council_text(self):
        html = render(sample(), template())
        self.assertEqual(html.count("<script"), 1)
        self.assertEqual(self.script_blocks(html), self.script_blocks(template()))
        d = sample()
        d["question"] = "</script><script>alert(1)</script>"
        html = render(d, template())
        self.assertEqual(html.count("<script"), 1)
        self.assertEqual(self.script_blocks(html), self.script_blocks(template()))

    def test_script_falls_back_to_no_js_layout_when_init_fails(self):
        """init이 예외를 내면 `js` 클래스를 떼어, CSS로 숨겨 둔 위원 상세가 다시 보이게 한다."""
        script = self.script_blocks(render(sample(), template()))[0]
        self.assertRegex(script, r"catch\s*\([^)]*\)\s*\{[^}]*classList\.remove\('js'\)")

    def test_no_external_resources(self):
        html = render(sample(), template())
        self.assertIsNone(re.search(r'(src|href)="https?:|@import|url\(\s*[\'"]?https?:', html))

    def test_no_hidden_content_without_js(self):
        html = render(sample(), template())
        self.assertIsNone(re.search(r"<[^>]+\shidden[\s>]", html))
        self.assertNotIn('style="display:none', html)
        self.assertIn('class="banner"', html)
        self.assertIn('class="disclaimer"', html)

    def test_theme_and_print_css_present(self):
        html = render(sample(), template())
        for needle in ("prefers-color-scheme: dark", 'data-theme="dark"', 'data-theme="light"',
                       "prefers-reduced-motion", "@media print"):
            self.assertIn(needle, html)

    def test_chair_card_comes_before_advisor_minis(self):
        html = render(sample(), template())
        self.assertLess(html.index('class="verdict hero"'), html.index('id="advisors"'))


LETTER_OF = {v: k for k, v in MAPPING.items()}


def svg_of(html):
    start = html.index('<svg viewBox="0 0 600')  # 헤더의 인쇄 아이콘 svg는 건너뛴다
    return html[start:html.index("</svg>", start) + len("</svg>")]


class AffinityTests(unittest.TestCase):
    def test_affinity_edges_has_ten_with_kinds(self):
        edges = _affinity_edges(sample())
        self.assertEqual(len(edges), 10)
        self.assertEqual(sum(e["kind"] == "support" for e in edges), 5)
        self.assertEqual(sum(e["kind"] == "critique" for e in edges), 5)
        self.assertFalse(any(e["mutual"] for e in edges))

    def test_affinity_edges_marks_mutual_support(self):
        d = sample()
        d["reviews"][1]["strongest"] = LETTER_OF["contrarian"]  # 똘똘이 → 투덜이 (투덜이 → 똘똘이는 기존)
        self.assertEqual(validate(d), [])
        mutual = [(e["from"], e["to"]) for e in _affinity_edges(d) if e["mutual"]]
        self.assertEqual(sorted(mutual), [("contrarian", "first_principles"), ("first_principles", "contrarian")])

    def test_affinity_map_renders_ten_edges_and_legend(self):
        html = render(sample(), template())
        self.assertEqual(html.count('class="edge '), 10)
        critiques = re.findall(r'<[^>]*class="edge critique[^>]*>', html)
        self.assertEqual(len(critiques), 5)
        self.assertTrue(all("stroke-dasharray" in c for c in critiques))
        self.assertIn("점수가 아니라", html)

    def test_opposite_edges_curve_to_opposite_sides(self):
        """서로 반대 방향인 두 간선(상호 지지 쌍)이 같은 곡선으로 겹쳐 하나로 보이면 안 된다."""
        d = sample()
        d["reviews"][1]["strongest"] = LETTER_OF["contrarian"]  # 투덜이 ↔ 똘똘이 상호 지지
        svg = svg_of(render(d, template()))
        pattern = (r'data-from="(\w+)" data-to="(\w+)"[^>]*d="M([-\d.]+) ([-\d.]+) '
                   r'Q([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+)"')
        paths = {(m[0], m[1]): tuple(map(float, m[2:])) for m in re.findall(pattern, svg)}
        a_to_b = paths[("contrarian", "first_principles")]
        b_to_a = paths[("first_principles", "contrarian")]
        (ax, ay), (bx, by) = a_to_b[0:2], b_to_a[0:2]  # 각 간선의 시작점 근처(노드 중심 근사)

        def side(control):  # 직선 A→B에 대해 제어점이 놓인 쪽(+1/-1)
            cross = (bx - ax) * (control[1] - ay) - (by - ay) * (control[0] - ax)
            return 1 if cross > 0 else -1

        self.assertNotEqual(side(a_to_b[2:4]), side(b_to_a[2:4]))

    def test_arrowheads_do_not_scale_with_stroke_width(self):
        self.assertIn('markerUnits="userSpaceOnUse"', svg_of(render(sample(), template())))

    def test_affinity_map_escapes_labels(self):
        d = sample()
        d["advisors"][0]["name"] = "<b>x</b>"
        svg = svg_of(render(d, template()))
        self.assertNotIn("<b>x</b>", svg)
        self.assertIn("&lt;b&gt;x&lt;/b&gt;", svg)

    def test_affinity_map_survives_self_critique(self):
        d = sample()
        d["reviews"][0]["weakest"] = LETTER_OF["contrarian"]  # 검토자 본인(투덜이)을 약점으로
        self.assertEqual(validate(d), [])
        html = render(d, template())
        self.assertIn('class="edge critique self"', html)
        self.assertEqual(html.count('class="edge '), 10)

    def test_affinity_map_hub_target_keeps_all_edges(self):
        d = sample()
        for rv in d["reviews"]:
            rv["strongest"] = LETTER_OF["first_principles"] if rv["reviewer"] != "first_principles" \
                else LETTER_OF["contrarian"]
            rv["weakest"] = LETTER_OF["executor"] if rv["strongest"] != LETTER_OF["executor"] \
                else LETTER_OF["outsider"]
        self.assertEqual(validate(d), [])
        html = render(d, template())
        self.assertEqual(html.count('class="edge '), 10)
        self.assertEqual(len(_affinity_edges(d)), 10)


class RecommendationBriefTests(unittest.TestCase):
    def test_recommendation_rest_keeps_its_first_sentence_in_brief_mode(self):
        d = sample()
        d["verdict"]["recommendation"] = "세트에 집중한다. 이유는 원가다. 다만 광고는 보류한다."
        html = render(d, template())
        self.assertIn('<p class="rec-rest"><span class="s1">이유는 원가다.</span><span class="rest"> 다만 광고는 보류한다.</span></p>', html)
        css = re.search(r"<style>(.*?)</style>", template(), flags=re.S).group(1)
        self.assertNotIn(".rec-rest { display: none; }", css)
        self.assertNotRegex(css, r'data-print-level="3"\][^{]*\.rec-rest')


class NoticeAndLinkTests(unittest.TestCase):
    def test_affinity_nodes_link_to_review_cards(self):
        svg = svg_of(render(sample(), template()))
        self.assertEqual(svg.count('class="affinity-link"'), 5)
        self.assertEqual(svg.count('href="#review-'), 5)

    def test_footer_notices_present(self):
        html = render(sample(), template())
        for needle in ("보고서 안내", "스킬 사용 시 주의 사항", "실행 방식", "한계 사항", "출력 방식",
                       "조언 아님", "개인 정보", "저장 위치", "인쇄 아이콘을 누르면 위원장의 최종 검토 보고서만"):
            self.assertIn(needle, html)
        self.assertIn(DISCLAIMER, html)
        self.assertIn("병렬 — 위원 5명을", html)
        self.assertNotIn("실행 방식: 병렬", html)
        self.assertEqual(html.count('<path d="M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM10 8.5l5 3.5-5 3.5z"/>'), 1)


class ProfileTests(unittest.TestCase):
    def test_advisor_names_derived_from_profile(self):
        self.assertEqual(set(ADVISOR_PROFILE), set(ADVISOR_IDS))
        self.assertEqual(ADVISOR_NAMES, NAMES)

    def test_blurbs_are_sentences_from_advisors_md(self):
        advisors_md = (ROOT / "kr-council-skill" / "references" / "advisors.md").read_text(encoding="utf-8")
        for advisor_id, profile in ADVISOR_PROFILE.items():
            for line in profile["blurb"].split(chr(10)):
                self.assertIn(line, advisors_md, advisor_id)

    def test_blurbs_match_readme_intro(self):
        expected = {
            "contrarian": ["뭐든 싫다며 문제부터 짚는다", "선택이 실패할 때를 대비한 가장 그럴듯한 이유를 찾는다"],
            "first_principles": ["진짜 목적이 뭔지, 선택지가 맞는 질문인지 부터 묻는다"],
            "expansionist": ["큰 그림과 가능성을 그린다", "잘 풀렸을 때의 상승 여력과 인접 기회를 본다"],
            "outsider": ["배경지식 없는 사람의 순진한 시각으로 당연한 것을 묻는다"],
            "executor": ["일단 만들어 본다", "가장 작은 검증 단계를 본다"],
        }
        for advisor_id, lines in expected.items():
            self.assertEqual(ADVISOR_PROFILE[advisor_id]["blurb"].split(chr(10)), lines)

    def test_chair_name_comes_from_constant(self):
        self.assertIn(CHAIR_NAME, render(sample(), template()))
        self.assertNotIn("파파스머프", template())


class SentenceSplitTests(unittest.TestCase):
    def test_split_keeps_original_text(self):
        cases = {
            "A는 B다. C도 D다.": ("A는 B다.", " C도 D다."),
            "끝 표시 없음": ("끝 표시 없음", ""),
        }
        for text, expected in cases.items():
            self.assertEqual(split_first_sentence(text), expected)
        for text in ("가격은 2.7만 원이다. 다음 문장.", "(1) 청구액이 3만 원 이상이다. (2) 정지가 발생했다.", ""):
            first, rest = split_first_sentence(text)
            self.assertEqual(first + rest, text)
        self.assertEqual(split_first_sentence("가격은 2.7만 원이다. 다음 문장.")[0], "가격은 2.7만 원이다.")
        self.assertEqual(split_first_sentence("(1) 청구액이 3만 원 이상이다. (2) 정지가 발생했다.")[0],
                         "(1) 청구액이 3만 원 이상이다.")

    def test_sent_escapes_and_omits_empty_rest(self):
        out = _sent("<b>x</b>. y")
        self.assertIn("&lt;b&gt;", out)
        self.assertNotIn("<b>", out)
        self.assertIn('class="rest"', out)
        self.assertNotIn('class="rest"', _sent("한 문장"))


class DesignSystemTemplateTests(unittest.TestCase):
    def css(self):
        return re.search(r"<style>(.*?)</style>", template(), flags=re.S).group(1)

    def script(self):
        return DashboardBehaviorContractTests.script_blocks(template())[0]

    def test_design_tokens_present(self):
        css = self.css()
        for name in ("--primary", "--brand", "--on-brand", "--neg", "--line"):
            self.assertRegex(css, re.escape(name) + r"\s*:")
        for value in ("#246beb", "#034694", "#5b96ff", "#4072b7"):
            self.assertIn(value, css)

    def test_only_regular_and_bold_weights_and_no_shadow(self):
        css = self.css()
        self.assertLessEqual(set(re.findall(r"font-weight:\s*(\d+)", css)), {"400", "700"})
        self.assertNotIn("box-shadow", css)

    def test_structure_order(self):
        html = render(sample(), template())
        marks = ['class="site-header"', 'id="question"', 'data-tab="report"', 'id="report"', 'id="advisors"',
                 'id="affinity"', 'id="reviews"', 'id="notice"']
        positions = [html.index(m) for m in marks]
        self.assertEqual(positions, sorted(positions))
        for tab in ("report", "advisors", "affinity", "reviews"):
            self.assertEqual(html.count(f'data-tab="{tab}"'), 1)
        self.assertEqual(html.count('class="js-only" data-all'), 2)  # 위원·검토자 "전체 보기" 버튼

    def test_inactive_panels_hide_even_against_id_selectors(self):
        """#advisors { display: flex } 같은 ID 규칙이 탭 숨김을 이기면 모든 패널이 한 화면에 보인다."""
        self.assertRegex(self.css(), r"\.js \[data-panel\]:not\(\.is-active\)\s*\{\s*display:\s*none\s*!important")

    def test_script_defines_tab_functions(self):
        script = self.script()
        for name in ("showTab", "showSub", "pickAdvisor", "pickReviewer"):
            self.assertIn(name, script)

    def test_print_a4_one_page_contract(self):
        css, script, html = self.css(), self.script(), render(sample(), template())
        self.assertIn("@page", css)
        self.assertRegex(css, r"size:\s*A4")
        self.assertIn("print-mode", css)
        self.assertIn("data-print-level", css)
        self.assertIn('[data-print-level="3"] .rest', css)
        for needle in ("beforeprint", "afterprint", "1009"):
            self.assertIn(needle, script)
        self.assertIn("※ 지면 관계로 항목별 핵심만 실었습니다. 인쇄에 포함되지 않은 자세한 내용은 원본 파일을 참고하십시오.", html)


class CliTests(unittest.TestCase):
    def _run(self, args, cwd=None, env=None):
        return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=cwd, env=env,
                              capture_output=True, text=True, encoding="utf-8", errors="replace")

    def _write_json(self, tmp, data):
        path = Path(tmp) / "council.json"
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return path

    def test_cli_cp949_env(self):
        d = sample()
        d["question"] += " 😀"
        env = dict(os.environ, PYTHONUTF8="0", PYTHONIOENCODING="cp949")
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "r.html"
            r = self._run(["render", str(self._write_json(tmp, d)), "--out", str(out)], env=env)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("투덜이 스머프(반대자)", out.read_text(encoding="utf-8"))

    def test_cli_invalid_exit_code_2(self):
        d = sample()
        d["advisors"].pop()
        with tempfile.TemporaryDirectory() as tmp:
            r = self._run(["render", str(self._write_json(tmp, d)), "--out", str(Path(tmp) / "r.html")])
            self.assertEqual(r.returncode, 2)
            self.assertTrue(r.stderr.strip())

    def test_cli_runs_from_other_cwd(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as elsewhere:
            out = Path(tmp) / "r.html"
            r = self._run(["render", str(self._write_json(tmp, sample())), "--out", str(out)], cwd=elsewhere)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(out.exists())

    def test_cli_shuffle_prints_valid_mapping(self):
        r = self._run(["shuffle", "--seed", "3"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), make_mapping(3))

    def test_cli_creates_missing_output_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "council-reports" / "r.html"
            r = self._run(["render", str(self._write_json(tmp, sample())), "--out", str(out)])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(out.exists())

    def test_cli_lone_surrogate_exit_2_and_no_empty_file(self):
        d = sample()
        d["title"] = "제목 " + chr(0xD83D)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "r.html"
            path = Path(tmp) / "council.json"
            path.write_text(json.dumps(d), encoding="utf-8")
            r = self._run(["render", str(path), "--out", str(out)])
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertFalse(out.exists())

    def test_cli_output_path_is_a_folder_exit_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = self._run(["render", str(self._write_json(tmp, sample())), "--out", tmp])
            self.assertEqual(r.returncode, 2, r.stderr)


def facts_sample(**over):
    """정상 facts 한 벌(checked, 항목 3개). 테스트가 복사해 일부만 망가뜨린다."""
    facts = {
        "status": "checked", "checked_at": "2026-11-17", "reason": "시행 중인 법령의 현재 기준 확인이 필요함",
        "queries": ["일반화한 검색어 1", "일반화한 검색어 2"],
        "items": [
            {"claim": "확인된 사실 1", "source": "https://example.org/a", "source_label": "해당 부처 공지",
             "confirmed": True, "note": "변동 큼"},
            {"claim": "도구로 조회한 사실", "source_label": "국가법령정보센터 조회(도구)", "confirmed": True},
            {"claim": "확인하지 못한 사항", "source_label": "비공식 출처만 확인", "confirmed": False},
        ],
    }
    facts.update(over)
    return facts


def facts_errors(facts):
    import render_report as rr
    errors = []
    rr._check_facts(facts, errors)
    return errors


class FactsValidateTests(unittest.TestCase):
    def test_sample_is_valid_alone_and_inside_validate(self):
        self.assertEqual(facts_errors(facts_sample()), [])
        d = sample()
        d["facts"] = facts_sample()
        self.assertEqual(validate(d), [])

    def test_validate_without_facts_is_unchanged(self):
        self.assertEqual(validate(sample()), [])

    def test_validate_confirmed_requires_source_or_label(self):
        f = facts_sample()
        f["items"][1] = {"claim": "근거 없음", "confirmed": True}
        self.assertTrue(any("항목 2번" in e for e in facts_errors(f)))

    def test_validate_rejects_non_http_scheme(self):
        for bad in ("javascript:alert(1)", "JAVASCRIPT:alert(1)", "ftp://x.org", "data:text/html,x"):
            f = facts_sample()
            f["items"][0]["source"] = bad
            self.assertTrue(any("항목 1번" in e for e in facts_errors(f)), bad)
        for ok in ("HTTP://example.org", "https://example.org/x"):
            f = facts_sample()
            f["items"][0]["source"] = ok
            self.assertEqual(facts_errors(f), [], ok)

    def test_validate_source_must_be_string(self):
        f = facts_sample()
        f["items"][0]["source"] = 7
        self.assertTrue(any("항목 1번" in e for e in facts_errors(f)))

    def test_validate_unconfirmed_must_not_have_source(self):
        f = facts_sample()
        f["items"][2]["source"] = "https://example.org/b"
        self.assertTrue(any("항목 3번" in e for e in facts_errors(f)))
        f["items"][2]["source"] = ""
        self.assertEqual(facts_errors(f), [])  # 빈 문자열과 source_label은 허용

    def test_validate_checked_item_count(self):
        self.assertTrue(facts_errors(facts_sample(items=[])))
        item = {"claim": "사실", "source_label": "공지", "confirmed": True}
        self.assertTrue(facts_errors(facts_sample(items=[dict(item) for _ in range(11)])))
        self.assertEqual(facts_errors(facts_sample(items=[dict(item) for _ in range(10)])), [])

    def test_validate_non_checked_status_has_no_items(self):
        for status in ("skipped", "unavailable"):
            self.assertEqual(facts_errors({"status": status, "checked_at": "2026-11-17", "reason": "사유"}), [])
            self.assertTrue(facts_errors(facts_sample(status=status)))

    def test_validate_status_values(self):
        self.assertTrue(facts_errors(facts_sample(status="done")))

    def test_validate_facts_wrong_type(self):
        for bad in ([], "", 0, {}, None, "x"):
            d = sample()
            d["facts"] = bad
            self.assertTrue(validate(d), repr(bad))  # 검증을 건너뛰지 않고 크래시도 없다
            self.assertTrue(facts_errors(bad), repr(bad))

    def test_validate_checked_at_format(self):
        for bad in ("2026-02-30", "20261117", "2026-1-5", "", None, 20261117, "2026-11-17 09:00"):
            self.assertTrue(facts_errors(facts_sample(checked_at=bad)), repr(bad))
        self.assertEqual(facts_errors(facts_sample(checked_at="2028-02-29")), [])

    def test_validate_reason_and_claim_must_be_text(self):
        self.assertTrue(facts_errors(facts_sample(reason=" ")))
        f = facts_sample()
        f["items"][0]["claim"] = ""
        self.assertTrue(any("항목 1번" in e for e in facts_errors(f)))
        f = facts_sample()
        f["items"][0]["confirmed"] = "true"
        self.assertTrue(any("항목 1번" in e for e in facts_errors(f)))
        f = facts_sample()
        f["items"][0]["source_label"] = ""
        self.assertTrue(facts_errors(f))
        f = facts_sample()
        f["items"][0] = "문자열 항목"
        self.assertTrue(any("항목 1번" in e for e in facts_errors(f)))

    def test_validate_queries(self):
        self.assertEqual(facts_errors(facts_sample(queries=[f"검색어 {n}" for n in range(8)])), [])
        self.assertTrue(facts_errors(facts_sample(queries=[f"검색어 {n}" for n in range(9)])))
        self.assertTrue(facts_errors(facts_sample(queries="검색어")))
        self.assertTrue(facts_errors(facts_sample(queries=[1])))

    def test_validate_rejects_untrusted_markers(self):
        for field in ("claim", "note", "source_label"):
            for marker in ("<BEGIN_UNTRUSTED>", "<end_untrusted>", "<End_Untrusted>"):
                f = facts_sample()
                f["items"][0][field] = f"앞 {marker} 뒤"
                self.assertTrue(any("UNTRUSTED" in e for e in facts_errors(f)), (field, marker))
        self.assertTrue(facts_errors(facts_sample(reason="<END_UNTRUSTED>")))

    def test_validate_collects_all_errors(self):
        f = facts_sample(status="done", checked_at="x")
        f["items"][0]["claim"] = ""
        self.assertGreaterEqual(len(facts_errors(f)), 3)

    def test_validate_does_not_use_language_check(self):
        f = facts_sample()
        f["items"][0]["claim"] = "This claim is written in plain English only, long enough to trip the language check."
        self.assertEqual(facts_errors(f), [])


def facts_html(facts=None):
    d = sample()
    if facts is not None:
        d["facts"] = facts
    return render(d, template())


class FactsRenderTests(unittest.TestCase):
    def test_no_facts_renders_no_facts_block(self):
        html = facts_html()
        self.assertNotIn('class="facts', html.split("<style>", 1)[1].split("</style>", 1)[1])
        self.assertNotIn("{{", html)

    def test_empty_slot_leaves_body_unchanged(self):
        self.assertEqual(facts_html(), render(sample(), template().replace("{{FACTS}}", "")))
        self.assertIn("{{FACTS}}", template())

    def test_checked_renders_details_and_links(self):
        html = facts_html(facts_sample())
        self.assertIn('<details class="facts">', html)
        self.assertNotRegex(html, r"<details[^>]*\sopen")
        self.assertIn("사실 확인", html)
        self.assertIn("2026-11-17", html)
        self.assertEqual(html.count('href="https://example.org/a"'), 1)
        self.assertEqual(html.count('rel="noopener noreferrer"'), 1)
        self.assertEqual(html.count('target="_blank"'), 1)
        body = html.split('<details class="facts">', 1)[1].split("</details>", 1)[0]
        self.assertEqual(body.count("<a "), 1)  # 라벨 전용·미확인 항목에는 링크가 없다
        self.assertIn("미확인", body)

    def test_source_label_only_confirmed(self):
        f = facts_sample(items=[{"claim": "도구로 조회", "source_label": "국가법령정보센터 조회(도구)", "confirmed": True}])
        html = facts_html(f)
        body = html.split('<details class="facts">', 1)[1].split("</details>", 1)[0]
        self.assertNotIn("<a ", body)
        self.assertIn("국가법령정보센터 조회(도구)", body)
        self.assertNotIn("미확인", body)

    def test_unconfirmed_label_is_shown(self):
        body = facts_html(facts_sample()).split('<details class="facts">', 1)[1]
        self.assertIn("비공식 출처만 확인", body)

    def test_skipped_renders_nothing(self):
        f = {"status": "skipped", "checked_at": "2026-11-17", "reason": "관점이 갈리는 결정이라 건너뜀"}
        self.assertEqual(facts_html(f), facts_html())
        self.assertNotIn("관점이 갈리는 결정이라 건너뜀", facts_html(f))

    def test_unavailable_shows_notice(self):
        f = {"status": "unavailable", "checked_at": "2026-11-17", "reason": "검색 도구 없음"}
        html = facts_html(f)
        self.assertIn("최신 정보를 확인하지 못했습니다", html)
        self.assertNotIn("<details", html.split("</style>", 1)[1].split("<main>", 1)[1].split('id="report"', 1)[0])

    def test_facts_escapes_and_does_not_resubstitute(self):
        f = facts_sample()
        f["items"][0]["claim"] = "<script>alert(1)</script> {{TITLE}}"
        f["items"][0]["note"] = '"><img src=x onerror=1>'
        f["items"][1]["source_label"] = "{{QUESTION}} & <b>굵게</b>"
        html = facts_html(f)
        self.assertEqual(html.count("<script"), 1)  # 템플릿의 정적 스크립트 하나뿐
        self.assertNotIn("<img src=x", html)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt; {{TITLE}}", html)
        self.assertIn("{{QUESTION}} &amp; &lt;b&gt;굵게&lt;/b&gt;", html)

    def test_url_is_escaped_in_href(self):
        f = facts_sample()
        f["items"][0]["source"] = 'https://example.org/a?x=1&y="2"'
        html = facts_html(f)
        self.assertIn('href="https://example.org/a?x=1&amp;y=&quot;2&quot;"', html)

    def test_items_numbered_in_input_order(self):
        body = facts_html(facts_sample()).split('<details class="facts">', 1)[1]
        self.assertLess(body.index("F1"), body.index("F2"))
        self.assertLess(body.index("F2"), body.index("F3"))
        self.assertNotIn("F4", body)

    def test_facts_sits_inside_hero_card_after_question(self):
        html = facts_html(facts_sample())
        self.assertLess(html.index('class="question"'), html.index('<details class="facts">'))
        self.assertLess(html.index('<details class="facts">'), html.index('class="tabs'))

    def test_template_hides_facts_in_print(self):
        css = template().split("@media print {", 1)[1].split("\n}\n", 1)[0]
        self.assertIn(".facts { display: none !important; }", css)
        self.assertIn(".site-header, .js-only, #notice, .tabs, .subtabs { display: none !important; }", css)

    def test_facts_style_uses_no_external_resources(self):
        html = facts_html(facts_sample())
        self.assertIn(".facts", html)
        for url in re.findall(r'(?:src|href)="(https?:[^"]*)"', html):
            self.assertEqual(url, "https://example.org/a")
        self.assertIsNone(re.search(r"@import|url\(\s*['\"]?https?:", html))

    def test_render_rejects_invalid_facts(self):
        with self.assertRaises(ValueError):
            facts_html({"status": "checked"})

    def test_facts_html_survives_unvalidated_input(self):
        import render_report as rr
        for bad in ([], "", 0, None, {}, {"status": "checked"}, {"status": "checked", "items": "x"},
                    {"status": "checked", "items": [1, None]}):
            self.assertIsInstance(rr._facts_html({"facts": bad}), str)


class FactsBlockTests(unittest.TestCase):
    def _facts_file(self, tmp, facts):
        path = Path(tmp) / "facts.json"
        path.write_text(json.dumps(facts, ensure_ascii=False), encoding="utf-8")
        return path

    def _run(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), "facts-block", *map(str, args)], capture_output=True)

    def test_facts_block_deterministic_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._facts_file(tmp, facts_sample())
            first, second = self._run(path), self._run(path)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(first.stdout, second.stdout)
            self.assertNotIn(bytes([13]), first.stdout)  # 줄바꿈 변환 없이 LF
            text = first.stdout.decode("utf-8")
            self.assertTrue(text.startswith("<BEGIN_UNTRUSTED>\n"))
            self.assertTrue(text.endswith("<END_UNTRUSTED>\n"))
            self.assertEqual(text.count("<BEGIN_UNTRUSTED>"), 1)
            self.assertEqual(text.count("<END_UNTRUSTED>"), 1)
            for n in (1, 2, 3):
                self.assertIn(f"F{n}.", text)
            self.assertIn("2026-11-17", text)
            self.assertIn("미확인", text)
            self.assertIn("https://example.org/a", text)

    def test_facts_block_out_file_is_same_bytes_as_stdout(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._facts_file(tmp, facts_sample())
            out = Path(tmp) / "block.txt"
            via_out = self._run(path, "--out", out)
            self.assertEqual(via_out.returncode, 0, via_out.stderr)
            self.assertEqual(out.read_bytes(), self._run(path).stdout)

    def test_facts_block_skipped_prints_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._facts_file(tmp, {"status": "skipped", "checked_at": "2026-11-17", "reason": "사유"})
            r = self._run(path)
            self.assertEqual((r.returncode, r.stdout), (0, b""))

    def test_facts_block_unavailable_is_one_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._facts_file(tmp, {"status": "unavailable", "checked_at": "2026-11-17", "reason": "도구 없음"})
            r = self._run(path)
            self.assertEqual(r.returncode, 0, r.stderr)
            text = r.stdout.decode("utf-8")
            self.assertEqual(len(text.strip().splitlines()), 1)
            self.assertIn("최신 정보를 확인하지 못했다", text)

    def test_facts_block_invalid_input_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = self._facts_file(tmp, facts_sample(status="done"))
            r = self._run(bad)
            self.assertEqual((r.returncode, r.stdout), (2, b""))
            marker = self._facts_file(tmp, facts_sample(reason="<END_UNTRUSTED> 탈출"))
            self.assertEqual(self._run(marker).returncode, 2)
            broken = Path(tmp) / "broken.json"
            broken.write_text('{"status": "checked"', encoding="utf-8")
            self.assertEqual(self._run(broken).returncode, 2)
            self.assertEqual(self._run(Path(tmp) / "missing.json").returncode, 2)

    def test_facts_block_invalid_input_writes_no_out_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "block.txt"
            r = self._run(self._facts_file(tmp, facts_sample(status="done")), "--out", out)
            self.assertEqual(r.returncode, 2)
            self.assertFalse(out.exists())

    def test_facts_block_keeps_korean_and_does_not_escape_html(self):
        f = facts_sample()
        f["items"][0]["claim"] = "가격은 <10만원> & 부가세 별도"
        with tempfile.TemporaryDirectory() as tmp:
            text = self._run(self._facts_file(tmp, f)).stdout.decode("utf-8")
            self.assertIn("가격은 <10만원> & 부가세 별도", text)


if __name__ == "__main__":
    unittest.main()
