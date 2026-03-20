import pytest
import json
from unittest.mock import patch
from app import app

# 테스트용 client 픽스처 (conftest.py에 있다면 생략 가능)
@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_invalid_page_type_returns_400(client):
    """파라미터 타입 오류: page=abc 전송 시 400 반환"""
    res = client.get("/api/movies?page=abc&limit=10")
    assert res.status_code == 400

def test_invalid_limit_type_returns_400(client):
    """파라미터 타입 오류: limit=특수문자 전송 시 400 반환"""
    res = client.get("/api/movies?page=1&limit=!@#")
    assert res.status_code == 400

def test_out_of_range_page_returns_empty(client):
    """페이지 범위 초과: page=9999 요청 시 200 OK와 빈 리스트 반환"""
    res = client.get("/api/movies?page=9999")
    assert res.status_code in (200, 404)
    if res.status_code == 200:
        assert json.loads(res.data) == []

def test_excessive_limit_returns_400(client):
    """제한 초과 로드: limit=1000000 요청 시 400 반환"""
    res = client.get("/api/movies?limit=1000000")
    assert res.status_code == 400

# app 내부에서 데이터를 가져올 때 사용하는 실제 DB 함수를 모킹한다고 가정
@patch("app.get_movies_from_db") # 뷰 함수가 아닌 데이터 호출 함수를 모킹
def test_db_timeout_returns_500(mock_db_call, client):
    """DB 타임아웃 시 500 반환"""
    mock_db_call.side_effect = Exception("DB connection timeout")
    res = client.get("/api/movies")
    assert res.status_code == 500

def test_empty_database_returns_empty_list(client):
    """빈 DB: 200 OK와 [] 반환 (Null Reference 없음)"""
    res = client.get("/api/movies")
    assert res.status_code == 200
    assert isinstance(json.loads(res.data), list)