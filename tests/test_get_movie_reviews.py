import pytest
import json
from app import app, REVIEWS

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        # 테스트 시작 전 리뷰 데이터 초기화
        REVIEWS.clear()
        REVIEWS.append({"id": 1, "movie_id": 1, "content": "Good!", "rating": 5})
        REVIEWS.append({"id": 2, "movie_id": 1, "content": "Bad!", "rating": 2})
        REVIEWS.append({"id": 3, "movie_id": 2, "content": "Awesome!", "rating": 5})
        yield client

def test_get_movie_reviews_success(client):
    """정상 조회: 1번 영화의 리뷰 2개가 정확히 반환되는지 확인"""
    res = client.get("/api/movies/1/reviews")
    assert res.status_code == 200
    
    data = json.loads(res.data)
    
    # 1. 리스트의 길이를 먼저 확인 (리뷰가 2개여야 함)
    assert len(data) == 2
    
    # 2. 첫 번째 리뷰()가 1번 영화의 것인지 확인
    assert data[0]["movie_id"] == 1  # <---을 꼭 추가해 주세요!

def test_get_movie_reviews_empty(client):
    """리뷰 없음: 리뷰가 없는 영화(예: 3번) 조회 시 빈 리스트 반환"""
    res = client.get("/api/movies/3/reviews")
    assert res.status_code == 200
    assert json.loads(res.data) == []

def test_get_movie_reviews_not_found_movie(client):
    """영화 존재 안함: DATABASE에 없는 영화 ID(예: 999) 조회 시 404 반환"""
    res = client.get("/api/movies/999/reviews")
    assert res.status_code == 404