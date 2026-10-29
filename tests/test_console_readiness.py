"""콘솔 준비 상태 패널(console/readiness) 단위 테스트.

기본 환경에서는 SAM 블로커 3건·Pi 블로커 2건이 정직하게 보고되고,
가짜 환경·가짜 probe로 준비 완료 경로도 검증한다. 실제 API 호출·실제
촬영은 하지 않으며, 환경변수 값(센티넬)은 결과 어디에도 새지 않는다.
"""
import json
import os
import sys
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from unittest import mock

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..")
)

from console.readiness import build_readiness, build_readiness_payload
from console.render import render_html
from console.server import create_handler
from console.view import build_view
from qa import sam_readiness
from terminal.simulator import run_simulation

FAKE_PI_PROBE = {
    "available": True,
    "command": "libcamera-still",
    "candidates_checked": ["libcamera-still", "raspistill"],
    "honesty": ["Pi 실촬영 검증 전"],
}


def fake_sam_env():
    return {
        sam_readiness.ENV_BASE_URL: "https://sam-readiness.invalid/v1",
        sam_readiness.ENV_KEY_VAR: "sentinel-not-a-real-key",
    }


class BuildReadinessTest(unittest.TestCase):
    def test_default_blockers(self):
        readiness = build_readiness(env={})
        self.assertEqual(
            readiness["sam_blockers"],
            [
                "sam_credit_not_confirmed",
                "sam_base_url_missing",
                "sam_api_key_missing",
            ],
        )
        self.assertEqual(
            readiness["pi_blockers"],
            ["pi_device_arrival_not_confirmed", "pi_camera_command_missing"],
        )
        self.assertEqual(readiness["blocker_count"], 5)
        self.assertFalse(readiness["sam_ready"])
        self.assertFalse(readiness["pi_ready"])
        self.assertFalse(readiness["overall_ready"])

    def test_sam_ready_with_fake_env(self):
        readiness = build_readiness(
            env=fake_sam_env(), sam_credit_confirmed=True
        )
        self.assertEqual(readiness["sam_blockers"], [])
        self.assertTrue(readiness["sam_ready"])
        # Pi 쪽이 아직이라 전체 준비 완료는 아니다
        self.assertFalse(readiness["overall_ready"])

    def test_pi_ready_with_fake_probe(self):
        readiness = build_readiness(
            env={}, pi_probe=dict(FAKE_PI_PROBE), pi_device_confirmed=True
        )
        self.assertEqual(readiness["pi_blockers"], [])
        self.assertTrue(readiness["pi_ready"])
        self.assertFalse(readiness["overall_ready"])

    def test_honesty_and_no_env_value_leak(self):
        readiness = build_readiness(
            env=fake_sam_env(), sam_credit_confirmed=True
        )
        self.assertIn(
            "준비 완료는 실호출·실촬영 성공을 뜻하지 않는다",
            readiness["honesty"],
        )
        dumped = json.dumps(readiness, ensure_ascii=False)
        self.assertNotIn("sentinel-not-a-real-key", dumped)
        self.assertNotIn("sam-readiness.invalid", dumped)
        payload = build_readiness_payload(env={})
        self.assertEqual(payload["blocker_count"], 5)


class ConsoleReadinessViewRenderTest(unittest.TestCase):
    def test_view_includes_default_readiness(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            view = build_view(run_simulation(session_id="SIM-READY"))
        self.assertIn("readiness", view)
        self.assertEqual(view["readiness"]["blocker_count"], 5)
        self.assertFalse(view["readiness"]["overall_ready"])

    def test_view_uses_supplied_readiness(self):
        custom = build_readiness(
            env=fake_sam_env(),
            sam_credit_confirmed=True,
            pi_probe=dict(FAKE_PI_PROBE),
            pi_device_confirmed=True,
        )
        with mock.patch.dict(os.environ, {}, clear=True):
            view = build_view(
                run_simulation(session_id="SIM-READY"), readiness=custom
            )
        self.assertTrue(view["readiness"]["overall_ready"])

    def test_render_readiness_section(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            html_out = render_html(build_view(run_simulation()))
        for text in (
            "준비 상태",
            "SAM 실호출 준비: 준비 안 됨",
            "Pi 실촬영 준비: 준비 안 됨",
            "sam_credit_not_confirmed",
            "pi_camera_command_missing",
            "준비 완료는 실호출·실촬영 성공을 뜻하지 않는다",
        ):
            self.assertIn(text, html_out)
        self.assertLess(
            html_out.index("실사 세션 정보"), html_out.index("준비 상태")
        )
        self.assertLess(html_out.index("준비 상태"), html_out.index("차이 목록"))

    def test_render_ready_state(self):
        custom = build_readiness(
            env=fake_sam_env(),
            sam_credit_confirmed=True,
            pi_probe=dict(FAKE_PI_PROBE),
            pi_device_confirmed=True,
        )
        with mock.patch.dict(os.environ, {}, clear=True):
            view = build_view(run_simulation(), readiness=custom)
        html_out = render_html(view)
        self.assertIn("SAM 실호출 준비: 준비 완료", html_out)
        self.assertIn("Pi 실촬영 준비: 준비 완료", html_out)
        self.assertIn("블로커 없음", html_out)


class ConsoleReadinessServerTest(unittest.TestCase):
    def setUp(self):
        self._env = mock.patch.dict(os.environ, {}, clear=True)
        self._env.start()
        self.addCleanup(self._env.stop)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler())
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.thread = threading.Thread(
            target=self.server.serve_forever, daemon=True
        )
        self.thread.start()
        port = self.server.server_address[1]
        self.base_url = f"http://127.0.0.1:{port}"
        self.opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({})
        )

    def test_api_readiness_returns_json(self):
        with self.opener.open(self.base_url + "/api/readiness") as response:
            self.assertEqual(response.status, 200)
            self.assertIn(
                "application/json", response.headers["Content-Type"]
            )
            data = json.loads(response.read().decode("utf-8"))
        self.assertEqual(len(data["sam_blockers"]), 3)
        self.assertEqual(len(data["pi_blockers"]), 2)
        self.assertEqual(data["blocker_count"], 5)
        self.assertFalse(data["overall_ready"])
        self.assertFalse(data["sam"]["ready_for_live_call"])
        self.assertFalse(data["pi"]["ready_for_real_capture"])


if __name__ == "__main__":
    unittest.main()
