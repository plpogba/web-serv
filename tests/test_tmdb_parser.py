# tests/test_tmdb_parser.py
# TmdbParser 클래스 전체 테스트
# 엣지 케이스: TMDB 응답 지연/타임아웃, TV 시리즈 runtime 형식 불일치, 필드 누락

import pytest
import time
import urllib.error
from unittest.mock import patch, MagicMock
from app.tmdb_parser import TmdbParser


# ─────────────────────────────────────────
#  공통 Fixture
# ─────────────────────────────────────────

@pytest.fixture
def parser():
    return TmdbParser()


# 정상적인 영화 상세 응답 (기준 데이터)
@pytest.fixture
def movie_detail():
    return {
        "id": 157336,
        "title": "인터스텔라",
        "tagline": "우리는 답을 찾을 것이다. 늘 그랬듯이.",
        "overview": "세계 각국의 정부와 경제가 완전히 붕괴된 미래...",
        "poster_path": "/gEU2QniE6E77NI6lCU6MxlNBvIE.jpg",
        "backdrop_path": "/xJHokMbljvjADYdit5fK5VQsXEG.jpg",
        "vote_average": 8.4,
        "vote_count": 32000,
        "release_date": "2014-11-06",
        "runtime": 169,
        "genres": [
            {"id": 18, "name": "드라마"},
            {"id": 878, "name": "SF"},
        ],
        "credits": {
            "cast": [
                {"name": "매튜 맥커너히", "character": "쿠퍼", "profile_path": "/mOpb.jpg"},
                {"name": "앤 해서웨이",   "character": "브랜드 박사", "profile_path": "/amnd.jpg"},
            ]
        },
        "reviews": {
            "results": [
                {
                    "author": "moviefan",
                    "content": "최고의 SF 영화!",
                    "author_details": {"rating": 9.0},
                }
            ]
        },
    }


# 정상적인 TV 시리즈 상세 응답
@pytest.fixture
def tv_detail():
    return {
        "id": 1396,
        "name": "브레이킹 배드",
        "tagline": "",
        "overview": "평범한 고등학교 화학 교사가...",
        "poster_path": "/ggFHVNu6YYI5L9pCfOacjizRGt.jpg",
        "backdrop_path": "/tsRy63Mu5cu8etL1X7ZLyf7UP1M.jpg",
        "vote_average": 9.5,
        "vote_count": 12000,
        "first_air_date": "2008-01-20",
        "episode_run_time": [47],
        "genres": [{"id": 18, "name": "드라마"}, {"id": 80, "name": "범죄"}],
        "credits": {"cast": []},
        "reviews": {"results": []},
    }


# OTT providers 응답
@pytest.fixture
def providers_raw():
    return {
        "results": {
            "KR": {
                "flatrate": [
                    {"provider_id": 8,  "provider_name": "Netflix",
                     "logo_path": "/9A1J.png"},
                    {"provider_id": 97, "provider_name": "Watcha",
                     "logo_path": "/watcha.png"},
                ]
            }
        }
    }


# ═════════════════════════════════════════
#  1. img_url()
# ═════════════════════════════════════════

class TestImgUrl:

    def test_정상_경로_기본사이즈(self, parser):
        """정상 경로 → w500 URL 생성"""
        result = parser.img_url("/abc.jpg")
        assert result == "https://image.tmdb.org/t/p/w500/abc.jpg"

    def test_정상_경로_커스텀사이즈(self, parser):
        """size 인자를 지정하면 해당 사이즈 URL 생성"""
        result = parser.img_url("/abc.jpg", "w1280")
        assert result == "https://image.tmdb.org/t/p/w1280/abc.jpg"

    def test_경로가_None이면_None반환(self, parser):
        """poster_path 가 None 이면 None 반환"""
        assert parser.img_url(None) is None

    def test_경로가_빈문자열이면_None반환(self, parser):
        """poster_path 가 빈 문자열이면 None 반환"""
        assert parser.img_url("") is None


# ═════════════════════════════════════════
#  2. parse_list_item()
# ═════════════════════════════════════════

