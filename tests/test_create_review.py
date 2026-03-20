import pytest
import json
from app import app

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_create_review_success(client):
    """정상 등록: 올바른 데이터를 보냈을 때 201 Created 반환"""
    payload = {
        "movie_id": 1,
        "content": "정말 감동적인 영화였습니다!",
        "rating": 5
    }
    # JSON 데이터를 전송할 때는 data와 content_type을 명시합니다.
    res = client.post("/api/reviews", 
                      data=json.dumps(payload), 
                      content_type='application/json')
    
    assert res.status_code == 201
    data = json.loads(res.data)
    assert data["message"] == "Review created successfully"

def test_create_review_missing_fields(client):
    """필드 누락: 필수 데이터(rating)가 없을 때 400 반환"""
    payload = {
        "movie_id": 1,
        "content": "내용만 있고 별점이 없어요."
    }
    res = client.post("/api/reviews", 
                      data=json.dumps(payload), 
                      content_type='application/json')
    assert res.status_code == 400

def test_create_review_invalid_rating(client):
    """범위 초과: 별점이 1~5 사이가 아닐 때 400 반환"""
    payload = {
        "movie_id": 1,
        "content": "별점 10점 드립니다!",
        "rating": 10  # 잘못된 범위
    }
    res = client.post("/api/reviews", 
                      data=json.dumps(payload), 
                      content_type='application/json')
    assert res.status_code == 400