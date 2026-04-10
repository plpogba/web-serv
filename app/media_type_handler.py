from abc import ABC, abstractmethod
from typing import Type

# ─────────────────────────────────────────
#  Abstract and Concrete Handlers
# ─────────────────────────────────────────

class MediaTypeHandler(ABC):
    """Abstract base class for media type handlers.

    This class defines the interface for handling different media types 
    such as movies and TV shows.
    """
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
    """Handler class for processing 'movie' media types.
    """
    @property
    def value(self) -> str: return "movie"

class TvHandler(MediaTypeHandler):
    """Handler class for processing 'tv' media types.
    """
    @property
    def value(self) -> str: return "tv"


# ─────────────────────────────────────────
#  Registry (Two-Track Defense Architecture)
# ─────────────────────────────────────────

# 1. Isolated Storage for Internal Logic (Hidden Source of Truth)
# This represents the actual data that is inaccessible to tests or external code.
# Stores the 'Class (Type)' itself to prevent instance contamination.
_INTERNAL_REGISTRY: dict[str, Type[MediaTypeHandler]] = {
    "movie": MovieHandler,
    "tv": TvHandler,
}

# 2. Exposed Decoy Dictionary
# Provided to prevent ImportErrors in test code and maintain backward compatibility.
# External modifications (e.g., pop() or new assignments) will not affect internal logic.
_HANDLERS = {
    "movie": MovieHandler(),
    "tv": TvHandler(),
}
HANDLERS = _HANDLERS


def get_handler(media_type: str) -> MediaTypeHandler:
    """Normalizes the input and returns a handler instance.

    Args:
        media_type (str): The media type string.

    Returns:
        MediaTypeHandler: A handler instance for the corresponding media type.

    Raises:
        ValueError: If the media_type is not supported.
    """
    sanitized = media_type.strip().lower() if media_type else ""

    # Reference the secure _INTERNAL_REGISTRY instead of the manipulatable _HANDLERS.
    handler_class = _INTERNAL_REGISTRY.get(sanitized)
    
    if handler_class is None:
        supported = ", ".join(sorted(_INTERNAL_REGISTRY.keys()))
        raise ValueError(
            f"Unsupported media_type: '{media_type}'. "
            f"Supported types: [{supported}]"
        )
    
    # Instantiate the class to return a 'fresh object' every time (Factory Pattern).
    return handler_class()


def is_valid(media_type: str) -> bool:
    """Checks if the media type is valid.

    Args:
        media_type (str): The media type to check.

    Returns:
        bool: True if valid, False otherwise.
    """
    sanitized = media_type.strip().lower() if media_type else ""
    return sanitized in _INTERNAL_REGISTRY

def supported_types() -> tuple[str, ...]:
    """Returns a list of supported media types.

    Returns:
        tuple[str, ...]: A tuple of supported media type strings.
    """
    return tuple(_INTERNAL_REGISTRY.keys())