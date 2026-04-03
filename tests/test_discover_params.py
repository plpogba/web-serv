import pytest
from dataclasses import dataclass, field


# ─────────────────────────────────────────
#  테스트 대상: DiscoverParams dataclass
#  (전략 5 — 파라미터를 dataclass로 모델링)
#
#  아래 클래스는 app.py에 구현될 최종 코드를 미리 정의한 것입니다.
#  테스트가 먼저 작성되고(Red), 이후 app.py에 클래스를 추가해 통과(Green)시킵니다.
# ─────────────────────────────────────────

@dataclass
class DiscoverParams:
    genre:           str
    page:            str
    ott:             str  = ""
    sort_by:         str  = "popularity.desc"
    genre_operator:  str  = "AND"          # "AND"(,) | "OR"(|)
    monetization_type: str = "flatrate"    # flatrate | free | ads | buy | rent

    # ── page 검증 ──────────────────────────
    def __post_init__(self):
        # 타입 검증: 정수로 변환 불가능하면 TypeError
        try:
            page_int = int(self.page)
        except (ValueError, TypeError):
            raise TypeError(f"page는 정수여야 합니다: '{self.page}'")

        # 범위 검증: 1 이상 500 이하 (TMDB 최대 페이지 제한)
        if not (1 <= page_int <= 500):
            raise ValueError(f"page는 1~500 사이여야 합니다: {page_int}")

        # genre_operator 검증
        if self.genre_operator not in ("AND", "OR"):
            raise ValueError(f"genre_operator는 'AND' 또는 'OR'이어야 합니다: '{self.genre_operator}'")

        # monetization_type 검증
        valid_types = {"flatrate", "free", "ads", "buy", "rent"}
        if self.monetization_type not in valid_types:
            raise ValueError(f"monetization_type이 유효하지 않습니다: '{self.monetization_type}'")

    def _formatted_genre(self) -> str:
        """genre_operator에 따라 장르 ID 구분자를 결정합니다."""
        if not self.genre:
            return ""
        separator = "," if self.genre_operator == "AND" else "|"
        # 이미 구분자가 포함된 경우 재변환 방지
        ids = [g.strip() for g in self.genre.replace("|", ",").split(",") if g.strip()]
        return separator.join(ids)

    def to_dict(self) -> dict:
        params = {
            "with_genres": self._formatted_genre(),
            "page":        self.page,
            "sort_by":     self.sort_by,
        }
        if self.ott:
            params["with_watch_providers"]  = self.ott
            params["watch_region"]          = "KR"
            params["with_watch_monetization_types"] = self.monetization_type
        return params


# ─────────────────────────────────────────
#  테스트: page 파라미터 타입 불일치 / 범위 초과
# ─────────────────────────────────────────

class TestPageValidation:

    def test_page_문자열_숫자는_정상_통과(self):
        """page='3' 처럼 숫자 문자열은 정상 생성"""
        params = DiscoverParams(genre="28", page="3")
        assert params.to_dict()["page"] == "3"

    def test_page_알파벳_문자열_TypeError(self):
        """page='abc' 전달 시 TypeError 발생"""
        with pytest.raises(TypeError, match="정수여야 합니다"):
            DiscoverParams(genre="28", page="abc")

    def test_page_특수문자_TypeError(self):
        """page='!@#' 전달 시 TypeError 발생"""
        with pytest.raises(TypeError, match="정수여야 합니다"):
            DiscoverParams(genre="28", page="!@#")

    def test_page_float_문자열_TypeError(self):
        """page='1.5' 처럼 실수 문자열 전달 시 TypeError 발생"""
        with pytest.raises(TypeError, match="정수여야 합니다"):
            DiscoverParams(genre="28", page="1.5")

    def test_page_0_범위초과_ValueError(self):
        """page='0' 전달 시 ValueError 발생 (최솟값 1 미만)"""
        with pytest.raises(ValueError, match="1~500"):
            DiscoverParams(genre="28", page="0")

    def test_page_음수_범위초과_ValueError(self):
        """page='-1' 전달 시 ValueError 발생"""
        with pytest.raises(ValueError, match="1~500"):
            DiscoverParams(genre="28", page="-1")

    def test_page_501_범위초과_ValueError(self):
        """page='501' 전달 시 ValueError 발생 (TMDB 최대 500 초과)"""
        with pytest.raises(ValueError, match="1~500"):
            DiscoverParams(genre="28", page="501")

    def test_page_경계값_1_정상(self):
        """page='1' 경계값 정상 통과"""
        params = DiscoverParams(genre="28", page="1")
        assert params.to_dict()["page"] == "1"

    def test_page_경계값_500_정상(self):
        """page='500' 경계값 정상 통과"""
        params = DiscoverParams(genre="28", page="500")
        assert params.to_dict()["page"] == "500"

    def test_page_None_TypeError(self):
        """page=None 전달 시 TypeError 발생"""
        with pytest.raises(TypeError, match="정수여야 합니다"):
            DiscoverParams(genre="28", page=None)


# ─────────────────────────────────────────
#  테스트: 다중 장르 AND / OR 연산자
# ─────────────────────────────────────────

