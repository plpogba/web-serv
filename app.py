from flask import Flask, request, jsonify, render_template
import urllib.request
import urllib.parse
import urllib.error
import json
import ssl

app = Flask(__name__)

# ─────────────────────────────────────────
#  설정
# ─────────────────────────────────────────

TMDB_API_KEY  = "9ca27837eb1468b7e55e35038920d183"
TMDB_BASE     = "https://api.themoviedb.org/3"
TMDB_IMG_BASE = "https://image.tmdb.org/t/p/w500"
LANGUAGE      = "ko-KR"

OTT_PROVIDERS = {
    8:   {"name": "Netflix",      "color": "#E50914"},
    97:  {"name": "Watcha",       "color": "#FF0558"},
    356: {"name": "Coupang Play", "color": "#1ABCFE"},
    337: {"name": "Disney+",      "color": "#113CCF"},
    2:   {"name": "Apple TV+",    "color": "#555555"},
}

REVIEWS = {}  # { "movie_123": [{id, author, rating, text, ott}] }

# ─────────────────────────────────────────
#  SSL 컨텍스트 (인증서 오류 방지)
# ─────────────────────────────────────────

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode    = ssl.CERT_NONE

# ─────────────────────────────────────────
#  TMDB 헬퍼
# ─────────────────────────────────────────

def tmdb_get(path, extra_params=None):
    params = {"api_key": TMDB_API_KEY, "language": LANGUAGE}
    if extra_params:
        params.update(extra_params)
    url = f"{TMDB_BASE}{path}?{urllib.parse.urlencode(params)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CineReview/1.0"})
        with urllib.request.urlopen(req, timeout=10, context=SSL_CTX) as res:
            data = json.loads(res.read().decode("utf-8"))
            # TMDB 오류 응답 체크 (status_code 필드가 있으면 API 오류)
            if "status_code" in data and data.get("status_code") != 1:
                return None
            return data
    except Exception:
        return None

def safe_runtime(detail):
    """영화/TV 상영 시간 안전하게 추출"""
    rt = detail.get("runtime")
    if rt:
        return rt
    ep = detail.get("episode_run_time")
    if ep and isinstance(ep, list) and len(ep) > 0:
        return ep[0]
    return None

def format_content(item, media_type=None):
    mt = media_type or item.get("media_type", "movie")
    if mt not in ("movie", "tv"):   # person 등 제외
        return None
    return {
        "id":         item.get("id"),
        "media_type": mt,
        "title":      item.get("title") or item.get("name", ""),
        "overview":   item.get("overview", ""),
        "poster":     TMDB_IMG_BASE + item["poster_path"] if item.get("poster_path") else None,
        "backdrop":   "https://image.tmdb.org/t/p/w1280" + item["backdrop_path"] if item.get("backdrop_path") else None,
        "rating":     round(float(item.get("vote_average") or 0), 1),
        "vote_count": item.get("vote_count", 0),
        "release":    item.get("release_date") or item.get("first_air_date", ""),
        "genre_ids":  item.get("genre_ids", []),
    }

def get_providers(content_id, media_type):
    data = tmdb_get(f"/{media_type}/{content_id}/watch/providers")
    if not data:
        return []
    kr = data.get("results", {}).get("KR", {})
    provider_list = (kr.get("flatrate") or []) + (kr.get("buy") or []) + (kr.get("rent") or [])
    seen, result = set(), []
    for p in provider_list:
        pid = p.get("provider_id")
        if pid in OTT_PROVIDERS and pid not in seen:
            seen.add(pid)
            info = OTT_PROVIDERS[pid].copy()
            logo = p.get("logo_path", "")
            info["logo_url"] = f"https://image.tmdb.org/t/p/w92{logo}" if logo else ""
            result.append(info)
    return result

# ─────────────────────────────────────────
#  Flask 오류 핸들러
# ─────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return render_template("error.html", code=404, msg="페이지를 찾을 수 없습니다."), 404

@app.errorhandler(500)
def server_error(e):
    return render_template("error.html", code=500, msg=str(e)), 500

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
    if media_type not in ("movie", "tv"):
        return render_template("error.html", code=400, msg="잘못된 콘텐츠 유형입니다."), 400
    return render_template("detail.html",
                           content_id=content_id,
                           media_type=media_type)

@app.route("/review")
def review_page():
    return render_template("review.html")

