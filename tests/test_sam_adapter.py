"""SAM 어댑터 단위 테스트.

이 파일의 테스트는 가짜 transport로만 검증한다 — 실제 네트워크·실제
API 호출 없음. 규격 자체는 2026-10-30에 커넥터 경유 실호출 탐침으로
별도 검증했고, 여기서는 그 규격(responses 형식 본문·output_text 안
박스 마커 계수)과 종전 해석 형태가 함께 지켜지는지 확인한다.
"""
import base64
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
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
        self.assertEqual(set(payload), {"model", "input"})
        message = payload["input"][0]
        self.assertEqual(message["role"], "user")
        content = message["content"]
        self.assertEqual(content[0], {"type": "input_text", "text": "cardboard box"})
        self.assertEqual(content[1], {"type": "input_image",
                                      "image_url": "photo-1.jpg"})

    def test_build_payload_requires_image(self):
        with self.assertRaises(SamCountingError):
            build_payload("A-01-02")
        with self.assertRaises(SamCountingError):
            build_payload("A-01-02", image_ref=None)

    def test_build_payload_embeds_local_file_as_data_uri(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bin-photo.png"
            path.write_bytes(b"fake-png-bytes")
            payload = build_payload("A-01-02", image_ref=str(path))
        url = payload["input"][0]["content"][1]["image_url"]
        expected = "data:image/png;base64," + base64.b64encode(
            b"fake-png-bytes").decode("ascii")
        self.assertEqual(url, expected)

    def test_parse_response_responses_format_counts_boxes(self):
        text = ("<0f>0<|box;x1=1;y1=2;x2=3;y2=4;w=100;h=80|>"
                "<|mask;x=0;y=0;data=aa|>"
                "<|box;x1=5;y1=6;x2=7;y2=8;w=100;h=80|>"
                "<|mask;x=0;y=0;data=bb|>"
                "<|box;x1=9;y1=10;x2=11;y2=12;w=100;h=80|>"
                "<|mask;x=0;y=0;data=cc|>")
        payload = {"status": "completed", "output": [
            {"type": "message", "content": [
                {"type": "output_text", "text": text}]}]}
        self.assertEqual(parse_response(payload), 3)

    def test_parse_response_responses_format_zero_and_mask_only(self):
        empty = {"output": [{"type": "message", "content": [
            {"type": "output_text", "text": ""}]}]}
        self.assertEqual(parse_response(empty), 0)
        mask_only = {"output": [{"type": "message", "content": [
            {"type": "output_text",
             "text": "<|mask;x=0;y=0;data=aa|><|mask;x=0;y=0;data=bb|>"}]}]}
        self.assertEqual(parse_response(mask_only), 2)

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
        self.assertEqual(sent["model"], "sam-3.1")
        self.assertEqual(sent["input"][0]["content"][1]["image_url"], "photo-1.jpg")
        self.assertNotIn("test-key-not-real", seen["body"].decode())

    def test_live_count_with_responses_shaped_fake_transport(self):
        def fake_transport(url, headers, body, timeout):
            text = ("<|box;x1=1;y1=2;x2=3;y2=4;w=100;h=80|>"
                    "<|mask;x=0;y=0;data=aa|>"
                    "<|box;x1=5;y1=6;x2=7;y2=8;w=100;h=80|>"
                    "<|mask;x=0;y=0;data=bb|>")
            return 200, {"status": "completed", "output": [
                {"type": "message", "content": [
                    {"type": "output_text", "text": text}]}]}

        counter = LiveSamCounter(
            "https://example.invalid/sam", "test-key-not-real",
            transport=fake_transport)
        result = counter.count("A-01-02", image_ref="photo-1.jpg")
        self.assertEqual(result.counted_qty, 2)
        self.assertEqual(result.source, "sam")

    def test_live_count_http_error_raises_without_mock_fallback(self):
        def fake_transport(url, headers, body, timeout):
            return 503, {"error": "unavailable"}

        counter = LiveSamCounter(
            "https://example.invalid/sam", "test-key-not-real", transport=fake_transport
        )
        with self.assertRaises(SamCountingError):
            counter.count("A-01-02", image_ref="photo-1.jpg")

    def test_live_count_transport_exception_is_wrapped(self):
        def fake_transport(url, headers, body, timeout):
            raise OSError("network down")

        counter = LiveSamCounter(
            "https://example.invalid/sam", "test-key-not-real", transport=fake_transport
        )
        with self.assertRaises(SamCountingError) as ctx:
            counter.count("A-01-02", image_ref="photo-1.jpg")
        self.assertIsInstance(ctx.exception.__cause__, OSError)


if __name__ == "__main__":
    unittest.main()
