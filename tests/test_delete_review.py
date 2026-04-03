# UR-09 delete_review() 테스트
import pytest
import json
from app import app
from review_repository import ReviewRepository, ContentKey

@pytest.fixture
def client():
    app.config["TESTING"] = True
    repo = ReviewRepository()
    key = ContentKey("movie", 1)
    repo.add(key, {"author": "Test1", "text": "Good!", "rating": 5})
    repo.add(key, {"author": "Test2", "text": "Bad!", "rating": 2})
    with app.test_client() as c:
        yield c

def test_delete_review_success(client):
    """정상 삭제: 존재하는 리뷰 삭제 시 200 반환"""
    res = client.delete("/api/reviews/movie/1/1")
    assert res.status_code == 200
    data = json.loads(res.data)
    assert "deleted" in data["message"].lower() or "success" in data["message"].lower()

def test_delete_review_not_found(client):
    """존재하지 않는 리뷰 삭제: 404 반환"""
    res = client.delete("/api/reviews/999")
    assert res.status_code == 404

def test_delete_review_actually_removed(client):
    """삭제 후 실제로 REVIEWS에서 제거되었는지 확인"""
    client.delete("/api/reviews/1")
    remaining_ids = [r["id"] for r in REVIEWS]
    assert 1 not in remaining_ids

def test_delete_review_invalid_type(client):
    """문자열 review_id: Flask 라우팅 404 반환"""
    res = client.delete("/api/reviews/not-a-number")
    assert res.status_code == 404

def test_delete_review_idempotent(client):
    """이미 삭제된 리뷰 재삭제: 404 반환"""
    client.delete("/api/reviews/1")
    res = client.delete("/api/reviews/1")
    assert res.status_code == 404