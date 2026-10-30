"""SAM 계수 어댑터 경계.

계수는 이 인터페이스 뒤에서만 일어난다. 실호출 규격은 2026-10-30에
Meta Model API(api.meta.ai) 실호출 탐침으로 검증했다: POST
/v1/responses에 model "sam-3.1"과 input_image 콘텐츠를 보내면
output_text 안에 검출 1건마다 박스·마스크 마커 쌍이 반복돼 돌아온다.
이 프로젝트의 환경변수(SAM_API_BASE_URL·SAM_API_KEY)는 아직 이 환경에
없으므로, 환경변수가 갖춰지기 전까지 기본 동작은 모의 어댑터다.
탐침은 커넥터 경유로 했고, 이 모듈 자체는 키를 어디에도 기록하지 않는다.

규격에 의존하는 부분은 build_payload와 parse_response 두 지점에
격리돼 있다. 모듈을 불러오거나 어댑터를 만드는 것만으로는 네트워크를
쓰지 않는다.
"""
from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Protocol

from .models import CountResult

MODEL_ID = "sam-3.1"
# SAM 3의 개념 프롬프트는 명사구다. 무엇을 셀지는 이 상수 한 곳에서 정한다.
COUNT_PROMPT = "cardboard box"


class SamCountingError(Exception):
    """실호출 계수 실패. 전송 오류와 응답 해석 실패를 이 예외로만 모은다."""


class SamCounter(Protocol):
    source: str  # 결과에 찍히는 출처 표기 ("mock" / "sam")

    def count(self, bin_id: str, image_ref: str | None = None) -> CountResult:
        """빈 사진(image_ref)에서 품목 수를 세어 결과를 돌려준다."""
        ...


_IMAGE_MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
               ".webp": "image/webp"}


def _image_url(image_ref: str) -> str:
    """이미지 참조를 API의 image_url 값으로 바꾼다.

    로컬 파일이 실존하면 바이트를 읽어 data URI로 넣는다(탐침으로 검증한
    전송 방식). 실존하지 않는 문자열은 URL이나 테스트 참조로 보고 그대로
    넣는다. 회사 자료가 아닌 호출자가 건넨 이미지만 다룬다.
    """
    if os.path.isfile(image_ref):
        mime = _IMAGE_MIME.get(os.path.splitext(image_ref)[1].lower(),
                               "application/octet-stream")
        with open(image_ref, "rb") as handle:
            encoded = base64.b64encode(handle.read()).decode("ascii")
        return f"data:{mime};base64,{encoded}"
    return image_ref


def build_payload(bin_id: str, image_ref: str | None = None) -> dict:
    """요청 본문을 만든다. 규격 의존 지점 중 하나다.

    2026-10-30 실측 규격(responses 형식): 본문은 model과 input만으로
    구성하고, input은 input_text(개념 프롬프트)와 input_image를 담은
    user 메시지 하나다. 이미지가 없으면 서버가 400으로 거부하므로
    여기서 먼저 SamCountingError로 막는다. bin_id는 본문에 넣지
    않는다. API 키는 본문에 넣지 않는다 — 키는 Authorization
    헤더로만 보낸다.
    """
    if not image_ref:
        raise SamCountingError(
            "SAM 계수에는 이미지가 필요합니다 (input_image 필수)."
        )
    return {
        "model": MODEL_ID,
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": COUNT_PROMPT},
                    {"type": "input_image", "image_url": _image_url(image_ref)},
                ],
            }
        ],
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


def _count_from_responses_output(payload: dict) -> int | None:
    """responses 형식 output에서 검출 개수를 센다. 해당 없으면 None.

    2026-10-30 실측: output은 message 항목 리스트이고, 각 항목의
    content에서 type이 "output_text"인 text 안에 검출 1건마다
    "<|box;...|>"와 "<|mask;...|>" 마커 쌍이 반복된다. 계수는 box
    마커 개수이며, 검출이 없으면 text가 비어 있어 0이다. output_text
    자체가 없으면 이 규격의 응답이 아니므로 None을 돌려준다.
    """
    output = payload.get("output")
    if not isinstance(output, list):
        return None
    texts: list[str] = []
    for item in output:
        if not isinstance(item, dict):
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if isinstance(part, dict) and part.get("type") == "output_text":
                text = part.get("text")
                if isinstance(text, str):
                    texts.append(text)
    if not texts:
        return None
    joined = "".join(texts)
    boxes = joined.count("<|box;")
    if boxes:
        return boxes
    return joined.count("<|mask;")


def parse_response(payload: object) -> int:
    """응답 본문에서 수량을 꺼낸다. 규격 의존 지점 중 하나다.

    실측 규격(responses 형식의 output_text 안 박스 마커 개수)을 먼저
    보고, 종전 준비 단계 형태(최상위 수량 키, result나 output dict
    안의 수량 키, detections나 segments 리스트의 길이)도 계속
    지원한다 — 가짜 transport 검증이 그 형태를 쓰기 때문이다. 어느
    형태에도 맞지 않으면 SamCountingError를 던진다. 추측으로 숫자를
    만들지 않는다.
    """
    if not isinstance(payload, dict):
        raise SamCountingError("SAM 응답이 객체가 아닙니다.")
    found = _count_from_responses_output(payload)
    if found is not None:
        return found
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
    """SAM 실호출 계수기다. 규격은 2026-10-30 실호출 탐침으로 검증했다.

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
