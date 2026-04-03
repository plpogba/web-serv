class ReviewRepository:
    def __init__(self):
        self._store: dict = {}

    def _key(self, media_type: str, content_id: int) -> str:
        return f"{media_type}_{content_id}"

    def get(self, media_type: str, content_id: int) -> list:
        return self._store.get(self._key(media_type, content_id), [])

    def add(self, media_type: str, content_id: int, review: dict) -> dict:
        key = self._key(media_type, content_id)
        self._store.setdefault(key, [])
        review["id"] = len(self._store[key]) + 1
        self._store[key].append(review)
        return review

    def delete(self, media_type: str, content_id: int, review_id: int) -> bool:
        key = self._key(media_type, content_id)
        for i, r in enumerate(self._store.get(key, [])):
            if r["id"] == review_id:
                self._store[key].pop(i)
                return True
        return False