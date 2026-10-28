"""파일 기반 사진 입력 파이프라인 테스트.

Pi 실촬영이 아니라 임시 파일로 만든 가짜 이미지 바이트를 쓴다.
계수는 모의 어댑터 기준이며, 대조 요약은 시뮬레이터와 같은 데모
기준값(빈 6·일치 4·불일치 2·절대차이 6·순차이 0)이어야 한다.
"""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from terminal.demo_data import demo_bin_ids
from terminal.photo_intake import (
    SUPPORTED_EXTENSIONS,
    CaptureRecord,
    load_capture,
    main,
    run_photo_intake,
)


def _write_photo(directory: Path, name: str, content: bytes) -> Path:
    path = directory / name
    path.write_bytes(content)
    return path


def _full_captures(directory: Path) -> dict[str, Path]:
    captures = {}
    for bin_id in demo_bin_ids():
        captures[bin_id] = _write_photo(
            directory, f"{bin_id}.jpg", f"fake-photo-{bin_id}".encode()
        )
    return captures


class LoadCaptureTests(unittest.TestCase):
    def test_record_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            content = b"fake-jpeg-bytes"
            path = _write_photo(Path(tmp), "rack.JPG", content)
            record = load_capture("A-01-02", path)
            self.assertIsInstance(record, CaptureRecord)
            self.assertEqual(record.bin_id, "A-01-02")
            self.assertEqual(record.image_ref, "rack.JPG")
            self.assertEqual(record.size_bytes, len(content))
            self.assertEqual(record.sha256, hashlib.sha256(content).hexdigest())
            self.assertEqual(record.suffix, ".jpg")
            self.assertIn(".png", SUPPORTED_EXTENSIONS)

    def test_missing_file_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                load_capture("A-01-02", Path(tmp) / "nope.jpg")

    def test_unsupported_extension_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_photo(Path(tmp), "notes.txt", b"hello")
            with self.assertRaises(ValueError):
                load_capture("A-01-02", path)

    def test_empty_file_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_photo(Path(tmp), "empty.jpg", b"")
            with self.assertRaises(ValueError):
                load_capture("A-01-02", path)


class RunPhotoIntakeTests(unittest.TestCase):
    def test_full_report_matches_demo_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            captures = _full_captures(Path(tmp))
            report = run_photo_intake(captures, session_id="PHOTO-TEST-1")
            self.assertEqual(report["session_id"], "PHOTO-TEST-1")
            self.assertEqual(report["source"], "mock")
            self.assertEqual(report["capture_source"], "file")
            self.assertTrue(
                any("Pi 실촬영이 아닙니다" in line for line in report["honesty"])
            )
            summary = report["summary"]
            self.assertEqual(summary["counted_bins"], 6)
            self.assertEqual(summary["matched"], 4)
            self.assertEqual(summary["mismatched"], 2)
            self.assertEqual(summary["abs_diff_total"], 6)
            self.assertEqual(summary["net_diff"], 0)
            by_bin = {b["bin_id"]: b for b in report["bins"]}
            self.assertEqual(by_bin["A-01-02"]["verdict"], "short")
            self.assertEqual(by_bin["A-01-02"]["diff"], -3)
            self.assertEqual(by_bin["B-01-02"]["verdict"], "over")
            expected_sha = hashlib.sha256(b"fake-photo-A-01-02").hexdigest()
            self.assertEqual(by_bin["A-01-02"]["photo"]["sha256"], expected_sha)
            self.assertEqual(
                by_bin["A-01-02"]["photo"]["image_ref"], "A-01-02.jpg"
            )

    def test_subset_of_bins(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            captures = {
                "A-01-01": _write_photo(root, "a.jpg", b"a-bytes"),
                "B-02-02": _write_photo(root, "b.png", b"b-bytes"),
            }
            report = run_photo_intake(captures, session_id="PHOTO-TEST-2")
            self.assertEqual(report["summary"]["counted_bins"], 2)
            self.assertEqual(report["summary"]["matched"], 2)
            self.assertEqual(report["bins"][1]["photo"]["suffix"], ".png")

    def test_empty_captures_raise(self):
        with self.assertRaises(ValueError):
            run_photo_intake({})


class PhotoIntakeCliTests(unittest.TestCase):
    def test_cli_writes_json_out(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            captures = _full_captures(root)
            argv: list[str] = []
            for bin_id, path in captures.items():
                argv += ["--capture", f"{bin_id}={path}"]
            out = root / "report.json"
            argv += ["--session-id", "PHOTO-CLI-1", "--out", str(out)]
            self.assertEqual(main(argv), 0)
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(payload["session_id"], "PHOTO-CLI-1")
            self.assertEqual(payload["capture_source"], "file")
            self.assertEqual(payload["summary"]["counted_bins"], 6)

    def test_cli_rejects_bad_capture_format(self):
        with self.assertRaises(SystemExit):
            main(["--capture", "no-equals-sign"])


if __name__ == "__main__":
    unittest.main()
