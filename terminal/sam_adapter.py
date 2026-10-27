"""SAM 계수 어댑터 경계.

계수는 이 인터페이스 뒤에서만 일어난다. 지금은 모의 어댑터만 구현돼 있고,
실호출 어댑터는 환경변수(SAM_API_BASE_URL, SAM_API_KEY)가 모두 있을 때만
선택되는 자리만 마련돼 있다. 키가 없으면 항상 모의로 동작한다.
"""
from __future__ import annotations

import os
from typing import Protocol

from .models import CountResult


class SamCounter(Protocol):
    source: str  # 결과에 찍히는 출처 표기 ("mock" / "sam")

    def count(self, bin_id: str, image_ref: str | None = None) -> CountResult:
        """빈 사진(image_ref)에서 품목 수를 세어 결과를 돌려준다."""
        ...


class MockSamCounter:
    """데모 데이터 기반 모의 계수기. 실호출이 붙기 전까지의 개발용."""

    source = "mock"

    def __init__(self, demo_counts: dict[str, int]) -> None:
        self._demo_counts = dict(demo_counts)

    def count(self, bin_id: str, image_ref: str | None = None) -> CountResult:
        if bin_id not in self._demo_counts:
            raise KeyError(f"no demo count prepared for bin {bin_id}")
        return CountResult(
            bin_id=bin_id,
            counted_qty=self._demo_counts[bin_id],
            source=self.source,
        )


class LiveSamCounter:
    """Meta Model API 실호출 자리. 크레딧 입금 확인 뒤에 구현한다."""

    source = "sam"

    def __init__(self, base_url: str, api_key: str) -> None:
        self._base_url = base_url
        self._api_key = api_key

    def count(self, bin_id: str, image_ref: str | None = None) -> CountResult:
        raise NotImplementedError(
            "live SAM counting is wired after credit deposit is confirmed"
        )


def build_counter(demo_counts: dict[str, int]) -> SamCounter:
    """환경변수가 갖춰졌으면 실호출, 아니면 모의 어댑터를 돌려준다."""
    base_url = os.environ.get("SAM_API_BASE_URL")
    api_key = os.environ.get("SAM_API_KEY")
    if base_url and api_key:
        return LiveSamCounter(base_url=base_url, api_key=api_key)
    return MockSamCounter(demo_counts)
