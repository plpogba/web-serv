import pytest
import copy
from app.media_type_handler import (
    get_handler,
    is_valid,
    supported_types,
    MovieHandler,
    TvHandler,
    _HANDLERS,
)


# ─────────────────────────────────────────
#  테스트: Person 타입 유입으로 인한 서비스 중단
#  (The "Person" Crash)
#
#  TMDB trending/search API는 media_type="person"을 포함한 결과를 반환합니다.
#  이 값이 그대로 핸들러에 전달될 경우 서비스가 중단되어야 하는 게 아니라
#  ValueError로 명확히 거부되어야 합니다.
# ─────────────────────────────────────────

class TestPersonTypeCrash:

    def test_person_타입_ValueError_발생(self):
        """'person' 유입 시 서비스 중단 대신 ValueError 발생"""
        with pytest.raises(ValueError, match="지원하지 않는 media_type"):
            get_handler("person")

    def test_person_타입_is_valid_False(self):
        """'person'은 is_valid()에서 False 반환 — 조용한 거부"""
        assert is_valid("person") is False

    def test_person_타입_에러메시지에_지원목록_포함(self):
        """에러 메시지에 지원 타입 목록이 포함되어 디버깅을 돕는다"""
        with pytest.raises(ValueError) as exc_info:
            get_handler("person")
        assert "movie" in str(exc_info.value)
        assert "tv"    in str(exc_info.value)

    def test_빈문자열_ValueError_발생(self):
        """빈 문자열 유입 시 ValueError 발생"""
        with pytest.raises(ValueError, match="지원하지 않는 media_type"):
            get_handler("")

    def test_None_ValueError_발생(self):
        """None 유입 시 ValueError 발생 (AttributeError가 아니어야 함)"""
        with pytest.raises(ValueError, match="지원하지 않는 media_type"):
            get_handler(None)

    def test_알수없는_타입_ValueError_발생(self):
        """'anime', 'documentary' 등 미등록 타입은 ValueError"""
        for unknown in ("anime", "documentary", "short", "unknown"):
            with pytest.raises(ValueError):
                get_handler(unknown)

    def test_person_타입_discover_path_접근_불가(self):
        """'person'으로 discover_path에 접근하는 시나리오가 차단됨을 확인"""
        with pytest.raises(ValueError):
            handler = get_handler("person")
            _ = handler.discover_path   # 이 줄은 실행되지 않아야 함


# ─────────────────────────────────────────
#  테스트: 대소문자 및 공백 처리 누락
#  (Case-Sensitivity & Sanitization)
#
#  URL, 쿼리스트링, 클라이언트에서 'Movie', 'TV ', ' movie ' 형태로
#  들어올 수 있습니다. 이를 거부하지 않고 정상 처리해야 합니다.
# ─────────────────────────────────────────

class TestCaseSensitivityAndSanitization:

    def test_대문자_Movie_정상_처리(self):
        """'Movie' → MovieHandler 반환"""
        handler = get_handler("Movie")
        assert isinstance(handler, MovieHandler)

    def test_전체_대문자_MOVIE_정상_처리(self):
        """'MOVIE' → MovieHandler 반환"""
        handler = get_handler("MOVIE")
        assert isinstance(handler, MovieHandler)

    def test_대문자_TV_정상_처리(self):
        """'TV' → TvHandler 반환"""
        handler = get_handler("TV")
        assert isinstance(handler, TvHandler)

    def test_앞뒤_공백_movie_정상_처리(self):
        """' movie ' → MovieHandler 반환 (공백 strip)"""
        handler = get_handler(" movie ")
        assert isinstance(handler, MovieHandler)

    def test_앞뒤_공백_tv_정상_처리(self):
        """' tv ' → TvHandler 반환"""
        handler = get_handler(" tv ")
        assert isinstance(handler, TvHandler)

    def test_대소문자_혼합_공백_포함_정상_처리(self):
        """' Movie ' → MovieHandler 반환"""
        handler = get_handler(" Movie ")
        assert isinstance(handler, MovieHandler)

    def test_정제된_value는_항상_소문자(self):
        """'MOVIE' 입력 후 핸들러의 value는 소문자 'movie'"""
        handler = get_handler("MOVIE")
        assert handler.value == "movie"

    def test_탭_공백_정제(self):
        """'\tmovie\t' → MovieHandler 반환 (탭 문자 제거)"""
        handler = get_handler("\tmovie\t")
        assert isinstance(handler, MovieHandler)

    def test_is_valid_대소문자_무관(self):
        """is_valid()도 대소문자 무관하게 동작"""
        assert is_valid("Movie")  is True
        assert is_valid("TV")     is True
        assert is_valid("MOVIE")  is True

    def test_내부_공백_포함은_ValueError(self):
        """'mo vie' 처럼 중간 공백은 다른 값이므로 ValueError"""
        with pytest.raises(ValueError):
            get_handler("mo vie")


