from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List, Dict, Any

# 상수 설정
IMG_BASE = "https://image.tmdb.org/t/p"
VALID_TYPES = ("movie", "tv")

OTT_PROVIDERS = {
    8:   {"name": "Netflix",      "color": "#E50914"},
    97:  {"name": "Watcha",       "color": "#FF0558"},
    356: {"name": "Coupang Play", "color": "#1ABCFE"},
    337: {"name": "Disney+",      "color": "#113CCF"},
    2:   {"name": "Apple TV+",    "color": "#555555"},
}

class TmdbParser:
    """
    TMDB API 응답을 내부 도메인 모델로 변환하는 전담 클래스.
    부동 소수점 반올림 오차 및 데이터 누락에 대한 방어 로직 포함.
    """

    def _safe_round(self, value: Any) -> float:
        """사사오입을 적용하여 소수점 첫째 자리까지 반올림"""
        try:
            if value is None or value == "":
                return 0.0
            rounded = Decimal(str(value)).quantize(
                Decimal("0.1"), 
                rounding=ROUND_HALF_UP
            )
            return float(rounded)
        except (ValueError, TypeError, ArithmeticError):
            return 0.0

    def img_url(self, path: Optional[str], size: str = "w500") -> Optional[str]:
        """이미지 경로 URL 변환"""
        if not path:
            return None
        return f"{IMG_BASE}/{size}{path}"

    def parse_runtime(self, detail: Dict[str, Any]) -> Optional[int]:
        """
        TV(episode_run_time)와 영화(runtime)를 구분하여 유효한 런타임 추출.
        """
        if not detail:
            return None

        # 1. 일반 runtime 필드 먼저 확인 (영화 우선)
        rt = detail.get("runtime")
        if isinstance(rt, int) and rt > 0:
            return rt

        # 2. runtime이 리스트로 들어오는 변칙 케이스 대응
        if isinstance(rt, list) and len(rt) > 0:
            val = rt[0]
            if isinstance(val, int) and val > 0:
                return val

        # 3. TV 시리즈 전용 필드 fallback
        ert = detail.get("episode_run_time")
        if isinstance(ert, list) and len(ert) > 0:
            val = ert[0]
            if isinstance(val, int) and val > 0:
                return val

        return None

    def parse_list_item(self, item: Dict[str, Any], media_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        mt = media_type or item.get("media_type", "movie")
        if mt not in VALID_TYPES:
            return None
            
        return {
            "id":         item.get("id"),
            "media_type": mt,
            "title":      item.get("title") or item.get("name") or "제목 없음",
            "overview":   item.get("overview") or "",
            "poster":     self.img_url(item.get("poster_path")),
            "backdrop":   self.img_url(item.get("backdrop_path"), "w1280"),
            "rating":     self._safe_round(item.get("vote_average")),
            "vote_count": item.get("vote_count") or 0,
            "release":    item.get("release_date") or item.get("first_air_date") or "",
            "genre_ids":  item.get("genre_ids") or [],
        }

    def parse_cast(self, detail: Dict[str, Any]) -> List[Dict[str, Any]]:
        credits = detail.get("credits") or {}
        cast_raw = credits.get("cast") or []
        return [{
            "name":      c.get("name") or "",
            "character": c.get("character") or "",
            "photo":     self.img_url(c.get("profile_path"), "w185"),
        } for c in cast_raw[:10]]

    def parse_reviews(self, detail: Dict[str, Any]) -> List[Dict[str, Any]]:
        reviews_obj = detail.get("reviews") or {}
        reviews_raw = reviews_obj.get("results") or []
        result = []
        for r in reviews_raw[:5]:
            text = r.get("content") or ""
            result.append({
                "author":  r.get("author") or "익명",
                "content": text[:400] + ("..." if len(text) > 400 else ""),
                "rating":  (r.get("author_details") or {}).get("rating"),
            })
        return result

    def parse_genres(self, detail: Dict[str, Any]) -> List[str]:
        genres_raw = detail.get("genres") or []
        return [g["name"] for g in genres_raw if isinstance(g, dict) and g.get("name")]

    def parse_providers(self, providers_raw: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not providers_raw:
            return []
        results = providers_raw.get("results") or {}
        kr_data = results.get("KR") or {}
        combined = (kr_data.get("flatrate") or []) + (kr_data.get("buy") or []) + (kr_data.get("rent") or [])
        
        seen_ids, result = set(), []
        for p in combined:
            pid = p.get("provider_id")
            if pid in OTT_PROVIDERS and pid not in seen_ids:
                seen_ids.add(pid)
                info = OTT_PROVIDERS[pid].copy()
                info["logo_url"] = self.img_url(p.get("logo_path"), "w92") or ""
                result.append(info)
        return result

    def parse_detail(self, content_id: int, media_type: str,
                     detail: Dict[str, Any], providers_raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        data = detail or {}
        return {
            "id":           content_id,
            "media_type":   media_type,
            "title":        data.get("title") or data.get("name") or "제목 없음",
            "tagline":      data.get("tagline") or "",
            "overview":     data.get("overview") or "줄거리 정보 없음",
            "poster":       self.img_url(data.get("poster_path")),
            "backdrop":     self.img_url(data.get("backdrop_path"), "w1280"),
            "rating":       self._safe_round(data.get("vote_average")),
            "vote_count":   data.get("vote_count") or 0,
            "release":      data.get("release_date") or data.get("first_air_date") or "",
            "runtime":      self.parse_runtime(data),
            "genres":       self.parse_genres(data),
            "cast":         self.parse_cast(data),
            "providers":    self.parse_providers(providers_raw),
            "tmdb_reviews": self.parse_reviews(data),
        }