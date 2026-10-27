"""데모 영상 제작 자산 패키지."""
from __future__ import annotations

__all__ = ["CUTS", "build_shot_list", "build_srt", "build_vtt"]


def __getattr__(name: str):
    # 지연 re-export: `python3 -m demo.captions` 실행 시 runpy 경고를 피한다.
    if name in __all__:
        from . import captions

        return getattr(captions, name)
    raise AttributeError(name)
