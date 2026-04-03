from flask import Flask, request, jsonify, render_template
from review_repository import ReviewRepository, ContentKey
from discover_params import DiscoverParams
from tmdb_parser import TmdbParser
from media_type_handler import HANDLERS
import urllib.request
import urllib.parse
import urllib.error
import json
import ssl
import logging

app = Flask(__name__)

# 로깅 설정
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ─────────────────────────────────────────
#  설정
# ─────────────────────────────────────────

TMDB_API_KEY  = "9ca27837eb1468b7e55e35038920d183"
TMDB_BASE     = "https://api.themoviedb.org/3"
LANGUAGE      = "ko-KR"

review_repo = ReviewRepository()
parser = TmdbParser()

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
                logger.error(f"TMDB API error: {data}")
                return None
            return data
    except Exception as e:
        logger.error(f"TMDB request failed: {str(e)}")
        return None

def safe_runtime(detail):
    """영화/TV 상영 시간 안전하게 추출"""
    return parser.parse_runtime(detail)

def format_content(item, media_type=None):
    return parser.parse_list_item(item, media_type)

def get_providers(content_id, media_type):
    data = tmdb_get(f"/{media_type}/{content_id}/watch/providers")
    return parser.parse_providers(data)

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
    if media_type not in HANDLERS:
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
    if media_type not in HANDLERS:
        return jsonify({"error": "잘못된 media_type"}), 400
    genre      = request.args.get("genre", "")
    ott        = request.args.get("ott", "")
    query      = request.args.get("q", "").strip()
    page       = request.args.get("page", "1")

    try:
        if query:
            data = tmdb_get("/search/multi", {"query": query, "page": page})
        else:
            params = DiscoverParams(genre=genre, page=page, ott=ott)
            data = tmdb_get(f"/discover/{media_type}", params.to_dict())

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
    logger.info(f"Requesting content detail: {media_type}/{content_id}")
    try:
        if media_type not in HANDLERS:
            logger.error(f"Invalid media_type: {media_type}")
            return jsonify({"error": "잘못된 media_type"}), 400

        # 기본 정보
        logger.info("Fetching detail from TMDB")
        detail = tmdb_get(f"/{media_type}/{content_id}")
        if not detail:
            logger.error("Detail not found")
            return jsonify({"error": "콘텐츠를 찾을 수 없습니다."}), 404

        # credits 정보
        logger.info("Fetching credits from TMDB")
        credits_data = tmdb_get(f"/{media_type}/{content_id}/credits")
        if credits_data:
            detail["credits"] = credits_data

        # reviews 정보
        logger.info("Fetching reviews from TMDB")
        reviews_data = tmdb_get(f"/{media_type}/{content_id}/reviews")
        if reviews_data:
            detail["reviews"] = reviews_data

        # OTT 편성
        logger.info("Fetching providers from TMDB")
        providers_data = tmdb_get(f"/{media_type}/{content_id}/watch/providers")

        # 파서로 데이터 변환
        logger.info("Parsing data")
        result = parser.parse_detail(content_id, media_type, detail, providers_data)

        logger.info("Returning result")
        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in api_content_detail: {str(e)}", exc_info=True)
        return jsonify({"error": f"서버 오류: {str(e)}"}), 500

@app.route("/api/genres/<media_type>")
def api_genres(media_type):
    if media_type not in HANDLERS:
        return jsonify({"error": "잘못된 media_type"}), 400
    data = tmdb_get(f"/genre/{media_type}/list")
    if not data:
        return jsonify([])
    return jsonify(data.get("genres", []))

# ─────────────────────────────────────────
#  API — 자체 리뷰
# ─────────────────────────────────────────

@app.route("/api/reviews/<media_type>/<int:content_id>", methods=["GET"])
def get_site_reviews(media_type, content_id):
    if media_type not in HANDLERS:
        return jsonify({"error": "잘못된 media_type"}), 400
    key = ContentKey(media_type, content_id)
    return jsonify(review_repo.get(key))

@app.route("/api/reviews/<media_type>/<int:content_id>", methods=["POST"])
def create_site_review(media_type, content_id):
    if media_type not in HANDLERS:
        return jsonify({"error": "잘못된 media_type"}), 400
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
    key = ContentKey(media_type, content_id)
    review = review_repo.add(key, {
        "author": author, "text": text, "rating": rating, "ott": ott
    })
    return jsonify(review), 201

@app.route("/api/reviews/<media_type>/<int:content_id>/<int:review_id>", methods=["DELETE"])
def delete_site_review(media_type, content_id, review_id):
    if media_type not in HANDLERS:
        return jsonify({"error": "잘못된 media_type"}), 400
    key = ContentKey(media_type, content_id)
    if review_repo.delete(key, review_id):
        return jsonify({"message": "deleted"}), 200
    return jsonify({"error": "Not found"}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)