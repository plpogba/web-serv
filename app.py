from flask import Flask, request, jsonify, render_template
import urllib.request
import urllib.parse
import json

app = Flask(__name__)

# ─────────────────────────────────────────
#  설정
# ─────────────────────────────────────────

TMDB_API_KEY  = "9ca27837eb1468b7e55e35038920d183"
TMDB_BASE     = "https://api.themoviedb.org/3"
TMDB_IMG_BASE = "https://image.tmdb.org/t/p/w500"
LANGUAGE      = "ko-KR"

# JustWatch는 TMDB의 watch/providers 엔드포인트로 대체 (공식 파트너십)
# provider_id: 넷플릭스=8, 왓챠=97, 쿠팡플레이=356, 디즈니+=337, 애플TV=2
OTT_PROVIDERS = {
    8:   {"name": "Netflix",       "color": "#E50914", "logo": "netflix"},
    97:  {"name": "Watcha",        "color": "#FF0558", "logo": "watcha"},
    356: {"name": "Coupang Play",  "color": "#1ABCFE", "logo": "coupang"},
    337: {"name": "Disney+",       "color": "#113CCF", "logo": "disney"},
    2:   {"name": "Apple TV+",     "color": "#555555", "logo": "apple"},
}

# 자체 리뷰 DB
REVIEWS = {}   # { content_id: [ {id, author, rating, text, ott, created_at} ] }

# ─────────────────────────────────────────
#  TMDB 헬퍼 함수
# ─────────────────────────────────────────

def tmdb_get(path, extra_params=None):
    params = {"api_key": TMDB_API_KEY, "language": LANGUAGE}
    if extra_params:
        params.update(extra_params)
    url = f"{TMDB_BASE}{path}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=5) as res:
            return json.loads(res.read())
    except Exception as e:
        return None

def format_content(item, media_type=None):
    """TMDB 응답을 공통 포맷으로 변환"""
    mt = media_type or item.get("media_type", "movie")
    return {
        "id":          item.get("id"),
        "media_type":  mt,
        "title":       item.get("title") or item.get("name", ""),
        "overview":    item.get("overview", ""),
        "poster":      TMDB_IMG_BASE + item["poster_path"] if item.get("poster_path") else None,
        "backdrop":    "https://image.tmdb.org/t/p/w1280" + item["backdrop_path"] if item.get("backdrop_path") else None,
        "rating":      round(item.get("vote_average", 0), 1),
        "vote_count":  item.get("vote_count", 0),
        "release":     item.get("release_date") or item.get("first_air_date", ""),
        "genre_ids":   item.get("genre_ids", []),
    }

def get_providers(content_id, media_type):
    """JustWatch 연동 (TMDB watch/providers - 공식 파트너십)"""
    data = tmdb_get(f"/{media_type}/{content_id}/watch/providers")
    if not data:
        return []
    kr = data.get("results", {}).get("KR", {})
    provider_list = kr.get("flatrate", []) + kr.get("buy", []) + kr.get("rent", [])
    seen = set()
    result = []
    for p in provider_list:
        pid = p.get("provider_id")
        if pid in OTT_PROVIDERS and pid not in seen:
            seen.add(pid)
            info = OTT_PROVIDERS[pid].copy()
            info["logo_url"] = f"https://image.tmdb.org/t/p/original{p.get('logo_path','')}"
            result.append(info)
    return result

# ─────────────────────────────────────────
#  페이지 라우트
# ─────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/browse")
def browse():
    return render_template("browse.html")

@app.route("/content/<media_type>/<int:content_id>")
def content_detail(media_type, content_id):
    return render_template("detail.html",
                           content_id=content_id,
                           media_type=media_type)

@app.route("/review")
def review_page():
    return render_template("review.html")

# ─────────────────────────────────────────
#  API — 콘텐츠 조회
# ─────────────────────────────────────────

@app.route("/api/trending")
def api_trending():
    """홈 화면 트렌딩 (영화+TV 통합)"""
    data = tmdb_get("/trending/all/week")
    if not data:
        return jsonify([])
    items = [format_content(i) for i in data.get("results", [])[:20]]
    return jsonify(items)

