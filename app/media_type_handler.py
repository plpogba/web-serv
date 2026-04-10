from abc import ABC, abstractmethod
from typing import Type

# ─────────────────────────────────────────
#  추상 및 구체 핸들러
# ─────────────────────────────────────────

class MediaTypeHandler(ABC):
    @property
    @abstractmethod
    def value(self) -> str: ...

    @property
    def discover_path(self) -> str: return f"/discover/{self.value}"
    @property
    def detail_path_prefix(self) -> str: return f"/{self.value}"
    @property
    def genre_path(self) -> str: return f"/genre/{self.value}/list"
    @property
    def provider_path_suffix(self) -> str: return "/watch/providers"

class MovieHandler(MediaTypeHandler):
    @property
    def value(self) -> str: return "movie"

class TvHandler(MediaTypeHandler):
    @property
    def value(self) -> str: return "tv"


# ─────────────────────────────────────────
#  Registry (투트랙 방어 아키텍처)
# ─────────────────────────────────────────

# 1. 내부 로직용 격리 저장소 (Hidden Source of Truth)
# 테스트나 외부에서 접근할 수 없는 진짜 데이터입니다.
# 인스턴스 오염을 막기 위해 '클래스(Type)' 자체를 저장합니다.
_INTERNAL_REGISTRY: dict[str, Type[MediaTypeHandler]] = {
    "movie": MovieHandler,
    "tv": TvHandler,
}

# 2. 외부 노출용 더미 딕셔너리 (Decoy)
# 테스트 코드의 ImportError 방지 및 하위 호환성을 위해 제공합니다.
# 외부에서 이 딕셔너리를 pop() 하거나 새 값을 할당해도 내부 로직에는 영향이 없습니다.
_HANDLERS = {
    "movie": MovieHandler(),
    "tv": TvHandler(),
}
HANDLERS = _HANDLERS


def get_handler(media_type: str) -> MediaTypeHandler:
    """
    입력값을 정규화하여 핸들러 인스턴스를 반환합니다.
    """
    sanitized = media_type.strip().lower() if media_type else ""

    # 조작 가능한 _HANDLERS 대신, 안전한 _INTERNAL_REGISTRY를 참조합니다.
    handler_class = _INTERNAL_REGISTRY.get(sanitized)
    
    if handler_class is None:
        supported = ", ".join(sorted(_INTERNAL_REGISTRY.keys()))
        raise ValueError(
            f"지원하지 않는 media_type: '{media_type}'. "
            f"지원 타입: [{supported}]"
        )
    
    # 클래스를 인스턴스화하여 매번 '새로운 객체'를 반환합니다. (Factory 패턴)
    return handler_class()


def is_valid(media_type: str) -> bool:
    sanitized = media_type.strip().lower() if media_type else ""
    return sanitized in _INTERNAL_REGISTRY

def supported_types() -> tuple[str, ...]:
    return tuple(_INTERNAL_REGISTRY.keys())