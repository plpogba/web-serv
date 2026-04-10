import pytest
from app.review_repository import ReviewRepository, ContentKey

@pytest.fixture
def repo():
    return ReviewRepository()

def test_content_key_valid():
    key = ContentKey("movie", 123)
    assert key.media_type == "movie"
    assert key.content_id == 123
    assert key.to_key() == "movie_123"

def test_content_key_invalid_media_type():
    with pytest.raises(ValueError, match="Invalid media_type"):
        ContentKey("anime", 123)

def test_review_repository_get_empty(repo):
    key = ContentKey("movie", 123)
    assert repo.get(key) == []

def test_review_repository_add_and_get(repo):
    key = ContentKey("tv", 456)
    review = {"author": "Test", "text": "Good", "rating": 4.0}
    added = repo.add(key, review)
    assert added["id"] == 1
    assert repo.get(key) == [added]

def test_review_repository_delete_existing(repo):
    key = ContentKey("movie", 789)
    review = {"author": "Test", "text": "Good", "rating": 4.0}
    repo.add(key, review)
    assert repo.delete(key, 1) is True
    assert repo.get(key) == []

def test_review_repository_delete_non_existing(repo):
    key = ContentKey("tv", 101)
    assert repo.delete(key, 999) is False

def test_content_key_immutable():
    key = ContentKey("movie", 123)
    with pytest.raises(AttributeError):
        key.media_type = "tv"  # frozen dataclass