@app.route("/api/browse")
def api_browse():
    """
    전체 목록 조회
    ?type=movie|tv  ?genre=장르id  ?ott=provider_id  ?q=검색어  ?page=1
    """
    media_type = request.args.get("type", "movie")
    genre      = request.args.get("genre", "")
    ott        = request.args.get("ott", "")
    query      = request.args.get("q", "").strip()
    page       = request.args.get("page", "1")

    try:
        if query:
            data = tmdb_get("/search/multi", {"query": query, "page": page})
        elif ott:
            data = tmdb_get(f"/discover/{media_type}", {
                "with_watch_providers": ott,
                "watch_region": "KR",
                "with_genres": genre,
                "page": page,
                "sort_by": "popularity.desc",
            })
        else:
            data = tmdb_get(f"/discover/{media_type}", {
                "with_genres": genre,
                "page": page,
                "sort_by": "popularity.desc",
            })

        if not data:
            return jsonify({"results": [], "total_pages": 0})

        results = []
        for item in data.get("results", []):
            mt = item.get("media_type", media_type)
            if mt in ("movie", "tv"):
                results.append(format_content(item, mt))

        return jsonify({"results": results, "total_pages": data.get("total_pages", 1)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/content/<media_type>/<int:content_id>")
def api_content_detail(media_type, content_id):
    """콘텐츠 상세 정보 (기본정보 + OTT편성 + 출연진 + TMDB리뷰)"""
    try:
        # 기본 정보
        detail = tmdb_get(f"/{media_type}/{content_id}", {"append_to_response": "credits,reviews"})
        if not detail:
            return jsonify({"error": "Not found"}), 404

        # 출연진
        cast = []
        for c in detail.get("credits", {}).get("cast", [])[:10]:
            cast.append({
                "name":      c.get("name"),
                "character": c.get("character"),
                "photo":     TMDB_IMG_BASE + c["profile_path"] if c.get("profile_path") else None,
            })

        # TMDB 외부 리뷰
        tmdb_reviews = []
        for r in detail.get("reviews", {}).get("results", [])[:5]:
            tmdb_reviews.append({
                "author":  r.get("author"),
                "content": r.get("content", "")[:300] + ("..." if len(r.get("content","")) > 300 else ""),
                "rating":  r.get("author_details", {}).get("rating"),
                "source":  "TMDB",
            })

        # OTT 편성 (JustWatch via TMDB)
        providers = get_providers(content_id, media_type)

        # 장르
        genres = [g.get("name") for g in detail.get("genres", [])]

        return jsonify({
            "id":           content_id,
            "media_type":   media_type,
            "title":        detail.get("title") or detail.get("name"),
            "tagline":      detail.get("tagline", ""),
            "overview":     detail.get("overview", ""),
            "poster":       TMDB_IMG_BASE + detail["poster_path"] if detail.get("poster_path") else None,
            "backdrop":     "https://image.tmdb.org/t/p/w1280" + detail["backdrop_path"] if detail.get("backdrop_path") else None,
            "rating":       round(detail.get("vote_average", 0), 1),
            "vote_count":   detail.get("vote_count", 0),
            "release":      detail.get("release_date") or detail.get("first_air_date", ""),
            "runtime":      detail.get("runtime") or detail.get("episode_run_time", [None])[0],
            "genres":       genres,
            "cast":         cast,
            "providers":    providers,
            "tmdb_reviews": tmdb_reviews,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/genres/<media_type>")
def api_genres(media_type):
    """장르 목록"""
    data = tmdb_get(f"/genre/{media_type}/list")
    if not data:
        return jsonify([])
    return jsonify(data.get("genres", []))

# ─────────────────────────────────────────
#  API — 자체 리뷰
# ─────────────────────────────────────────

@app.route("/api/reviews/<media_type>/<int:content_id>", methods=["GET"])
def get_site_reviews(media_type, content_id):
    key = f"{media_type}_{content_id}"
    return jsonify(REVIEWS.get(key, []))

@app.route("/api/reviews/<media_type>/<int:content_id>", methods=["POST"])
def create_site_review(media_type, content_id):
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "No data"}), 400

    author = data.get("author", "").strip()
    text   = data.get("text", "").strip()
    rating = data.get("rating")
    ott    = data.get("ott", "")   # 어떤 OTT에서 봤는지

    if not author or not text or rating is None:
        return jsonify({"error": "author, text, rating 필수"}), 400
    if not isinstance(rating, (int, float)) or not (1 <= rating <= 5):
        return jsonify({"error": "rating은 1~5 사이"}), 400

    key = f"{media_type}_{content_id}"
    if key not in REVIEWS:
        REVIEWS[key] = []

    review = {
        "id":      len(REVIEWS[key]) + 1,
        "author":  author,
        "text":    text,
        "rating":  rating,
        "ott":     ott,
        "source":  "site",
    }
    REVIEWS[key].append(review)
    return jsonify(review), 201

@app.route("/api/reviews/<media_type>/<int:content_id>/<int:review_id>", methods=["DELETE"])
def delete_site_review(media_type, content_id, review_id):
    key = f"{media_type}_{content_id}"
    reviews = REVIEWS.get(key, [])
    for i, r in enumerate(reviews):
        if r["id"] == review_id:
            reviews.pop(i)
            return jsonify({"message": "deleted"}), 200
    return jsonify({"error": "Not found"}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)