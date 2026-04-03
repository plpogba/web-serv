from dataclasses import dataclass
from typing import Dict, List, Any

@dataclass(frozen=True)
class ContentKey:
    media_type: str
    content_id: int

    def __post_init__(self):
        if self.media_type not in ("movie", "tv"):
            raise ValueError(f"Invalid media_type: {self.media_type}")

    def to_key(self) -> str:
        return f"{self.media_type}_{self.content_id}"

class ReviewRepository:
    def __init__(self):
        self._store: Dict[str, List[Dict[str, Any]]] = {}

    def get(self, key: ContentKey) -> List[Dict[str, Any]]:
        return self._store.get(key.to_key(), [])

    def add(self, key: ContentKey, review: Dict[str, Any]) -> Dict[str, Any]:
        store_key = key.to_key()
        self._store.setdefault(store_key, [])
        review["id"] = len(self._store[store_key]) + 1
        self._store[store_key].append(review)
        return review

    def delete(self, key: ContentKey, review_id: int) -> bool:
        store_key = key.to_key()
        for i, r in enumerate(self._store.get(store_key, [])):
            if r["id"] == review_id:
                self._store[store_key].pop(i)
                return True
        return False