# ─────────────────────────────────────────
#  API — 콘텐츠
# ─────────────────────────────────────────

@app.route("/api/trending")
def api_trending():
    data = tmdb_get("/trending/all/week")
    if not data:
        return jsonify([])
    items = [format_content(i) for i in data.get("results", [])]
    return jsonify([i for i in items if i])  # None 제거

@app.route("/api/browse")
def api_browse():
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
            formatted = format_content(item, mt)
            if formatted:
                results.append(formatted)

        return jsonify({"results": results, "total_pages": data.get("total_pages", 1)})
    except Exception as e:
        return jsonify({"error": str(e), "results": [], "total_pages": 0}), 500

@app.route("/api/content/<media_type>/<int:content_id>")
def api_content_detail(media_type, content_id):
    try:
        if media_type not in ("movie", "tv"):
            return jsonify({"error": "잘못된 media_type"}), 400

        # 기본 정보 (credits, reviews 함께 요청)
        detail = tmdb_get(
            f"/{media_type}/{content_id}",
            {"append_to_response": "credits,reviews"}
        )
        if not detail:
            return jsonify({"error": "콘텐츠를 찾을 수 없습니다."}), 404

        # 출연진
        cast = []
        for c in (detail.get("credits") or {}).get("cast", [])[:10]:
            cast.append({
                "name":      c.get("name", ""),
                "character": c.get("character", ""),
                "photo":     TMDB_IMG_BASE + c["profile_path"] if c.get("profile_path") else None,
            })

        # TMDB 리뷰
        tmdb_reviews = []
        for r in (detail.get("reviews") or {}).get("results", [])[:5]:
            content_text = r.get("content", "")
            tmdb_reviews.append({
                "author":  r.get("author", "익명"),
                "content": content_text[:400] + ("..." if len(content_text) > 400 else ""),
                "rating":  (r.get("author_details") or {}).get("rating"),
            })

        # OTT 편성
        providers = get_providers(content_id, media_type)

        # 장르
        genres = [g["name"] for g in (detail.get("genres") or [])]

        return jsonify({
            "id":           content_id,
            "media_type":   media_type,
            "title":        detail.get("title") or detail.get("name") or "제목 없음",
            "tagline":      detail.get("tagline") or "",
            "overview":     detail.get("overview") or "줄거리 정보 없음",
            "poster":       TMDB_IMG_BASE + detail["poster_path"] if detail.get("poster_path") else None,
            "backdrop":     "https://image.tmdb.org/t/p/w1280" + detail["backdrop_path"] if detail.get("backdrop_path") else None,
            "rating":       round(float(detail.get("vote_average") or 0), 1),
            "vote_count":   detail.get("vote_count") or 0,
            "release":      detail.get("release_date") or detail.get("first_air_date") or "",
            "runtime":      safe_runtime(detail),   # ← 수정된 안전한 추출
            "genres":       genres,
            "cast":         cast,
            "providers":    providers,
            "tmdb_reviews": tmdb_reviews,
        })

    except Exception as e:
        return jsonify({"error": f"서버 오류: {str(e)}"}), 500

@app.route("/api/genres/<media_type>")
def api_genres(media_type):
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
        return jsonify({"error": "데이터 없음"}), 400
    author = (data.get("author") or "").strip()
    text   = (data.get("text")   or "").strip()
    rating = data.get("rating")
    ott    = data.get("ott", "")
    if not author or not text or rating is None:
        return jsonify({"error": "author, text, rating 필수"}), 400
    if not isinstance(rating, (int, float)) or not (1 <= rating <= 5):
        return jsonify({"error": "rating은 1~5 사이"}), 400
    key = f"{media_type}_{content_id}"
    if key not in REVIEWS:
        REVIEWS[key] = []
    review = {"id": len(REVIEWS[key]) + 1, "author": author, "text": text, "rating": rating, "ott": ott}
    REVIEWS[key].append(review)
    return jsonify(review), 201

@app.route("/api/reviews/<media_type>/<int:content_id>/<int:review_id>", methods=["DELETE"])
def delete_site_review(media_type, content_id, review_id):
    key = f"{media_type}_{content_id}"
    for i, r in enumerate(REVIEWS.get(key, [])):
        if r["id"] == review_id:
            REVIEWS[key].pop(i)
            return jsonify({"message": "deleted"}), 200
    return jsonify({"error": "Not found"}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)