# ─────────────────────────────────────────
#  테스트: 글로벌 딕셔너리의 가변성 위험
#  (Mutable Global Registry)
#
#  외부 코드가 _HANDLERS를 직접 수정해 등록된 핸들러를 오염시키거나
#  삭제할 수 있는 위험을 확인하고, 이에 대한 방어를 검증합니다.
# ─────────────────────────────────────────

class TestMutableGlobalRegistry:

    def test_외부에서_핸들러_추가해도_get_handler_영향없음(self):
        """_HANDLERS에 외부에서 항목을 추가해도 get_handler는 원본 기반 동작"""
        _HANDLERS["fake"] = MovieHandler()   # 외부 오염 시도
        # get_handler는 내부 튜플 기반으로 구성되므로 fake가 통과되어선 안 됨
        # 단, 현재 구현이 dict를 공유한다면 이 테스트는 실패 → 방어 구현 필요
        try:
            handler = get_handler("fake")
            # 만약 통과된다면 Registry 방어가 미흡함을 의미
            assert False, "외부 오염이 get_handler에 영향을 주어선 안 됩니다"
        except ValueError:
            pass   # 올바른 동작
        finally:
            _HANDLERS.pop("fake", None)   # 테스트 후 정리

    def test_외부에서_핸들러_삭제해도_get_handler_정상동작(self):
        """_HANDLERS에서 'movie'를 삭제해도 get_handler는 정상 반환해야 함"""
        original = _HANDLERS.pop("movie", None)   # 오염 시도
        try:
            # 방어 구현이 되어 있다면 ValueError가 아닌 핸들러를 반환해야 함
            handler = get_handler("movie")
            assert isinstance(handler, MovieHandler)
        except ValueError:
            # 방어 구현이 없다면 삭제가 영향을 준 것 → 실패를 명확히 기록
            pytest.fail("_HANDLERS 외부 삭제가 get_handler에 영향을 주었습니다")
        finally:
            if original:
                _HANDLERS["movie"] = original   # 테스트 후 복원

    def test_supported_types_는_불변_튜플_반환(self):
        """supported_types()는 tuple을 반환해 외부 수정이 원본에 영향 없음"""
        types = supported_types()
        assert isinstance(types, tuple)

    def test_supported_types_반환값_수정이_내부에_영향없음(self):
        """반환된 tuple은 immutable이므로 수정 시도 시 TypeError"""
        types = supported_types()
        with pytest.raises((TypeError, AttributeError)):
            types[0] = "hacked"   # tuple은 수정 불가

    def test_get_handler_반환_핸들러_수정이_Registry에_영향없음(self):
        """반환된 핸들러 인스턴스를 수정해도 Registry 원본이 오염되지 않음"""
        handler = get_handler("movie")
        original_value = handler.value

        # 핸들러에 임의 속성을 추가해도 Registry 원본은 불변
        handler.__dict__["_injected"] = "malicious"

        fresh_handler = get_handler("movie")
        assert fresh_handler.value == original_value
        assert "_injected" not in fresh_handler.__dict__ or \
               fresh_handler.__dict__.get("_injected") != "malicious", \
               "Registry 원본이 오염되었습니다"

    def test_동시_호출_시_Registry_일관성(self):
        """여러 번 get_handler를 호출해도 항상 동일한 타입의 핸들러 반환"""
        handlers = [get_handler("movie") for _ in range(10)]
        assert all(isinstance(h, MovieHandler) for h in handlers)

    def test_movie와_tv_핸들러는_서로_다른_인스턴스(self):
        """movie와 tv는 다른 핸들러 인스턴스임을 보장"""
        movie_handler = get_handler("movie")
        tv_handler    = get_handler("tv")
        assert movie_handler is not tv_handler
        assert movie_handler.value != tv_handler.value