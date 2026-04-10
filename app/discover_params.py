from dataclasses import dataclass


@dataclass
class DiscoverParams:
    """Data class to manage parameters for the TMDB discover API.

    Attributes:
        genre (str): Genre ID string (comma or pipe separated).
        page (str): Page number.
        ott (str): OTT provider ID. Defaults to "".
        sort_by (str): Sorting criteria. Defaults to "popularity.desc".
        genre_operator (str): Genre operator ("AND" or "OR"). Defaults to "AND".
        monetization_type (str): Monetization type. Defaults to "flatrate".
    """
    genre:             str
    page:              str
    ott:               str = ""
    sort_by:           str = "popularity.desc"
    genre_operator:    str = "AND"        # "AND"(,) | "OR"(|)
    monetization_type: str = "flatrate"   # flatrate | free | ads | buy | rent

    def __post_init__(self):
        """Performs validation after data class initialization.

        Raises:
            TypeError: If page is not an integer.
            ValueError: If page is out of range, or if genre_operator/monetization_type is invalid.
        """
        # Validate page type
        try:
            page_int = int(self.page)
        except (ValueError, TypeError):
            raise TypeError(f"page must be an integer: '{self.page}'")

        # Validate page range (TMDB limit is 500)
        if not (1 <= page_int <= 500):
            raise ValueError(f"page must be between 1 and 500: {page_int}")

        # Validate genre_operator
        if self.genre_operator not in ("AND", "OR"):
            raise ValueError(f"genre_operator must be 'AND' or 'OR': '{self.genre_operator}'")

        # Validate monetization_type
        valid_types = {"flatrate", "free", "ads", "buy", "rent"}
        if self.monetization_type not in valid_types:
            raise ValueError(f"monetization_type is invalid: '{self.monetization_type}'")

    def _formatted_genre(self) -> str:
        """Determines the genre ID separator based on the genre_operator.

        Returns:
            str: Formatted genre ID string.
        """
        if not self.genre:
            return ""
        separator = "," if self.genre_operator == "AND" else "|"
        ids = [g.strip() for g in self.genre.replace("|", ",").split(",") if g.strip()]
        return separator.join(ids)

    def to_dict(self) -> dict:
        """Generates a parameter dictionary to be used for TMDB API requests.

        Returns:
            dict: API parameter dictionary.
        """
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