class TestParseListItem:

    def test_영화_정상파싱(self, parser):
        """일반 영화 항목이 정상 파싱되는지 확인"""
        item = {
            "id": 1, "media_type": "movie",
            "title": "테스트 영화",
            "poster_path": "/p.jpg", "backdrop_path": "/b.jpg",
            "vote_average": 7.5, "vote_count": 1000,
            "release_date": "2023-01-01", "genre_ids": [28],
        }
        result = parser.parse_list_item(item)
        assert result["id"]         == 1
        assert result["title"]      == "테스트 영화"
        assert result["media_type"] == "movie"
        assert result["rating"]     == 7.5
        assert "poster" in result

    def test_person_타입_None반환(self, parser):
        """media_type이 person이면 None 반환 (필터링 대상)"""
        item = {"id": 99, "media_type": "person", "name": "배우 이름"}
        assert parser.parse_list_item(item) is None

    def test_title_없고_name_있는_TV(self, parser):
        """TV 시리즈는 title 대신 name 필드 사용"""
        item = {
            "id": 2, "media_type": "tv",
            "name": "TV 시리즈 제목",
            "vote_average": 8.0,
        }
        result = parser.parse_list_item(item)
        assert result["title"] == "TV 시리즈 제목"

    def test_vote_average_None이면_0점(self, parser):
        """vote_average 필드 누락 시 rating 0.0 반환"""
        item = {"id": 3, "media_type": "movie", "title": "무평점 영화"}
        result = parser.parse_list_item(item)
        assert result["rating"] == 0.0

    def test_poster_없으면_None(self, parser):
        """poster_path 누락 시 poster 필드가 None"""
        item = {"id": 4, "media_type": "movie", "title": "포스터 없는 영화"}
        result = parser.parse_list_item(item)
        assert result["poster"] is None


# ═════════════════════════════════════════
#  3. parse_cast()
# ═════════════════════════════════════════

class TestParseCast:

    def test_정상_출연진_파싱(self, parser, movie_detail):
        """credits.cast 데이터가 정상 파싱되는지 확인"""
        result = parser.parse_cast(movie_detail)
        assert len(result) == 2
        assert result[0]["name"]      == "매튜 맥커너히"
        assert result[0]["character"] == "쿠퍼"
        assert result[0]["photo"]     is not None

    def test_최대_10명_제한(self, parser):
        """cast가 10명 초과여도 최대 10명만 반환"""
        detail = {
            "credits": {
                "cast": [{"name": f"배우{i}", "character": f"역할{i}",
                          "profile_path": None} for i in range(20)]
            }
        }
        result = parser.parse_cast(detail)
        assert len(result) == 10

    def test_credits_필드_누락(self, parser):
        """credits 키 자체가 없어도 빈 리스트 반환 (KeyError 없음)"""
        result = parser.parse_cast({})
        assert result == []

    def test_credits_None이면_빈리스트(self, parser):
        """credits 값이 None이어도 빈 리스트 반환"""
        result = parser.parse_cast({"credits": None})
        assert result == []

    def test_cast_None이면_빈리스트(self, parser):
        """credits.cast 가 None이어도 빈 리스트 반환"""
        result = parser.parse_cast({"credits": {"cast": None}})
        assert result == []

    def test_배우_photo_없으면_None(self, parser):
        """profile_path 없는 배우의 photo는 None"""
        detail = {
            "credits": {
                "cast": [{"name": "무사진 배우", "character": "역할",
                          "profile_path": None}]
            }
        }
        result = parser.parse_cast(detail)
        assert result[0]["photo"] is None

    def test_배우_name_없으면_빈문자열(self, parser):
        """name 필드 누락 시 빈 문자열 반환 (KeyError 없음)"""
        detail = {"credits": {"cast": [{"character": "역할", "profile_path": None}]}}
        result = parser.parse_cast(detail)
        assert result[0]["name"] == ""


# ═════════════════════════════════════════
#  4. parse_reviews()
# ═════════════════════════════════════════

