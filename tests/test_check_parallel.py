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


if __name__ == "__main__":
    unittest.main()
