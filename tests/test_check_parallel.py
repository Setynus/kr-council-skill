import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from check_parallel import check_parallel  # noqa: E402


def use(uid, subagent_type="general-purpose", prompt="질문"):
    return {"type": "tool_use", "id": uid, "name": "Agent",
            "input": {"subagent_type": subagent_type, "prompt": prompt}}


def assistant(msg_id, *blocks):
    """실제 기록처럼 한 응답의 블록마다 한 줄씩, 같은 message.id로 만든다."""
    return [{"type": "assistant", "message": {"id": msg_id, "content": [b]}} for b in blocks]


def result(uid, text="결과 본문입니다 결과 본문입니다 결과 본문입니다 결과 본문입니다"):
    return {"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": uid, "content": text}]}}


def good_run():
    e = []
    e += assistant("m1", *[use(f"a{i}") for i in range(5)])
    e += [result(f"a{i}", f"위원{i}의 고유한 답변 내용입니다 번호{i}") for i in range(5)]
    e += assistant("m2", *[use(f"r{i}", prompt="익명 응답 검토") for i in range(5)])
    e += [result(f"r{i}") for i in range(5)]
    e += assistant("m3", use("c0", prompt="위원장 종합"))
    e += [result("c0")]
    return e


RECEIPT = "Async agent launched successfully. (internal)\nagentId: {aid} (internal ID)\nThe agent is working in the background."


def receipt(uid, aid):
    return result(uid, RECEIPT.format(aid=aid))


def handback(aid, text):
    """실제 기록: 접수 알림과 별개로, 위원의 답은 나중에 <agent-message from=...> 사용자 메시지로 도착한다."""
    return {"type": "user", "message": {"content":
            f'Another Claude session sent a message:\n<agent-message from="{aid}">\n[Subagent hand-back] {text}\n</agent-message>'}}


def async_run(batch_size=5, subagent_type="general-purpose", leak=None):
    e = []
    if leak:
        e += assistant("m0", use("x0")) + [receipt("x0", "ax0"), handback("ax0", leak)]
    e += assistant("m1", *[use(f"a{i}", subagent_type, prompt=f"질문 {leak or ''}") for i in range(batch_size)])
    e += [receipt(f"a{i}", f"aa{i}") for i in range(batch_size)]
    e += [handback(f"aa{i}", f"위원{i}의 고유한 답변 내용입니다 번호{i}") for i in range(batch_size)]
    e += assistant("m2", *[use(f"r{i}", subagent_type, prompt="익명 응답 검토") for i in range(batch_size)])
    e += [receipt(f"r{i}", f"rr{i}") for i in range(batch_size)]
    e += [handback(f"rr{i}", "검토 결과 본문입니다 번호") for i in range(batch_size)]
    e += assistant("m3", use("c0", subagent_type, prompt="위원장 종합"))
    e += [receipt("c0", "cc0"), handback("cc0", "판정 본문입니다 판정")]
    return e


class CheckParallelTests(unittest.TestCase):
    def test_parallel_ok_returns_empty(self):
        self.assertEqual(check_parallel(good_run()), [])

    def test_sequential_calls_flagged(self):
        e = []
        for i in range(5):
            e += assistant(f"s{i}", use(f"a{i}"))
            e += [result(f"a{i}")]
        self.assertTrue(any("묶" in v for v in check_parallel(e)))

    def test_only_one_batch_flagged(self):
        e = assistant("m1", *[use(f"a{i}") for i in range(5)]) + [result(f"a{i}") for i in range(5)]
        self.assertTrue(any("두 묶음" in v for v in check_parallel(e)))

    def test_result_read_before_all_launched_flagged(self):
        blocks = [use(f"a{i}") for i in range(5)]
        e = assistant("m1", *blocks[:4]) + [result("a0")] + assistant("m1", blocks[4])
        e += [result(f"a{i}") for i in range(1, 5)]
        e += assistant("m2", *[use(f"r{i}") for i in range(5)])
        self.assertTrue(any("시작하기 전에" in v for v in check_parallel(e)))

    def test_cross_contamination_flagged(self):
        leaked = "앞선 호출의 결과로 나온 아주 긴 고유 문장입니다 이 문장이 위원 프롬프트에 새어 들어가면 안 됩니다"
        e = assistant("m0", use("x0")) + [result("x0", leaked)]
        e += assistant("m1", *[use(f"a{i}", prompt=f"질문 {leaked}") for i in range(5)])
        e += [result(f"a{i}") for i in range(5)]
        e += assistant("m2", *[use(f"r{i}") for i in range(5)])
        self.assertTrue(any("새어" in v for v in check_parallel(e)))

    def test_fork_flagged(self):
        e = good_run()
        e[2]["message"]["content"][0]["input"]["subagent_type"] = "fork"
        self.assertTrue(any("fork" in v for v in check_parallel(e)))

    def test_missing_subagent_type_flagged(self):
        e = good_run()
        del e[1]["message"]["content"][0]["input"]["subagent_type"]
        self.assertTrue(any("subagent_type" in v for v in check_parallel(e)))

    def test_async_run_ok(self):
        self.assertEqual(check_parallel(async_run()), [])

    def test_async_leak_flagged(self):
        leaked = "앞선 호출의 결과로 나온 아주 긴 고유 문장입니다 이 문장이 위원 프롬프트에 새어 들어가면 안 됩니다"
        self.assertTrue(any("새어" in v for v in check_parallel(async_run(leak=leaked))))

    def test_async_review_before_advisor_results_flagged(self):
        e = async_run()
        # 자문 결과(핸드백) 전에 검토 묶음을 시작하도록 순서를 뒤집는다
        i_hand = next(i for i, x in enumerate(e) if "agent-message" in str(x["message"]["content"]))
        i_m2 = next(i for i, x in enumerate(e) if x.get("message", {}).get("id") == "m2")
        e.insert(i_hand, e.pop(i_m2))
        self.assertTrue(any("끝나기 전" in v for v in check_parallel(e)))

    def test_non_general_purpose_flagged(self):
        self.assertTrue(any("general-purpose" in v for v in check_parallel(async_run(subagent_type="Explore"))))

    def test_oversized_batch_flagged(self):
        self.assertTrue(any("정확히" in v for v in check_parallel(async_run(batch_size=6))))

    def test_receipt_without_result_is_unverified_not_pass(self):
        e = async_run()
        e = [x for x in e if "agent-message" not in str(x["message"]["content"]) or "hand-back" not in str(x["message"]["content"])]
        self.assertTrue(any("확인하지 못" in v for v in check_parallel(e)))

    def test_queued_command_handback_is_a_result(self):
        e = [({"type": "attachment", "attachment": {"type": "queued_command", "prompt": x["message"]["content"]}}
              if x.get("type") == "user" and "agent-message" in str(x["message"]["content"]) else x)
             for x in async_run()]
        self.assertEqual(check_parallel(e), [])


if __name__ == "__main__":
    unittest.main()