class TestGenreOperator:

    def test_단일_장르_AND_구분자_없음(self):
        """단일 장르 ID는 구분자 없이 그대로 반환"""
        params = DiscoverParams(genre="28", page="1", genre_operator="AND")
        assert params.to_dict()["with_genres"] == "28"

    def test_다중_장르_AND_쉼표_구분자(self):
        """AND 연산자 시 장르 ID를 쉼표(,)로 연결 — TMDB AND 처리"""
        params = DiscoverParams(genre="28,12", page="1", genre_operator="AND")
        assert params.to_dict()["with_genres"] == "28,12"

    def test_다중_장르_OR_파이프_구분자(self):
        """OR 연산자 시 장르 ID를 파이프(|)로 연결 — TMDB OR 처리"""
        params = DiscoverParams(genre="28,12", page="1", genre_operator="OR")
        assert params.to_dict()["with_genres"] == "28|12"

    def test_파이프_입력값_OR_연산자로_재변환(self):
        """이미 파이프로 들어온 입력도 OR 연산자 설정 시 파이프 유지"""
        params = DiscoverParams(genre="28|12", page="1", genre_operator="OR")
        assert params.to_dict()["with_genres"] == "28|12"

    def test_파이프_입력값_AND_연산자로_변환(self):
        """파이프로 들어온 입력을 AND 연산자 설정 시 쉼표로 변환"""
        params = DiscoverParams(genre="28|12", page="1", genre_operator="AND")
        assert params.to_dict()["with_genres"] == "28,12"

    def test_빈_장르_빈문자열_반환(self):
        """장르가 없으면 with_genres는 빈 문자열"""
        params = DiscoverParams(genre="", page="1")
        assert params.to_dict()["with_genres"] == ""

    def test_잘못된_genre_operator_ValueError(self):
        """'AND' / 'OR' 이외의 값 전달 시 ValueError 발생"""
        with pytest.raises(ValueError, match="genre_operator"):
            DiscoverParams(genre="28", page="1", genre_operator="XOR")

    def test_세_개_장르_AND(self):
        """세 개 장르 AND — 쉼표로 모두 연결"""
        params = DiscoverParams(genre="28,12,35", page="1", genre_operator="AND")
        assert params.to_dict()["with_genres"] == "28,12,35"

    def test_세_개_장르_OR(self):
        """세 개 장르 OR — 파이프로 모두 연결"""
        params = DiscoverParams(genre="28,12,35", page="1", genre_operator="OR")
        assert params.to_dict()["with_genres"] == "28|12|35"

    def test_공백_포함_장르_ID_정규화(self):
        """공백이 섞인 장르 ID 목록을 정상적으로 정규화"""
        params = DiscoverParams(genre="28, 12 , 35", page="1", genre_operator="AND")
        assert params.to_dict()["with_genres"] == "28,12,35"


# ─────────────────────────────────────────
#  테스트: OTT 필터링 Monetization Type 누락
# ─────────────────────────────────────────

class TestOttMonetizationType:

    def test_OTT_없으면_monetization_type_미포함(self):
        """OTT 미지정 시 with_watch_monetization_types 키가 없어야 함"""
        params = DiscoverParams(genre="28", page="1")
        result = params.to_dict()
        assert "with_watch_monetization_types" not in result

    def test_OTT_있으면_기본값_flatrate_포함(self):
        """OTT 지정 시 monetization_type 기본값 'flatrate'가 포함되어야 함"""
        params = DiscoverParams(genre="28", page="1", ott="8")
        result = params.to_dict()
        assert result["with_watch_monetization_types"] == "flatrate"

    def test_OTT_있으면_watch_region_KR_포함(self):
        """OTT 지정 시 watch_region=KR이 반드시 포함되어야 함"""
        params = DiscoverParams(genre="28", page="1", ott="8")
        result = params.to_dict()
        assert result["watch_region"] == "KR"

    def test_monetization_type_buy_설정(self):
        """monetization_type='buy' 설정 시 정상 반영"""
        params = DiscoverParams(genre="28", page="1", ott="8", monetization_type="buy")
        assert params.to_dict()["with_watch_monetization_types"] == "buy"

    def test_monetization_type_rent_설정(self):
        """monetization_type='rent' 설정 시 정상 반영"""
        params = DiscoverParams(genre="28", page="1", ott="8", monetization_type="rent")
        assert params.to_dict()["with_watch_monetization_types"] == "rent"

    def test_monetization_type_free_설정(self):
        """monetization_type='free' 설정 시 정상 반영"""
        params = DiscoverParams(genre="28", page="1", ott="8", monetization_type="free")
        assert params.to_dict()["with_watch_monetization_types"] == "free"

    def test_monetization_type_ads_설정(self):
        """monetization_type='ads' 설정 시 정상 반영"""
        params = DiscoverParams(genre="28", page="1", ott="8", monetization_type="ads")
        assert params.to_dict()["with_watch_monetization_types"] == "ads"

    def test_잘못된_monetization_type_ValueError(self):
        """유효하지 않은 monetization_type 전달 시 ValueError 발생"""
        with pytest.raises(ValueError, match="monetization_type"):
            DiscoverParams(genre="28", page="1", ott="8", monetization_type="premium")

    def test_OTT_없으면_watch_region_미포함(self):
        """OTT 미지정 시 watch_region 키가 없어야 함"""
        params = DiscoverParams(genre="28", page="1")
        result = params.to_dict()
        assert "watch_region" not in result

    def test_OTT_없으면_with_watch_providers_미포함(self):
        """OTT 미지정 시 with_watch_providers 키가 없어야 함"""
        params = DiscoverParams(genre="28", page="1")
        result = params.to_dict()
        assert "with_watch_providers" not in result