# search_movies() 함수 test

import pytest
import json
from unittest.mock import patch
from app.app import app

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_search_movies_success(client):
    res = client.get("/api/movies/search?q=Movie 1")
    assert res.status_code == 200

    data = json.loads(res.data)

    assert isinstance(data, list)
    assert len(data) > 0

    # ✅ 인덱스 [0]으로 첫 번째 요소(딕셔너리)에 접근 후 키 사용
    assert "Movie 1" in data[0]["title"]

def test_search_movies_no_keyword_returns_400(client):
    """키워드 누락: q 파라미터가 없을 때 400 반환"""
    res = client.get("/api/movies/search")
    assert res.status_code == 400

def test_search_movies_no_results(client):
    """결과 없음: 일치하는 영화가 없을 때 200과 빈 리스트 반환"""
    res = client.get("/api/movies/search?q=NonExistentMovie")
    assert res.status_code == 200
    assert json.loads(res.data) == []

def test_search_movies_case_insensitive(client):
    """대소문자 무시: 소문자 'movie'로 검색해도 결과가 나와야 함"""
    res = client.get("/api/movies/search?q=movie")
    assert res.status_code == 200
    data = json.loads(res.data)
    assert len(data) > 0

@patch("app.search_movies_from_db")
def test_search_db_error_returns_500(mock_search, client):
    """서버 에러: 검색 로직 중 예외 발생 시 500 반환"""
    mock_search.side_effect = Exception("Search engine failure")
    res = client.get("/api/movies/search?q=test")
    assert res.status_code == 500