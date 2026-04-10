import pytest
import json
from app.app import app
from app.review_repository import ReviewRepository, ContentKey

@pytest.fixture
def client():
    app.config["TESTING"] = True
    repo = ReviewRepository()
    key1 = ContentKey("movie", 1)
    key2 = ContentKey("movie", 2)
    repo.add(key1, {"author": "Test1", "text": "Good!", "rating": 5})
    repo.add(key1, {"author": "Test2", "text": "Bad!", "rating": 2})
    repo.add(key2, {"author": "Test3", "text": "Awesome!", "rating": 5})
    with app.test_client() as client:
        yield client

def test_get_movie_reviews_success(client):
    """정상 조회: 1번 영화의 리뷰 2개가 정확히 반환되는지 확인"""
    res = client.get("/api/reviews/movie/1")
    assert res.status_code == 200
    
    data = json.loads(res.data)
    
    # 1. 리스트의 길이를 먼저 확인 (리뷰가 2개여야 함)
    assert len(data) == 2
    
    # 2. 첫 번째 리뷰가 올바른 내용인지 확인
    assert data[0]["author"] == "Test1"

def test_get_movie_reviews_empty(client):
    """리뷰 없음: 리뷰가 없는 영화(예: 3번) 조회 시 빈 리스트 반환"""
    res = client.get("/api/movies/3/reviews")
    assert res.status_code == 200
    assert json.loads(res.data) == []

def test_get_movie_reviews_not_found_movie(client):
    """영화 존재 안함: DATABASE에 없는 영화 ID(예: 999) 조회 시 404 반환"""
    res = client.get("/api/movies/999/reviews")
    assert res.status_code == 404