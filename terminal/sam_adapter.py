"""SAM 계수 어댑터 경계.

계수는 이 인터페이스 뒤에서만 일어난다. 실호출 경로는 코드로 준비됐으나
아직 실제 API로 검증되지 않았다. 공식 규격을 확인하고 크레딧 입금을
확인한 뒤에만 실사용한다. 그 전까지 기본 동작은 모의 어댑터다.

규격에 의존하는 부분은 build_payload와 parse_response 두 지점에
격리돼 있다. 규격이 확정되면 이 두 함수만 고친다. 모듈을 불러오거나
어댑터를 만드는 것만으로는 네트워크를 쓰지 않는다.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Protocol

from .models import CountResult

MODEL_ID = "sam-3.1"
COUNT_PROMPT = "warehouse bin 안의 박스와 팔레트를 세어 주세요"


class SamCountingError(Exception):
    """실호출 계수 실패. 전송 오류와 응답 해석 실패를 이 예외로만 모은다."""


class SamCounter(Protocol):
    source: str  # 결과에 찍히는 출처 표기 ("mock" / "sam")

    def count(self, bin_id: str, image_ref: str | None = None) -> CountResult:
        """빈 사진(image_ref)에서 품목 수를 세어 결과를 돌려준다."""
        ...


def build_payload(bin_id: str, image_ref: str | None = None) -> dict:
    """요청 본문을 만든다. 규격 의존 지점 중 하나다.

    API 키는 본문에 넣지 않는다. 키는 Authorization 헤더로만 보낸다.
    """
    return {
        "model": MODEL_ID,
        "bin_id": bin_id,
        "image_ref": image_ref,
        "prompt": COUNT_PROMPT,
    }


_COUNT_KEYS = ("counted_qty", "count", "quantity")
_CONTAINER_KEYS = ("result", "output")
_LIST_KEYS = ("detections", "segments")


def _checked_count(value: object) -> int:
    # bool은 int의 하위형이라 먼저 걸러야 한다. True를 1로 세면 안 된다.
    if isinstance(value, bool) or not isinstance(value, int):
        raise SamCountingError("SAM 응답의 수량이 정수가 아닙니다.")
    if value < 0:
        raise SamCountingError("SAM 응답의 수량이 음수입니다.")
    return value


def _extract_count(container: dict) -> int | None:
    """한 단계 dict에서 수량을 찾는다. 키가 없으면 None을 돌려준다."""
    for key in _COUNT_KEYS:
        if key in container:
            return _checked_count(container[key])
    for key in _LIST_KEYS:
        if key in container:
            items = container[key]
            if not isinstance(items, list):
                raise SamCountingError("SAM 응답의 검출 결과가 리스트가 아닙니다.")
            return len(items)
    return None


def parse_response(payload: object) -> int:
    """응답 본문에서 수량을 꺼낸다. 규격 의존 지점 중 하나다.

    지원하는 형태는 세 가지다. 최상위 수량 키, result나 output 안의
    수량 키, detections나 segments 리스트의 길이다. 형태가 다르면
    SamCountingError를 던진다. 추측으로 숫자를 만들지 않는다.
    """
    if not isinstance(payload, dict):
        raise SamCountingError("SAM 응답이 객체가 아닙니다.")
    found = _extract_count(payload)
    if found is not None:
        return found
    for key in _CONTAINER_KEYS:
        nested = payload.get(key)
        if isinstance(nested, dict):
            found = _extract_count(nested)
            if found is not None:
                return found
    raise SamCountingError("SAM 응답에서 수량을 찾을 수 없습니다.")


def _default_transport(
    url: str, headers: dict, body: bytes, timeout: float
) -> tuple[int, dict]:
    """urllib로 POST하는 기본 전송이다.

    이 함수는 LiveSamCounter.count가 부를 때만 실행된다. HTTP 오류
    상태는 예외로 바꾸지 않고 상태 코드로 돌려준다. 호출자가 상태
    검사를 한 곳에서 하게 하기 위해서다.
    """
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.status
            raw = response.read()
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            parsed = json.loads(raw.decode("utf-8")) if raw else {}
        except (UnicodeDecodeError, json.JSONDecodeError):
            parsed = {}
        return exc.code, parsed if isinstance(parsed, dict) else {}
    parsed = json.loads(raw.decode("utf-8"))
    return status, parsed if isinstance(parsed, dict) else {}


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
    """SAM 실호출 계수기다. 코드는 준비됐으나 실제 API로 검증되지 않았다.

    실패하면 SamCountingError를 던진다. 모의 결과로 조용히 대체하지
    않는다. 잘못된 숫자를 그럴듯한 숫자로 바꾸면 재고 대조가 거짓으로
    통과하기 때문이다.
    """

    source = "sam"

    def __init__(
        self,
        base_url: str,
        api_key: str,
        transport: Callable[[str, dict, bytes, float], tuple[int, dict]] | None = None,
        timeout: float = 30,
    ) -> None:
        # base_url 자체를 엔드포인트로 본다. 규격 확인 전이라 경로를
        # 추측해서 덧붙이지 않는다. 끝의 슬래시만 정리한다.
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._transport = transport if transport is not None else _default_transport
        self._timeout = timeout

    def count(self, bin_id: str, image_ref: str | None = None) -> CountResult:
        body = json.dumps(build_payload(bin_id, image_ref)).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        try:
            status, data = self._transport(self._base_url, headers, body, self._timeout)
        except Exception as exc:
            # 원본 예외 문구를 메시지에 복사하지 않는다. 전송 계층
            # 메시지에 키가 섞여 들어갈 수 있기 때문이다.
            raise SamCountingError(
                f"SAM 계수 요청 중 전송 오류가 발생했습니다 (bin={bin_id})."
            ) from exc
        if status != 200:
            raise SamCountingError(
                f"SAM 계수 요청이 실패했습니다 (HTTP {status}, bin={bin_id})."
            )
        return CountResult(bin_id=bin_id, counted_qty=parse_response(data), source="sam")


def build_counter(demo_counts: dict[str, int]) -> SamCounter:
    """환경변수가 갖춰졌으면 실호출, 아니면 모의 어댑터를 돌려준다."""
    base_url = os.environ.get("SAM_API_BASE_URL")
    api_key = os.environ.get("SAM_API_KEY")
    if base_url and api_key:
        return LiveSamCounter(base_url=base_url, api_key=api_key)
    return MockSamCounter(demo_counts)