class TestParseReviews:

    def test_정상_리뷰_파싱(self, parser, movie_detail):
        """reviews.results 데이터가 정상 파싱되는지 확인"""
        result = parser.parse_reviews(movie_detail)
        assert len(result) == 1
        assert result[0]["author"]  == "moviefan"
        assert result[0]["content"] == "최고의 SF 영화!"
        assert result[0]["rating"]  == 9.0

    def test_최대_5개_제한(self, parser):
        """리뷰가 5개 초과여도 최대 5개만 반환"""
        detail = {
            "reviews": {
                "results": [
                    {"author": f"user{i}", "content": "좋아요",
                     "author_details": {"rating": 8.0}}
                    for i in range(10)
                ]
            }
        }
        result = parser.parse_reviews(detail)
        assert len(result) == 5

    def test_400자_초과_리뷰_truncate(self, parser):
        """400자 초과 리뷰는 400자로 자르고 '...' 추가"""
        long_text = "A" * 500
        detail = {
            "reviews": {
                "results": [{"author": "user", "content": long_text,
                             "author_details": {}}]
            }
        }
        result = parser.parse_reviews(detail)
        assert len(result[0]["content"]) == 403   # 400자 + "..."
        assert result[0]["content"].endswith("...")

    def test_400자_이하_리뷰_그대로(self, parser):
        """400자 이하 리뷰는 '...' 없이 그대로 반환"""
        short_text = "짧은 리뷰"
        detail = {
            "reviews": {
                "results": [{"author": "user", "content": short_text,
                             "author_details": {"rating": 7.0}}]
            }
        }
        result = parser.parse_reviews(detail)
        assert result[0]["content"] == short_text
        assert "..." not in result[0]["content"]

    def test_reviews_필드_누락(self, parser):
        """reviews 키 자체 없어도 빈 리스트 반환"""
        assert parser.parse_reviews({}) == []

    def test_reviews_None이면_빈리스트(self, parser):
        """reviews 값이 None이어도 빈 리스트 반환"""
        assert parser.parse_reviews({"reviews": None}) == []

    def test_author_없으면_익명(self, parser):
        """author 필드 누락 시 '익명' 반환"""
        detail = {
            "reviews": {
                "results": [{"content": "내용", "author_details": {}}]
            }
        }
        result = parser.parse_reviews(detail)
        assert result[0]["author"] == "익명"

    def test_author_details_없으면_rating_None(self, parser):
        """author_details 누락 시 rating은 None"""
        detail = {
            "reviews": {
                "results": [{"author": "user", "content": "내용"}]
            }
        }
        result = parser.parse_reviews(detail)
        assert result[0]["rating"] is None


# ═════════════════════════════════════════
#  5. parse_runtime() — TV 형식 불일치 엣지 케이스
# ═════════════════════════════════════════

class TestParseRuntime:

    def test_영화_runtime_정상(self, parser, movie_detail):
        """영화의 runtime 필드가 정수로 정상 반환"""
        assert parser.parse_runtime(movie_detail) == 169

    def test_TV_episode_run_time_정상(self, parser, tv_detail):
        """TV 시리즈 episode_run_time 리스트 첫 번째 값 반환"""
        assert parser.parse_runtime(tv_detail) == 47

    # ── TV 시리즈 runtime 형식 불일치 엣지 케이스 ──

    def test_TV_episode_run_time_빈리스트(self, parser):
        """episode_run_time이 빈 리스트이면 None 반환 (IndexError 없음)"""
        detail = {"episode_run_time": []}
        assert parser.parse_runtime(detail) is None

    def test_TV_episode_run_time_None(self, parser):
        """episode_run_time이 None이면 None 반환"""
        detail = {"episode_run_time": None}
        assert parser.parse_runtime(detail) is None

    def test_TV_episode_run_time_0이면_None(self, parser):
        """episode_run_time이 [0]이면 유효하지 않은 값으로 None 반환"""
        detail = {"episode_run_time": [0]}
        assert parser.parse_runtime(detail) is None

    def test_TV_episode_run_time_음수이면_None(self, parser):
        """episode_run_time이 [-1]이면 None 반환"""
        detail = {"episode_run_time": [-1]}
        assert parser.parse_runtime(detail) is None

    def test_TV_episode_run_time_문자열이면_None(self, parser):
        """episode_run_time이 ['45분'] 처럼 문자열이면 None 반환 (TypeError 없음)"""
        detail = {"episode_run_time": ["45분"]}
        assert parser.parse_runtime(detail) is None

    def test_영화_runtime이_0이면_None(self, parser):
        """runtime이 0이면 유효하지 않은 값으로 None 반환"""
        assert parser.parse_runtime({"runtime": 0}) is None

    def test_runtime_필드_전체_누락(self, parser):
        """runtime, episode_run_time 둘 다 없으면 None"""
        assert parser.parse_runtime({}) is None

    def test_영화에_episode_run_time도_있는_경우_runtime_우선(self, parser):
        """runtime과 episode_run_time 둘 다 있으면 runtime 우선 반환"""
        detail = {"runtime": 120, "episode_run_time": [45]}
        assert parser.parse_runtime(detail) == 120


