from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List, Dict, Any

# Constant Configuration
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
    """Dedicated class for converting TMDB API responses into internal domain models.

    Includes defensive logic for floating-point rounding errors and missing data.
    """
    def _safe_round(self, value: Any) -> float:
        """Rounds a value to one decimal place using ROUND_HALF_UP.

        Args:
            value (Any): The value to be rounded.

        Returns:
            float: The rounded value. Returns 0.0 if conversion fails.
        """
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
        """Converts an image path into a full TMDB image URL.

        Args:
            path (Optional[str]): The image path.
            size (str): Image size. Defaults to "w500".

        Returns:
            Optional[str]: The complete image URL. Returns None if the path is missing.
        """
        if not path:
            return None
        return f"{IMG_BASE}/{size}{path}"

    def parse_runtime(self, detail: Dict[str, Any]) -> Optional[int]:
        """Extracts valid runtime by distinguishing between TV (episode_run_time) and Movie (runtime).

        Args:
            detail (Dict[str, Any]): TMDB detail data.

        Returns:
            Optional[int]: Runtime in minutes. Returns None if extraction fails.
        """
        if not detail:
            return None

        # 1. Check standard runtime field (Priority: Movie)
        rt = detail.get("runtime")
        if isinstance(rt, int) and rt > 0:
            return rt

        # 2. Handle edge cases where runtime is provided as a list
        if isinstance(rt, list) and len(rt) > 0:
            val = rt
            if isinstance(val, int) and val > 0:
                return val

        # 3. Fallback for TV series specific fields
        ert = detail.get("episode_run_time")
        if isinstance(ert, list) and len(ert) > 0:
            val = ert
            if isinstance(val, int) and val > 0:
                return val

        return None

    def parse_list_item(self, item: Dict[str, Any], media_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Converts a TMDB list item into the internal format.

        Args:
            item (Dict[str, Any]): TMDB item data.
            media_type (Optional[str]): Media type. Defaults to None.

        Returns:
            Optional[Dict[str, Any]]: Formatted data. Returns None if the type is invalid.
        """
        mt = media_type or item.get("media_type", "movie")
        if mt not in VALID_TYPES:
            return None
            
        return {
            "id":         item.get("id"),
            "media_type": mt,
            "title":      item.get("title") or item.get("name") or "Untitled",
            "overview":   item.get("overview") or "",
            "poster":     self.img_url(item.get("poster_path")),
            "backdrop":   self.img_url(item.get("backdrop_path"), "w1280"),
            "rating":     self._safe_round(item.get("vote_average")),
            "vote_count": item.get("vote_count") or 0,
            "release":    item.get("release_date") or item.get("first_air_date") or "",
            "genre_ids":  item.get("genre_ids") or [],
        }

    def parse_cast(self, detail: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extracts cast information from the credits data.

        Args:
            detail (Dict[str, Any]): TMDB detail data (including credits).

        Returns:
            List[Dict[str, Any]]: List of cast members (up to 10).
        """
        credits = detail.get("credits") or {}
        cast_raw = credits.get("cast") or []
        return [{
            "name":      c.get("name") or "",
            "character": c.get("character") or "",
            "photo":     self.img_url(c.get("profile_path"), "w185"),
        } for c in cast_raw[:10]]

    def parse_reviews(self, detail: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Converts TMDB review data into the internal format.

        Args:
            detail (Dict[str, Any]): TMDB detail data (including reviews).

        Returns:
            List[Dict[str, Any]]: List of reviews (up to 5, content limited to 400 chars).
        """
        reviews_obj = detail.get("reviews") or {}
        reviews_raw = reviews_obj.get("results") or []
        result = []
        for r in reviews_raw[:5]:
            text = r.get("content") or ""
            result.append({
                "author":  r.get("author") or "Anonymous",
                "content": text[:400] + ("..." if len(text) > 400 else ""),
                "rating":  (r.get("author_details") or {}).get("rating"),
            })
        return result

    def parse_genres(self, detail: Dict[str, Any]) -> List[str]:
        """Extracts genre data as a list of strings.

        Args:
            detail (Dict[str, Any]): TMDB detail data.

        Returns:
            List[str]: List of genre names.
        """
        genres_raw = detail.get("genres") or []
        return [g["name"] for g in genres_raw if isinstance(g, dict) and g.get("name")]

    def parse_providers(self, providers_raw: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Converts OTT provider data into the internal format.

        Args:
            providers_raw (Optional[Dict[str, Any]]): Raw TMDB provider data.

        Returns:
            List[Dict[str, Any]]: List of providers (flatrate, buy, rent for KR region).
        """
        if not providers_raw:
            return []
        results = providers_raw.get("results") or {}
        kr_data = results.get("KR") or {}
        # Combine flatrate, buy, and rent options
        combined = (kr_data.get("flatrate") or []) + (kr_data.get("buy") or []) + (kr_data.get("rent") or [])
        
        seen_ids, result = set(), []
        for p in combined:
            pid = p.get("provider_id")
            # Only include providers defined in OTT_PROVIDERS without duplicates
            if pid in OTT_PROVIDERS and pid not in seen_ids:
                seen_ids.add(pid)
                info = OTT_PROVIDERS[pid].copy()
                info["logo_url"] = self.img_url(p.get("logo_path"), "w92") or ""
                result.append(info)
        return result

    def parse_detail(self, content_id: int, media_type: str,
                     detail: Dict[str, Any], providers_raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Transforms content detail into a complete internal format.

        Args:
            content_id (int): Content ID.
            media_type (str): Media type.
            detail (Dict[str, Any]): TMDB detail data.
            providers_raw (Optional[Dict[str, Any]]): Raw provider data.

        Returns:
            Dict[str, Any]: Fully formatted detail data.
        """
        try:
            data = detail or {}
            return {
                "id":           content_id,
                "media_type":   media_type,
                "title":        data.get("title") or data.get("name") or "Untitled",
                "tagline":      data.get("tagline") or "",
                "overview":     data.get("overview") or "No overview available.",
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
        except Exception as e:
            # Return default values in case of parsing errors
            return {
                "id": content_id,
                "media_type": media_type,
                "title": "Parsing Error",
                "overview": f"An error occurred while parsing data: {str(e)}",
                "rating": 0.0,
                "genres": [],
                "cast": [],
                "providers": [],
                "tmdb_reviews": [],
            }