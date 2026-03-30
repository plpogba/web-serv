from flask import Flask, request, jsonify

app = Flask(__name__)

# ─────────────────────────────────────────
#  가상 DB
# ─────────────────────────────────────────

DATABASE = [
    {
        "id": i,
        "title": f"Movie {i}",
        "genre": ["Action", "Romance", "Horror", "SF"][i % 4],
        "description": f"This is a detailed description for Movie {i}.",
        "rating": round(3.0 + (i % 3) * 0.5, 1),
        "year": 2000 + i,
    }
    for i in range(1, 21)
]

REVIEWS = []
WISHLIST = []

# ─────────────────────────────────────────
#  비즈니스 로직 함수 (테스트에서 @patch 대상)
# ─────────────────────────────────────────

def get_movies_from_db(movie_id_or_page, limit=None):
    # limit=None -> 상세 조회 (ID 기반), limit 있음 -> 목록 조회 (페이지네이션)
    if limit is None:
        return next((m for m in DATABASE if m["id"] == movie_id_or_page), None)
    start = (movie_id_or_page - 1) * limit
    end = start + limit
    return DATABASE[start:end]

def get_movie_by_id(movie_id):
    return next((m for m in DATABASE if m["id"] == movie_id), None)

def search_movies_from_db(query):
    if not query:
        return []
    query = query.lower()
    return [m for m in DATABASE if query in m["title"].lower()]

def filter_movies_from_db(genre):
    return [m for m in DATABASE if m["genre"].lower() == genre.lower()]

def get_reviews_from_db(movie_id):
    return [r for r in REVIEWS if r["movie_id"] == movie_id]

def delete_review_from_db(review_id):
    for i, r in enumerate(REVIEWS):
        if r["id"] == review_id:
            REVIEWS.pop(i)
            return True
    return False

def get_wishlist_from_db():
    result = []
    for movie_id in WISHLIST:
        movie = get_movie_by_id(movie_id)
        if movie:
            result.append(movie)
    return result

# ─────────────────────────────────────────
#  API 라우트
# ─────────────────────────────────────────

# UR-01 영화 목록 조회
@app.route("/api/movies", methods=["GET"])
def get_movies():
    try:
        page  = int(request.args.get("page",  "1"))
        limit = int(request.args.get("limit", "10"))
        if page < 1 or limit < 1 or limit > 100:
            return jsonify({"error": "Invalid range"}), 400
        movies = get_movies_from_db(page, limit)
        return jsonify(movies), 200
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid parameter type"}), 400
    except Exception:
        return jsonify({"message": "Internal Server Error"}), 500

# UR-02 영화 검색
@app.route("/api/movies/search", methods=["GET"])
def search_movies():
    try:
        query = request.args.get("q", "").strip()
        if not query:
            return jsonify({"error": "Search query is required"}), 400
        results = search_movies_from_db(query)
        return jsonify(results), 200
    except Exception:
        return jsonify({"message": "Internal Server Error"}), 500

# UR-03 장르별 필터링
@app.route("/api/movies/filter", methods=["GET"])
def filter_by_genre():
    try:
        genre = request.args.get("genre", "").strip()
        if not genre:
            return jsonify({"error": "genre parameter is required"}), 400
        results = filter_movies_from_db(genre)
        return jsonify(results), 200
    except Exception:
        return jsonify({"message": "Internal Server Error"}), 500

# UR-04 영화 상세 정보 조회
@app.route("/api/movies/<int:movie_id>", methods=["GET"])
def get_movie_detail(movie_id):
    try:
        movie = get_movies_from_db(movie_id)
        if movie is None:
            return jsonify({"error": "Movie not found"}), 404
        return jsonify(movie), 200
    except Exception:
        return jsonify({"message": "Internal Server Error"}), 500

# UR-05 리뷰 작성
@app.route("/api/reviews", methods=["POST"])
def create_review():
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "No input data provided"}), 400
        movie_id = data.get("movie_id")
        content  = data.get("content")
        rating   = data.get("rating")
        if movie_id is None or content is None or rating is None:
            return jsonify({"error": "Missing required fields"}), 400
        if not isinstance(rating, (int, float)):
            return jsonify({"error": "Rating must be a number"}), 400
        if not (1 <= rating <= 5):
            return jsonify({"error": "Rating must be between 1 and 5"}), 400
        movie = get_movie_by_id(movie_id)
        if movie is None:
            return jsonify({"error": "Movie not found"}), 404
        new_review = {"id": len(REVIEWS) + 1, "movie_id": movie_id, "content": content, "rating": rating}
        REVIEWS.append(new_review)
        return jsonify({"message": "Review created successfully", "review": new_review}), 201
    except Exception:
        return jsonify({"message": "Internal Server Error"}), 500

# UR-06 리뷰 조회
@app.route("/api/movies/<int:movie_id>/reviews", methods=["GET"])
def get_movie_reviews(movie_id):
    try:
        movie = get_movie_by_id(movie_id)
        if movie is None:
            return jsonify({"error": "Movie not found"}), 404
        reviews = get_reviews_from_db(movie_id)
        return jsonify(reviews), 200
    except Exception:
        return jsonify({"message": "Internal Server Error"}), 500

# UR-07 위시리스트 추가
@app.route("/api/wishlist", methods=["POST"])
def add_wishlist():
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "No input data provided"}), 400
        movie_id = data.get("movie_id")
        if movie_id is None:
            return jsonify({"error": "movie_id is required"}), 400
        movie = get_movie_by_id(movie_id)
        if movie is None:
            return jsonify({"error": "Movie not found"}), 404
        if movie_id in WISHLIST:
            return jsonify({"error": "Already in wishlist"}), 409
        WISHLIST.append(movie_id)
        return jsonify({"message": "Added to wishlist", "movie_id": movie_id}), 201
    except Exception:
        return jsonify({"message": "Internal Server Error"}), 500

# UR-07 위시리스트 삭제
@app.route("/api/wishlist/<int:movie_id>", methods=["DELETE"])
def remove_wishlist(movie_id):
    try:
        if movie_id not in WISHLIST:
            return jsonify({"error": "Not in wishlist"}), 404
        WISHLIST.remove(movie_id)
        return jsonify({"message": "Removed from wishlist"}), 200
    except Exception:
        return jsonify({"message": "Internal Server Error"}), 500

# UR-08 위시리스트 조회
@app.route("/api/wishlist", methods=["GET"])
def get_wishlist():
    try:
        result = get_wishlist_from_db()
        return jsonify(result), 200
    except Exception:
        return jsonify({"message": "Internal Server Error"}), 500

# UR-09 리뷰 삭제
@app.route("/api/reviews/<int:review_id>", methods=["DELETE"])
def delete_review(review_id):
    try:
        deleted = delete_review_from_db(review_id)
        if not deleted:
            return jsonify({"error": "Review not found"}), 404
        return jsonify({"message": "Review deleted successfully"}), 200
    except Exception:
        return jsonify({"message": "Internal Server Error"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)