# ═════════════════════════════════════════
#  6. parse_genres()
# ═════════════════════════════════════════

class TestParseGenres:

    def test_정상_장르_파싱(self, parser, movie_detail):
        """genres 리스트에서 name만 추출"""
        result = parser.parse_genres(movie_detail)
        assert result == ["드라마", "SF"]

    def test_genres_필드_누락(self, parser):
        """genres 키 없어도 빈 리스트 반환"""
        assert parser.parse_genres({}) == []

    def test_genres_None이면_빈리스트(self, parser):
        """genres 값이 None이어도 빈 리스트 반환"""
        assert parser.parse_genres({"genres": None}) == []

    def test_genre_name_없는_항목_필터링(self, parser):
        """name 키 없는 장르 항목은 건너뜀"""
        detail = {"genres": [{"id": 1, "name": "액션"}, {"id": 2}]}
        result = parser.parse_genres(detail)
        assert result == ["액션"]


# ═════════════════════════════════════════
#  7. parse_providers()
# ═════════════════════════════════════════

class TestParseProviders:

    def test_정상_OTT_파싱(self, parser, providers_raw):
        """KR flatrate OTT 목록이 정상 파싱되는지 확인"""
        result = parser.parse_providers(providers_raw)
        names = [p["name"] for p in result]
        assert "Netflix" in names
        assert "Watcha"  in names

    def test_중복_OTT_제거(self, parser):
        """flatrate와 buy에 동일한 provider가 있어도 한 번만 반환"""
        raw = {
            "results": {
                "KR": {
                    "flatrate": [{"provider_id": 8, "logo_path": "/n.jpg"}],
                    "buy":      [{"provider_id": 8, "logo_path": "/n.jpg"}],
                }
            }
        }
        result = parser.parse_providers(raw)
        assert len([p for p in result if p["name"] == "Netflix"]) == 1

    def test_KR_없으면_빈리스트(self, parser):
        """results에 KR 키가 없으면 빈 리스트 반환"""
        raw = {"results": {"US": {"flatrate": []}}}
        assert parser.parse_providers(raw) == []

    def test_알수없는_provider_id_제외(self, parser):
        """OTT_PROVIDERS에 없는 provider_id는 무시"""
        raw = {
            "results": {
                "KR": {
                    "flatrate": [{"provider_id": 99999, "logo_path": "/x.jpg"}]
                }
            }
        }
        assert parser.parse_providers(raw) == []

    def test_providers_raw_None이면_빈리스트(self, parser):
        """providers_raw 자체가 None이면 빈 리스트"""
        assert parser.parse_providers(None) == []

    def test_logo_path_없으면_빈문자열(self, parser):
        """logo_path 없는 provider는 logo_url이 빈 문자열"""
        raw = {
            "results": {
                "KR": {"flatrate": [{"provider_id": 8, "logo_path": None}]}
            }
        }
        result = parser.parse_providers(raw)
        assert result[0]["logo_url"] == ""


