"""SAM 어댑터 단위 테스트.

실호출 경로는 가짜 transport로만 검증한다 — 실제 네트워크·실제 API 호출 없음.
크레딧 입금 확인 전이라 실호출 검증이 아니며, 규격 의존 부분
(build_payload/parse_response)이 격리돼 있는지를 확인하는 준비 단계 테스트다.
"""
import json
import os
import sys
import unittest
from unittest import mock

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..")
)

from terminal.sam_adapter import (
    MODEL_ID,
    LiveSamCounter,
    MockSamCounter,
    SamCountingError,
    build_counter,
    build_payload,
    parse_response,
)

DEMO_COUNTS = {"A-01-02": 5, "B-01-02": 9}


class MockAndSelectionTest(unittest.TestCase):
    def test_mock_counter_counts_demo_value(self):
        counter = MockSamCounter(DEMO_COUNTS)
        result = counter.count("A-01-02")
        self.assertEqual(result.counted_qty, 5)
        self.assertEqual(result.source, "mock")

    def test_build_counter_without_env_is_mock(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            counter = build_counter(DEMO_COUNTS)
        self.assertIsInstance(counter, MockSamCounter)

    def test_build_counter_with_only_one_env_is_mock(self):
        with mock.patch.dict(
            os.environ, {"SAM_API_BASE_URL": "https://example.invalid/sam"}, clear=True
        ):
            counter = build_counter(DEMO_COUNTS)
        self.assertIsInstance(counter, MockSamCounter)

    def test_build_counter_with_both_env_is_live(self):
        env = {
            "SAM_API_BASE_URL": "https://example.invalid/sam",
            "SAM_API_KEY": "test-key-not-real",
        }
        with mock.patch.dict(os.environ, env, clear=True):
            counter = build_counter(DEMO_COUNTS)
        self.assertIsInstance(counter, LiveSamCounter)
        self.assertEqual(counter.source, "sam")


class PayloadAndParseTest(unittest.TestCase):
    def test_build_payload_shape(self):
        payload = build_payload("A-01-02", image_ref="photo-1.jpg")
        self.assertEqual(payload["model"], MODEL_ID)
        self.assertEqual(payload["model"], "sam-3.1")
        self.assertEqual(payload["bin_id"], "A-01-02")
        self.assertEqual(payload["image_ref"], "photo-1.jpg")
        self.assertIn("prompt", payload)

    def test_parse_response_variants(self):
        self.assertEqual(parse_response({"counted_qty": 7}), 7)
        self.assertEqual(parse_response({"count": 3}), 3)
        self.assertEqual(parse_response({"result": {"quantity": 4}}), 4)
        self.assertEqual(parse_response({"detections": [1, 2]}), 2)
        self.assertEqual(parse_response({"segments": [1, 2, 3]}), 3)

    def test_parse_response_rejects_bad_shapes(self):
        for bad in ({"counted_qty": -1}, {"counted_qty": True}, {"other": 1}, [], None):
            with self.assertRaises(SamCountingError):
                parse_response(bad)


class LiveCounterFakeTransportTest(unittest.TestCase):
    def test_live_count_uses_injected_transport_without_network(self):
        seen = {}

        def fake_transport(url, headers, body, timeout):
            seen["url"] = url
            seen["headers"] = headers
            seen["body"] = body
            return 200, {"counted_qty": 5}

        counter = LiveSamCounter(
            "https://example.invalid/sam/", "test-key-not-real", transport=fake_transport
        )
        result = counter.count("A-01-02", image_ref="photo-1.jpg")
        self.assertEqual(result.counted_qty, 5)
        self.assertEqual(result.source, "sam")
        self.assertEqual(seen["url"], "https://example.invalid/sam")
        self.assertEqual(seen["headers"]["Authorization"], "Bearer test-key-not-real")
        sent = json.loads(seen["body"])
        self.assertEqual(sent["bin_id"], "A-01-02")
        self.assertNotIn("test-key-not-real", seen["body"].decode())

    def test_live_count_http_error_raises_without_mock_fallback(self):
        def fake_transport(url, headers, body, timeout):
            return 503, {"error": "unavailable"}

        counter = LiveSamCounter(
            "https://example.invalid/sam", "test-key-not-real", transport=fake_transport
        )
        with self.assertRaises(SamCountingError):
            counter.count("A-01-02")

    def test_live_count_transport_exception_is_wrapped(self):
        def fake_transport(url, headers, body, timeout):
            raise OSError("network down")

        counter = LiveSamCounter(
            "https://example.invalid/sam", "test-key-not-real", transport=fake_transport
        )
        with self.assertRaises(SamCountingError) as ctx:
            counter.count("A-01-02")
        self.assertIsInstance(ctx.exception.__cause__, OSError)


if __name__ == "__main__":
    unittest.main()
