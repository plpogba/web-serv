from dataclasses import dataclass


@dataclass
class DiscoverParams:
    genre:             str
    page:              str
    ott:               str = ""
    sort_by:           str = "popularity.desc"
    genre_operator:    str = "AND"        # "AND"(,) | "OR"(|)
    monetization_type: str = "flatrate"   # flatrate | free | ads | buy | rent

    def __post_init__(self):
        # page 타입 검증
        try:
            page_int = int(self.page)
        except (ValueError, TypeError):
            raise TypeError(f"page는 정수여야 합니다: '{self.page}'")

        # page 범위 검증 (TMDB 최대 500)
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
        ids = [g.strip() for g in self.genre.replace("|", ",").split(",") if g.strip()]
        return separator.join(ids)

    def to_dict(self) -> dict:
        params = {
            "with_genres": self._formatted_genre(),
            "page":        self.page,
            "sort_by":     self.sort_by,
        }
        if self.ott:
            params["with_watch_providers"]          = self.ott
            params["watch_region"]                  = "KR"
            params["with_watch_monetization_types"] = self.monetization_type
        return params