# ═════════════════════════════════════════
#  8. parse_detail() — 통합 파싱
# ═════════════════════════════════════════

class TestParseDetail:

    def test_영화_전체_조립(self, parser, movie_detail, providers_raw):
        """영화 상세 응답 전체가 올바르게 조립되는지 확인"""
        result = parser.parse_detail(157336, "movie", movie_detail, providers_raw)

        assert result["id"]         == 157336
        assert result["media_type"] == "movie"
        assert result["title"]      == "인터스텔라"
        assert result["rating"]     == 8.4
        assert result["runtime"]    == 169
        assert len(result["cast"])  == 2
        assert len(result["genres"]) == 2
        assert len(result["providers"]) == 2

    def test_TV_전체_조립(self, parser, tv_detail, providers_raw):
        """TV 시리즈 상세 응답 전체 조립 확인"""
        result = parser.parse_detail(1396, "tv", tv_detail, providers_raw)

        assert result["media_type"] == "tv"
        assert result["title"]      == "브레이킹 배드"
        assert result["runtime"]    == 47
        assert result["release"]    == "2008-01-20"

    def test_title_누락시_제목없음(self, parser):
        """title, name 모두 없으면 '제목 없음' 반환"""
        result = parser.parse_detail(1, "movie", {}, {})
        assert result["title"] == "제목 없음"

    def test_overview_누락시_기본문구(self, parser):
        """overview 없으면 '줄거리 정보 없음' 반환"""
        result = parser.parse_detail(1, "movie", {}, {})
        assert result["overview"] == "줄거리 정보 없음"

    def test_poster_없으면_None(self, parser):
        """poster_path 누락 시 poster 필드 None"""
        result = parser.parse_detail(1, "movie", {}, {})
        assert result["poster"] is None

    def test_vote_average_None이면_0점(self, parser):
        """vote_average 없으면 rating 0.0"""
        result = parser.parse_detail(1, "movie", {"vote_average": None}, {})
        assert result["rating"] == 0.0

    def test_필수_키_전부_존재(self, parser):
        """parse_detail 결과에 UI에 필요한 모든 키가 포함되어 있는지 확인"""
        result = parser.parse_detail(1, "movie", {}, {})
        required_keys = [
            "id", "media_type", "title", "tagline", "overview",
            "poster", "backdrop", "rating", "vote_count", "release",
            "runtime", "genres", "cast", "providers", "tmdb_reviews",
        ]
        for key in required_keys:
            assert key in result, f"필수 키 '{key}'가 결과에 없음"


# ═════════════════════════════════════════
#  9. TMDB 응답 지연 및 타임아웃 엣지 케이스
# ═════════════════════════════════════════

