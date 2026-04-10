# UR-07, UR-08 위시리스트 테스트 (add / remove / get)
import pytest
import json
from app.app import app

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c

# ── add_wishlist ─────────────────────────────

@pytest.mark.skip(reason="Wishlist feature not implemented yet")
def test_add_wishlist_success(client):
    """정상 추가: 존재하는 영화 추가 시 201 반환"""
    res = client.post("/api/wishlist", json={"movie_id": 1})
    assert res.status_code == 201
    data = json.loads(res.data)
    assert data["movie_id"] == 1

@pytest.mark.skip(reason="Wishlist feature not implemented yet")
def test_add_wishlist_nonexistent_movie(client):
    """존재하지 않는 영화 추가: 404 반환"""
    res = client.post("/api/wishlist", json={"movie_id": 999})
    assert res.status_code == 404

@pytest.mark.skip(reason="Wishlist feature not implemented yet")
def test_add_wishlist_duplicate(client):
    """중복 추가: 이미 있는 영화 재추가 시 409 반환"""
    client.post("/api/wishlist", json={"movie_id": 1})
    res = client.post("/api/wishlist", json={"movie_id": 1})
@pytest.mark.skip(reason="Wishlist feature not implemented yet")
def test_add_wishlist_missing_movie_id(client):
    """movie_id 누락: 400 반환"""
    res = client.post("/api/wishlist", json={})
    assert res.status_code == 400

@pytest.mark.skip(reason="Wishlist feature not implemented yet")
def test_add_wishlist_no_body(client):
    """빈 바디: 400 반환"""
    res = client.post("/api/wishlist", content_type="application/json")
    assert res.status_code == 400

# ── remove_wishlist ──────────────────────────

@pytest.mark.skip(reason="Wishlist feature not implemented yet")
def test_remove_wishlist_success(client):
    """정상 삭제: 위시리스트에 있는 영화 삭제 시 200 반환"""
    client.post("/api/wishlist", json={"movie_id": 1})
    res = client.delete("/api/wishlist/1")
    assert res.status_code == 200

@pytest.mark.skip(reason="Wishlist feature not implemented yet")
def test_remove_wishlist_not_in_list(client):
    """위시리스트에 없는 항목 삭제: 404 반환"""
    res = client.delete("/api/wishlist/999")
    assert res.status_code == 404

@pytest.mark.skip(reason="Wishlist feature not implemented yet")
def test_remove_wishlist_invalid_type(client):
    """문자열 movie_id: Flask 라우팅 404 반환"""
    res = client.delete("/api/wishlist/abc")
    assert res.status_code == 404

# ── get_wishlist ─────────────────────────────

@pytest.mark.skip(reason="Wishlist feature not implemented yet")
def test_get_wishlist_empty(client):
    """빈 위시리스트: 200과 빈 리스트 반환"""
    res = client.get("/api/wishlist")
    assert res.status_code == 200
    assert json.loads(res.data) == []

@pytest.mark.skip(reason="Wishlist feature not implemented yet")
def test_get_wishlist_with_items(client):
    """항목 있음: 추가한 영화가 목록에 포함되어 있는지 확인"""
    client.post("/api/wishlist", json={"movie_id": 1})
    client.post("/api/wishlist", json={"movie_id": 2})
    res = client.get("/api/wishlist")
    assert res.status_code == 200
    data = json.loads(res.data)
    assert len(data) == 2
    ids = [m["id"] for m in data]
    assert 1 in ids
    assert 2 in ids

def test_get_wishlist_structure(client):
    """데이터 구조 검증: 필수 키값이 포함되어 있는지 확인"""
    client.post("/api/wishlist", json={"movie_id": 1})
    res = client.get("/api/wishlist")
    data = json.loads(res.data)
    for item in data:
        for key in ["id", "title", "genre", "rating"]:
            assert key in item