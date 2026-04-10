from dataclasses import dataclass
from typing import Dict, List, Any

@dataclass(frozen=True)
class ContentKey:
    """Key class used to identify content.

    Attributes:
        media_type (str): Media type ("movie" or "tv").
        content_id (int): Content ID.
    """
    media_type: str
    content_id: int

    def __post_init__(self):
        """Performs validation of the media type.

        Raises:
            ValueError: If the media_type is invalid.
        """
        if self.media_type not in ("movie", "tv"):
            raise ValueError(f"Invalid media_type: {self.media_type}")

    def to_key(self) -> str:
        """Generates a string key.

        Returns:
            str: Key in the format "{media_type}_{content_id}".
        """
        return f"{self.media_type}_{self.content_id}"

class ReviewRepository:
    """Repository class that stores and manages review data in memory.

    Attributes:
        _store (Dict[str, List[Dict[str, Any]]]): Internal storage for review data.
    """
    def __init__(self):
        self._store: Dict[str, List[Dict[str, Any]]] = {}

    def get(self, key: ContentKey) -> List[Dict[str, Any]]:
        """Returns the list of reviews for a specific content.

        Args:
            key (ContentKey): Content key.

        Returns:
            List[Dict[str, Any]]: List of reviews.
        """
        return self._store.get(key.to_key(), [])

    def add(self, key: ContentKey, review: Dict[str, Any]) -> Dict[str, Any]:
        """Adds a new review to the content.

        Args:
            key (ContentKey): Content key.
            review (Dict[str, Any]): Review data.

        Returns:
            Dict[str, Any]: The added review (including an assigned ID).
        """
        store_key = key.to_key()
        self._store.setdefault(store_key, [])
        # Assign ID based on current list length + 1
        review["id"] = len(self._store[store_key]) + 1
        self._store[store_key].append(review)
        return review

    def delete(self, key: ContentKey, review_id: int) -> bool:
        """Deletes a specific review from the content.

        Args:
            key (ContentKey): Content key.
            review_id (int): ID of the review to delete.

        Returns:
            bool: True if deletion was successful, False otherwise.
        """
        store_key = key.to_key()
        for i, r in enumerate(self._store.get(store_key, [])):
            if r["id"] == review_id:
                self._store[store_key].pop(i)
                return True
        return False