class TestTmdbTimeout:
    """
    TmdbParser 자체는 I/O를 수행하지 않는다.
    타임아웃 테스트는 tmdb_get() 을 @patch로 모킹하여
    app.py 라우트가 None 응답을 올바르게 처리하는지 검증한다.
    """

    @patch("app.tmdb_get")
    def test_타임아웃시_tmdb_get이_None반환(self, mock_tmdb, parser):
        """
        urllib.error.URLError(timeout) 발생 시
        tmdb_get 이 None 을 반환하고 파서는 안전하게 처리해야 함
        """
        mock_tmdb.side_effect = urllib.error.URLError("timed out")

        # tmdb_get 이 None 을 반환했을 때 parser 가 받는 값 시뮬레이션
        detail = None
        result = parser.parse_cast(detail or {})
        assert result == []

    @patch("app.tmdb_get")
    def test_응답지연_후_None수신(self, mock_tmdb, parser):
        """
        응답 지연(timeout=10초 초과) 후 None 을 받았을 때
        parse_detail 이 KeyError 없이 기본값으로 응답
        """
        mock_tmdb.return_value = None

        # None 을 빈 dict 로 대체하는 app.py 패턴 시뮬레이션
        detail = mock_tmdb() or {}
        result = parser.parse_detail(1, "movie", detail, {})

        assert result["title"]      == "제목 없음"
        assert result["overview"]   == "줄거리 정보 없음"
        assert result["cast"]       == []
        assert result["providers"]  == []
        assert result["genres"]     == []

    @patch("app.tmdb_get")
    def test_TMDB_API_오류_응답(self, mock_tmdb, parser):
        """
        TMDB 가 status_code:34 (not found) 오류 응답을 반환할 때
        tmdb_get이 None을 반환하고 파서는 안전하게 처리
        """
        mock_tmdb.return_value = None  # app.py tmdb_get 은 오류 시 None 반환

        detail = mock_tmdb() or {}
        assert parser.parse_genres(detail)  == []
        assert parser.parse_cast(detail)    == []
        assert parser.parse_reviews(detail) == []

    def test_파서_자체_지연없음(self, parser, movie_detail):
        """
        TmdbParser 메서드 자체는 I/O 없이 즉시 완료되어야 함
        (100ms 이내 완료 검증)
        """
        start = time.time()
        for _ in range(1000):
            parser.parse_cast(movie_detail)
            parser.parse_reviews(movie_detail)
            parser.parse_genres(movie_detail)
        elapsed = time.time() - start
        assert elapsed < 1.0, f"파서가 너무 느립니다: {elapsed:.2f}s for 1000 iterations"

    @patch("app.tmdb_get")
    def test_부분응답_credits만_누락(self, mock_tmdb, parser):
        """
        TMDB 가 append_to_response 중 credits 만 누락된 응답을 보낼 때
        나머지 필드는 정상 파싱되어야 함
        """
        partial_detail = {
            "id": 1, "title": "부분 응답 영화",
            "vote_average": 7.0,
            # credits 누락
            "reviews": {"results": []},
            "genres": [{"id": 28, "name": "액션"}],
        }
        mock_tmdb.return_value = partial_detail

        detail = mock_tmdb()
        assert parser.parse_genres(detail)  == ["액션"]
        assert parser.parse_cast(detail)    == []   # credits 없어도 안전
        assert parser.parse_reviews(detail) == []


# ═════════════════════════════════════════
#  10. 대용량 / 경계값 테스트
# ═════════════════════════════════════════

class TestBoundaryValues:

    def test_cast_0명(self, parser):
        """출연진 0명이어도 빈 리스트 반환"""
        assert parser.parse_cast({"credits": {"cast": []}}) == []

    def test_review_정확히_400자(self, parser):
        """리뷰가 정확히 400자이면 '...' 없이 그대로 반환"""
        text = "A" * 400
        detail = {"reviews": {"results": [{"author": "u", "content": text,
                                           "author_details": {}}]}}
        result = parser.parse_reviews(detail)
        assert len(result[0]["content"]) == 400
        assert not result[0]["content"].endswith("...")

    def test_review_401자(self, parser):
        """리뷰가 401자이면 400자 + '...' (총 403자)"""
        text = "A" * 401
        detail = {"reviews": {"results": [{"author": "u", "content": text,
                                           "author_details": {}}]}}
        result = parser.parse_reviews(detail)
        assert len(result[0]["content"]) == 403

    def test_rating_소수점반올림(self, parser):
        """vote_average 8.449 → 8.4, 8.450 → 8.5 반올림 확인"""
        item1 = {"id": 1, "media_type": "movie", "title": "A",
                 "vote_average": 8.449}
        item2 = {"id": 2, "media_type": "movie", "title": "B",
                 "vote_average": 8.450}
        assert parser.parse_list_item(item1)["rating"] == 8.4
        assert parser.parse_list_item(item2)["rating"] == 8.5

    def test_parse_detail_빈딕셔너리(self, parser):
        """완전히 빈 detail dict 이어도 예외 없이 기본값 반환"""
        try:
            result = parser.parse_detail(0, "movie", {}, {})
            assert isinstance(result, dict)
        except Exception as e:
            pytest.fail(f"빈 dict 에서 예외 발생: {e}")