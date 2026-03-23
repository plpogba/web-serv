from flask import Flask, request, jsonify

app = Flask(__name__)

# 1. 가상 DB
DATABASE = [
    {
        "id": i, 
        "title": f"Movie {i}", 
        "description": f"This is a detailed description for Movie {i}.", 
        "rating": 4.5
    } for i in range(1, 21)
]

# 2. 비즈니스 로직 함수들
def get_movies_from_db(movie_id_or_page, limit=None):
    if limit is None:
        return next((m for m in DATABASE if m["id"] == movie_id_or_page), None)
    start = (movie_id_or_page - 1) * limit
    end = start + limit
    return DATABASE[start:end]

def search_movies_from_db(query):
    if not query:
        return []
    query = query.lower()
    return [m for m in DATABASE if query in m["title"].lower()]

# 3. API 라우트들
@app.route("/api/movies", methods=["GET"])
def get_movies():
    try:
        page = int(request.args.get("page", "1"))
        limit = int(request.args.get("limit", "10"))
        if page < 1 or limit < 1 or limit > 100:
            return jsonify({"error": "Invalid range"}), 400
        movies = get_movies_from_db(page, limit)
        return jsonify(movies), 200
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid parameter type"}), 400
    except Exception:
        return jsonify({"message": "Internal Server Error"}), 500

@app.route("/api/movies/<int:movie_id>", methods=["GET"])
def get_movie_detail(movie_id):
    try:
        movie = get_movies_from_db(movie_id)
        if movie is None:
            return jsonify({"error": "Movie not found"}), 404
        return jsonify(movie), 200
    except Exception:
        return jsonify({"message": "Internal Server Error"}), 500

@app.route("/api/movies/search", methods=["GET"]) # 이제 이 데코레이터는 아래 search_movies를 정상적으로 가리킵니다.
def search_movies():
    try:
        query = request.args.get("q", "").strip()
        if not query:
            return jsonify({"error": "Search query is required"}), 400
        
        # 여기서 인자를 넘겨주며 함수를 호출하므로 TypeError가 나지 않습니다.
        results = search_movies_from_db(query)
        return jsonify(results), 200
    except Exception:
        return jsonify({"message": "Internal Server Error"}), 500

# 리뷰를 저장할 가상 DB (리스트)
REVIEWS = []

@app.route("/api/reviews", methods=["POST"])
def create_review():
    """
    영화 리뷰 등록 API
    1. 클라이언트로부터 JSON 데이터를 받음
    2. 필수 필드(movie_id, content, rating) 확인
    3. 별점 범위(1~5) 검증
    4. 성공 시 201 Created 반환
    """
    try:
        # JSON 데이터 추출
        data = request.get_json()
        if not data:
            return jsonify({"error": "No input data provided"}), 400

        movie_id = data.get("movie_id")
        content = data.get("content")
        rating = data.get("rating")

        # 1. 필수 필드 검증 (Missing fields)
        if movie_id is None or content is None or rating is None:
            return jsonify({"error": "Missing required fields"}), 400

        # 2. 별점 범위 검증 (UR-05 Code Red)
        if not (1 <= rating <= 5):
            return jsonify({"error": "Rating must be between 1 and 5"}), 400

        # 3. 데이터 저장
        new_review = {
            "id": len(REVIEWS) + 1,
            "movie_id": movie_id,
            "content": content,
            "rating": rating
        }
        REVIEWS.append(new_review)

        # 4. 성공 응답 (201 Created)
        return jsonify({
            "message": "Review created successfully",
            "review": new_review
        }), 201

    except Exception as e:
        return jsonify({"message": "Internal Server Error"}), 500

@app.route("/api/movies/<int:movie_id>/reviews", methods=["GET"])
def get_movie_reviews(movie_id):
    """
    특정 영화의 리뷰 목록 조회 API
    """
    # 1. 먼저 영화가 실제 DATABASE에 있는지 확인 (404 처리)
    movie = next((m for m in DATABASE if m["id"] == movie_id), None)
    if not movie:
        return jsonify({"error": "Movie not found"}), 404

    # 2. REVIEWS 리스트에서 해당 movie_id를 가진 리뷰만 골라내기
    # (지금은 REVIEWS가 비어있으므로 []가 반환되겠지만, 로직은 미리 짜둡니다)
    movie_reviews = [r for r in REVIEWS if r["movie_id"] == movie_id]

    return jsonify(movie_reviews), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)