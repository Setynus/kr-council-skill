"""kr-council-skill/SKILL.md가 공식 스킬 작성 규칙(설계 문서 §6.5)을 지키는지 검사한다."""
import re
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent / "kr-council-skill"
SKILL_MD = SKILL_DIR / "SKILL.md"
DISCLAIMER = "같은 모델이 서로 다른 관점으로 낸 의견이며, 독립된 전문가 5인이 아닙니다."
FIRST_OR_SECOND_PERSON = ("나는", "내가", "당신", "너는", "제가", "저는", "I can", "You can")


def load():
    text = SKILL_MD.read_text(encoding="utf-8")
    match = re.match(r"---\n(.*?)\n---\n(.*)", text, re.S)
    assert match, "frontmatter(--- … ---)가 없습니다"
    front, body = match.groups()
    fields = {}
    for line in front.splitlines():
        m = re.match(r"([A-Za-z_-]+):\s*(.*)", line)
        if m:
            fields[m.group(1)] = m.group(2).strip()
    return text, fields, body


class SkillMdTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text, cls.fields, cls.body = load()

    def test_name_rules(self):
        name = self.fields.get("name", "")
        self.assertEqual(name, "kr-council-skill")
        self.assertRegex(name, r"^[a-z0-9]+(-[a-z0-9]+)*$")
        self.assertLessEqual(len(name), 64)
        self.assertEqual(name, SKILL_DIR.name)
        for banned in ("claude", "anthropic"):
            self.assertNotIn(banned, name)

    def test_description_rules(self):
        desc = self.fields.get("description", "")
        self.assertTrue(desc)
        self.assertLessEqual(len(desc), 1024)
        self.assertNotIn("<", desc)
        self.assertNotIn(">", desc)
        self.assertRegex(desc, r"[가-힣]")
        self.assertIn("쓰지 않", desc)
        self.assertRegex(desc, r"다\.")
        for token in FIRST_OR_SECOND_PERSON:
            self.assertNotIn(token, desc)

    def test_distinct_triggers(self):
        desc = self.fields["description"]
        for phrase in ("위원회 열어줘", "자문단 소집", "council 돌려줘"):
            self.assertIn(phrase, desc)
        for sentence in re.split(r"(?<=\.)\s+", desc):
            if "검토해줘" in sentence:
                self.assertIn("않", sentence, "'검토해줘'는 쓰지 않는 경우 문장에서만 나와야 합니다")

    def test_frontmatter_has_compatibility_and_metadata(self):
        self.assertIn("compatibility", self.fields)
        self.assertIn("metadata:", self.text)

    def test_body_under_500_lines(self):
        self.assertLess(len(self.text.splitlines()), 500)

    def test_critical_section_on_top(self):
        headings = [l for l in self.body.splitlines() if l.startswith("## ")]
        self.assertTrue(headings)
        self.assertEqual(headings[0], "## 중요")
        section = self.body.split("## 중요", 1)[1].split("\n## ", 1)[0]
        for needle in ("한 번의 응답", "fork", "금지", "general-purpose", "11"):
            self.assertIn(needle, section)

    def test_three_modes_present(self):
        for mode in ("병렬", "프롬프트 묶음", "단일 세션"):
            self.assertIn(mode, self.body)

    def test_script_path_variable(self):
        self.assertIn("${CLAUDE_SKILL_DIR}/scripts/render_report.py", self.text)
        self.assertIn("이 SKILL.md가 있는 폴더", self.text)
        for line in self.text.splitlines():
            if "scripts" in line:
                self.assertNotIn("\\", line, f"역슬래시 경로: {line}")

    def test_output_path_and_disclaimer(self):
        self.assertIn("council-reports/", self.text)
        self.assertIn(DISCLAIMER, self.text)

    def test_references_one_level(self):
        links = re.findall(r"\]\((references/[^)#\s]+)\)", self.body)
        self.assertIn("references/advisors.md", links)
        self.assertIn("references/ko-context.md", links)
        for link in links:
            target = SKILL_DIR / link
            self.assertTrue(target.exists(), f"없는 참조: {link}")
            self.assertNotRegex(target.read_text(encoding="utf-8"), r"\]\([^)]*\.md",
                                f"{link}가 다른 파일을 다시 링크함(한 단계 깊이 규칙 위반)")

    def test_no_copied_original_phrases(self):
        for phrase in ("Lean fully into your assigned", "Don't hedge or try to be balanced",
                       "Always spawn all 5 advisors"):
            self.assertNotIn(phrase, self.text)

    def test_untrusted_marker(self):
        self.assertIn("UNTRUSTED", self.text)

    def test_no_readme_in_skill_folder(self):
        self.assertFalse((SKILL_DIR / "README.md").exists())

    def test_cost_notice_does_not_skip_when_preconsented(self):
        self.assertNotIn("이미 동의했으면 다시 묻지 않는다", self.text)
        self.assertIn("한 줄", self.body.split("## 1단계", 1)[1].split("## 2단계", 1)[0])

    def test_reviewers_get_verbatim_responses(self):
        section = self.body.split("## 3단계", 1)[1].split("## 4단계", 1)[0]
        self.assertIn("원문", section)
        self.assertIn("요약", section)

    def test_real_clock_for_timestamp(self):
        section = self.body.split("## 5단계", 1)[1]
        self.assertIn("date", section)
        self.assertNotIn("0000", section)

    def test_council_json_copies_advisor_text_unchanged(self):
        section = self.body.split("## 5단계", 1)[1]
        self.assertIn("고치지 않고 그대로", section)

    def test_cost_notice_depends_on_mode(self):
        self.assertIn("병렬일 때만", self.body)

    def test_prompt_pack_and_single_session_review_procedures(self):
        section = self.body.split("## 3단계", 1)[1].split("## 4단계", 1)[0]
        self.assertIn("프롬프트 묶음", section)
        self.assertIn("단일 세션", section)

    def test_advisor_responses_wrapped_as_untrusted_for_reviewers(self):
        section = self.body.split("## 3단계", 1)[1].split("## 4단계", 1)[0]
        self.assertIn("UNTRUSTED", section)

    def test_failed_advisor_answer_handling(self):
        self.assertIn("한 번만 다시", self.body)

    def test_retry_and_korean_rules_cover_review_and_chair_steps(self):
        self.assertIn("닫는 괄호", self.body)
        for head, tail in (("## 3단계", "## 4단계"), ("## 4단계", "## 5단계")):
            section = self.body.split(head, 1)[1].split(tail, 1)[0]
            self.assertIn("한국어", section)
            self.assertIn("재호출 규칙", section)

    def test_english_answers_are_retried_and_never_repaired_or_translated(self):
        section = self.body.split("## 2단계", 1)[1].split("## 3단계", 1)[0]
        self.assertIn("한국어가 아닌 문장", section)  # 재호출 사유이자 repair 거부 사유
        self.assertIn("번역해서 끼워 넣지 않고", section)

    def test_critical_section_requires_complete_json_before_next_step_and_unsplit_review_batch(self):
        section = self.body.split("## 중요", 1)[1].split("\n## ", 1)[0]
        self.assertIn("끝이 닫힌 완결된 JSON", section)
        self.assertIn("council.json", section)
        self.assertIn("직접 이어 붙여 쓰지 않는다", section)
        self.assertIn("5개가 모두 나가기 전에는 어떤 결과도 읽지 않는다", section)
        self.assertIn("닫는 따옴표와 중괄호까지 써서 끝내라고", self.body)

    def test_review_weakness_criterion_and_minority_definition(self):
        review = self.body.split("## 3단계", 1)[1].split("## 4단계", 1)[0]
        self.assertIn("모든 응답에 똑같이 적용", review)
        self.assertIn("구체적 내용", review)
        chair = self.body.split("## 4단계", 1)[1].split("## 5단계", 1)[0]
        self.assertIn("전원이 같은 방향이면 false", chair)
        self.assertIn("예시값을 적어 넣지 않는다", chair)
        advisors_md = (SKILL_DIR / "references" / "advisors.md").read_text(encoding="utf-8")
        self.assertIn("입장 없이 끝내기", advisors_md)

    def test_timestamp_command_works_in_any_shell(self):
        section = self.body.split("## 5단계", 1)[1]
        self.assertIn("python -c", section)
        self.assertNotIn('date +"', section)

    def test_extra_fields_not_copied(self):
        self.assertIn("규격 밖", self.body.split("## 5단계", 1)[1])

    def test_smurf_display_names(self):
        names = ("투덜이 스머프", "똘똘이 스머프", "화가 스머프", "덜렁이 스머프", "재주꾼 스머프", "파파스머프")
        advisors_md = (SKILL_DIR / "references" / "advisors.md").read_text(encoding="utf-8")
        for name in names:
            self.assertIn(name, self.body)
        for name in names[:5]:
            self.assertIn(name, advisors_md)
        self.assertIn("본질 탐구자", self.body)
        self.assertNotIn("제1원리 사색가", self.body)
        self.assertNotIn("제1원리 사색가", advisors_md)

    def test_prompts_use_functional_names_not_character_names(self):
        self.assertIn("호출 프롬프트에는 기능 이름", self.body)

    def test_frontmatter_plain_scalars_are_yaml_safe(self):
        front = self.text.split("---", 2)[1]
        for line in front.splitlines():
            key, _, value = line.partition(": ")
            if line.startswith(" ") or not value:
                continue
            for hazard in (": ", " #"):
                self.assertNotIn(hazard, value, f"{key}: YAML 일반 문자열에 '{hazard}'가 있음")

    def test_python3_fallback_documented(self):
        self.assertIn("python3", self.body)

    def test_background_results_wait_for_all_five(self):
        self.assertIn("일부만 먼저 도착", self.body)

    def test_council_json_is_not_overwritten(self):
        section = self.body.split("## 5단계", 1)[1]
        self.assertIn("council-YYYYMMDD-HHMM.json", section)

    def test_untrusted_marker_escape_rule(self):
        self.assertIn("꺾쇠 안쪽에 공백", self.body)

    def test_python3_note_is_in_critical_section(self):
        section = self.body.split("## 중요", 1)[1].split("## 0단계", 1)[0]
        self.assertIn("python3", section)

    def test_closure_is_decided_by_check_not_by_eye(self):
        section = self.body.split("## 중요", 1)[1].split("## 0단계", 1)[0]
        self.assertIn("render_report.py", section)
        self.assertIn("check", section)
        self.assertIn("눈으로 보고 판정하지 않는다", section)
        step2 = self.body.split("## 2단계", 1)[1].split("## 3단계", 1)[0]
        for kind in ("check advisor", "check review", "check verdict"):
            self.assertIn(kind, step2)

    def test_cost_notice_counts_retries(self):
        section = self.body.split("## 중요", 1)[1].split("## 0단계", 1)[0]
        self.assertIn("재호출", section.split("비용을 먼저 알린다", 1)[1].split("\n", 1)[0])

    def test_subagents_save_raw_answers_to_files(self):
        step2 = self.body.split("## 2단계", 1)[1].split("## 3단계", 1)[0]
        for needle in ("raw-YYYYMMDD-HHMM", "advisor-<id>.json", "reviews/<글자>.json", "verdict.json",
                       "Write 도구", "다른 파일은 읽지 않는다", "저장이 막히면", "JSON 자체를 답"):
            self.assertIn(needle, step2)

    def test_review_files_do_not_reveal_advisor_id(self):
        step2 = self.body.split("## 2단계", 1)[1].split("## 3단계", 1)[0]
        self.assertIn("위원 id가 드러나지 않게", step2)
        self.assertNotIn("review-<id>", self.body)

    def test_steps_3_and_4_read_the_saved_files(self):
        step3 = self.body.split("## 3단계", 1)[1].split("## 4단계", 1)[0]
        step4 = self.body.split("## 4단계", 1)[1].split("## 5단계", 1)[0]
        self.assertIn("advisor-<id>.json", step3)
        self.assertIn("읽어", step3)
        self.assertIn("읽어", step4)

    def test_timestamp_is_obtained_once_and_reused(self):
        step5 = self.body.split("## 5단계", 1)[1]
        self.assertIn("2단계에서 얻은 값", step5)

    def test_subagents_get_absolute_paths(self):
        step2 = self.body.split("## 2단계", 1)[1].split("## 3단계", 1)[0]
        self.assertIn("절대 경로", step2)

    def test_rejected_file_is_set_aside_before_the_retry(self):
        step2 = self.body.split("## 2단계", 1)[1].split("## 3단계", 1)[0]
        self.assertIn("재호출하기 전에", step2)
        self.assertIn("attempt1-rejected", step2)

    def test_check_has_an_exception_for_environments_without_code(self):
        section = self.body.split("## 중요", 1)[1].split("## 0단계", 1)[0]
        self.assertIn("코드를 실행할 수 없는", section)

    def test_report_step_assembles_from_raw_files_and_keeps_manual_fallback(self):
        step5 = self.body.split("## 5단계", 1)[1]
        self.assertIn("render_report.py\" assemble", step5)
        self.assertIn("meta.json", step5)
        self.assertIn("고치지 않고 그대로", step5)

    def test_second_failure_is_auto_repaired_by_script_and_disclosed(self):
        step2 = self.body.split("## 2단계", 1)[1].split("## 3단계", 1)[0]
        self.assertIn("repair <advisor|review|verdict>", step2)
        self.assertIn("사용자에게 묻지 않고", step2)
        self.assertIn("before-repair", step2)
        self.assertIn("손으로 고치거나", step2)
        self.assertIn("거부하면", step2)  # 보정이 안 되는 실패는 계속 묻는다

    def test_final_message_gives_absolute_report_path(self):
        step5 = self.body.split("## 5단계", 1)[1]
        self.assertIn("절대 경로", step5)

    def test_crisis_signal_stops_before_convening(self):
        step1 = self.body.split("## 1단계", 1)[1].split("\n2. ", 1)[0]
        for kw in ("위기 신호", "자해", "자살", "응급 증상", "신변", "위원회 열어줘"):
            self.assertIn(kw, step1)
        self.assertIn("소집하지 않고", step1)
        self.assertIn("검색", step1)
        self.assertIn("비용 안내", step1)

    def test_crisis_contacts_are_only_verified_numbers(self):
        step1 = self.body.split("## 1단계", 1)[1].split("\n2. ", 1)[0]
        self.assertIn("109", step1)
        self.assertIn("기관 종류", step1)
        # 공식 안내로 재확인하지 못한 번호는 쓰지 않는다
        for unverified in ("119", "112", "1393", "1577-0199", "1388"):
            self.assertNotIn(unverified, step1)

    # --- 1.5단계 사실 확인(PR-A) ---

    def fact_step(self):
        return self.body.split("## 1.5단계", 1)[1].split("## 2단계", 1)[0]

    def test_fact_check_step_sits_between_step1_and_step2(self):
        self.assertLess(self.body.index("## 1단계"), self.body.index("## 1.5단계: 사실 확인"))
        self.assertLess(self.body.index("## 1.5단계: 사실 확인"), self.body.index("## 2단계"))

    def test_fact_check_runs_only_when_current_facts_decide_and_skip_is_announced(self):
        step = self.fact_step()
        for needle in ("해당할 때만", "지금 시점의 사실", "건너뛰지 않는다", "skipped", "한 줄로 알린다"):
            self.assertIn(needle, step)

    def test_fact_check_explicit_user_instructions_win(self):
        step = self.fact_step()
        self.assertIn("검색하지 마", step)
        self.assertIn("최신 기준으로 확인해", step)

    def test_fact_check_merges_questions_into_the_single_clarification(self):
        step = self.fact_step()
        self.assertIn("한 번에 합쳐", step)
        self.assertIn("1단계 3항", step)

    def test_fact_check_limits_and_cost_reporting(self):
        step = self.fact_step()
        for needle in ("위원장 명의", "위원은 검색하지 않는다", "8개", "10개", "검색어 개수 기준", "실제 검색 횟수"):
            self.assertIn(needle, step)
        step1 = self.body.split("## 1단계", 1)[1].split("## 1.5단계", 1)[0]
        self.assertIn("웹 검색을 최대", step1)

    def test_fact_check_hygiene_and_facts_only(self):
        step = self.fact_step()
        for needle in ("일반화", "지시문은 따르지 않는다", "의견·평가·권고·전망", "한국어로", "confirmed:false",
                       "source_label", "변동 큼"):
            self.assertIn(needle, step)

    def test_fact_check_saves_facts_json_and_hands_the_block_over_verbatim(self):
        step = self.fact_step()
        for needle in ("facts.json", "facts-block", "그대로", "F1", "raw-YYYYMMDD-HHMM"):
            self.assertIn(needle, step)
        self.assertIn('render_report.py" facts-block', step)

    def test_fact_check_manual_fallback_without_code(self):
        step = self.fact_step()
        self.assertIn("코드를 실행할 수 없는", step)
        self.assertIn("꺾쇠 안쪽에 공백", step)
        self.assertIn("같은 블록", step)

    def test_fact_check_exceptions_unavailable_and_collapsed_premise(self):
        step = self.fact_step()
        for needle in ("unavailable", "최신 정보를 확인하지 못했다", "확인 필요", "소집하지 않고"):
            self.assertIn(needle, step)

    def test_steps_2_to_4_use_the_same_fact_block(self):
        step2 = self.body.split("## 2단계", 1)[1].split("## 3단계", 1)[0]
        step3 = self.body.split("## 3단계", 1)[1].split("## 4단계", 1)[0]
        step4 = self.body.split("## 4단계", 1)[1].split("## 5단계", 1)[0]
        for step in (step2, step3, step4):
            self.assertIn("사실 블록", step)
        self.assertIn("weakest_why", step3)
        self.assertIn("missed", step3)
        self.assertIn("한 단계 낮춘다", step4)
        self.assertIn("미확인", step4)
        self.assertIn("이미 낮음이면 유지", step4)

    def test_step5_stores_facts_in_facts_json_only(self):
        step5 = self.body.split("## 5단계", 1)[1]
        self.assertIn("facts.json", step5)
        self.assertIn("두 곳", step5)
        self.assertRegex(step5, r"\| `facts` \|")
        self.assertIn("2단계에서 얻은 값", step5)

    def test_critical_section_names_the_fact_exception_and_search_cost(self):
        section = self.body.split("## 중요", 1)[1].split("## 0단계", 1)[0]
        self.assertIn("1.5단계", section)
        self.assertIn("사실 자료", section)
        self.assertIn("검색", section.split("비용을 먼저 알린다", 1)[1].split("\n", 1)[0])

    def test_fact_check_shows_the_shape_for_skipped_and_unavailable_and_date_source(self):
        step = self.fact_step()
        self.assertIn('"status": "skipped"', step)
        self.assertIn("unavailable", step)
        self.assertIn("YYYY-MM-DD", step)
        self.assertIn("5단계의 명령", step)
        self.assertIn("단일 세션", step)

    def test_step5_timestamp_sentence_covers_the_early_timestamp_of_step_1_5(self):
        step5 = self.body.split("## 5단계", 1)[1]
        self.assertIn("1.5단계에서 먼저 얻었다면", step5)

    # --- 1.5단계 비교 안건(PR-B) ---

    def test_fact_check_compare_rules(self):
        step = self.fact_step()
        for needle in ("subjects", "subject", "공통", "대칭", "미확인", "똑같이", "대상당 얕아질"):
            self.assertIn(needle, step)

    def test_fact_check_compare_limits_are_stated_and_announced(self):
        step = self.fact_step()
        for needle in ("16개", "14개", "20개", "17개", "2~4개", "후보를 줄"):
            self.assertIn(needle, step)
        step1 = self.body.split("## 1단계", 1)[1].split("## 1.5단계", 1)[0]
        self.assertIn("웹 검색을 최대 8회", step1)  # 기존 문구는 그대로 둔다
        self.assertIn("비교 안건", step1)
        self.assertIn("14", step1)

    def test_fact_check_assumptions_and_jurisdiction(self):
        step = self.fact_step()
        for needle in ("assumptions", "산정", "총경비", "관할", "ko-context.md", "환율", "기준일"):
            self.assertIn(needle, step)

    def test_fact_check_format_example_shows_the_compare_fields(self):
        example = self.fact_step().split("```", 2)[1]
        for needle in ("subjects", "assumptions", '"subject"'):
            self.assertIn(needle, example)

    def test_step_numbering_in_fact_check_is_unique_and_sequential(self):
        nums = [int(n) for n in re.findall(r"^(\d+)\. ", self.fact_step(), flags=re.M)]
        self.assertEqual(nums, list(range(1, len(nums) + 1)))


if __name__ == "__main__":
    unittest.main()
