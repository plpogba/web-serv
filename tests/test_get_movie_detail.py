#get_movie_detail test
import pytest
import json
from unittest.mock import patch
from app.app import app

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_get_movie_detail_success(client):
    """정상 조회: 존재하는 ID 요청 시 200과 영화 정보 반환"""
    res = client.get("/api/movies/1")
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["id"] == 1
    assert "title" in data

def test_get_movie_detail_not_found(client):
    """존재하지 않는 ID: 404 반환"""
    # 999번 영화가 없다고 가정
    res = client.get("/api/movies/999")
    assert res.status_code == 404

def test_get_movie_detail_invalid_type(client):
    """잘못된 타입: 숫자가 아닌 ID 요청 시 404(Flask 라우팅) 반환"""
    res = client.get("/api/movies/not-number")
    assert res.status_code == 404

@patch("app.get_movies_from_db")
def test_get_movie_detail_db_error(mock_db, client):
    """서버 에러: DB 조회 중 예외 발생 시 500 반환"""
    mock_db.side_effect = Exception("Database connection failed")
    res = client.get("/api/movies/1")
    assert res.status_code == 500

def test_get_movie_detail_structure(client):
    """데이터 구조 검증: 필수 키값이 모두 포함되어 있는지 확인"""
    res = client.get("/api/movies/1")
    data = json.loads(res.data)
    required_keys = ["id", "title", "description", "rating"]
    for key in required_keys:
        assert key in data