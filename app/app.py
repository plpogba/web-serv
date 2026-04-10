from flask import Flask, request, jsonify, render_template
from app.review_repository import ReviewRepository, ContentKey
from app.discover_params import DiscoverParams
from app.tmdb_parser import TmdbParser
from app.media_type_handler import HANDLERS
import urllib.request
import urllib.parse
import urllib.error
import json
import ssl
import logging

app = Flask(__name__)

# Logging configuration
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
#  Settings
# ─────────────────────────────────────────

TMDB_API_KEY  = "9ca27837eb1468b7e55e35038920d183"
TMDB_BASE     = "https://api.themoviedb.org/3"
LANGUAGE      = "ko-KR"

review_repo = ReviewRepository()
parser = TmdbParser()

# ─────────────────────────────────────────
#  SSL Context (Prevent certificate errors)
# ─────────────────────────────────────────

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode    = ssl.CERT_NONE

# ─────────────────────────────────────────
#  TMDB Helpers
# ─────────────────────────────────────────

def tmdb_get(path, extra_params=None):
    """Sends a GET request to the TMDB API and returns the JSON response.

    Args:
        path (str): TMDB API path (e.g., "/movie/123").
        extra_params (dict, optional): Additional query parameters. Defaults to None.

    Returns:
        dict or None: API response data. Returns None on error.
    """
    params = {"api_key": TMDB_API_KEY, "language": LANGUAGE}
    if extra_params:
        params.update(extra_params)
    url = f"{TMDB_BASE}{path}?{urllib.parse.urlencode(params)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CineReview/1.0"})
        with urllib.request.urlopen(req, timeout=10, context=SSL_CTX) as res:
            data = json.loads(res.read().decode("utf-8"))
            # Check for TMDB error responses (status_code field indicates an API error)
            if "status_code" in data and data.get("status_code") != 1:
                logger.error(f"TMDB API error: {data}")
                return None
            return data
    except Exception as e:
        logger.error(f"TMDB request failed: {str(e)}")
        return None

def safe_runtime(detail):
    """Safely extracts the runtime for a movie or TV show.

    Args:
        detail (dict): TMDB detail data.

    Returns:
        int or None: Runtime in minutes. Returns None if extraction fails.
    """
    return parser.parse_runtime(detail)

def format_content(item, media_type=None):
    """Converts TMDB item data into the internal format.

    Args:
        item (dict): TMDB item data.
        media_type (str, optional): Media type. Defaults to None.

    Returns:
        dict: Formatted data.
    """
    return parser.parse_list_item(item, media_type)

def get_providers(content_id, media_type):
    """Fetches OTT provider information for the content.

    Args:
        content_id (int): Content ID.
        media_type (str): Media type ("movie" or "tv").

    Returns:
        list: List of providers.
    """
    data = tmdb_get(f"/{media_type}/{content_id}/watch/providers")
    return parser.parse_providers(data)

# ─────────────────────────────────────────
#  Flask Error Handlers
# ─────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    """Renders the 404 error page.

    Args:
        e (Exception): Error object.

    Returns:
        tuple: (HTML template, status code).
    """
    return render_template("error.html", code=404, msg="Page not found."), 404

@app.errorhandler(500)
def server_error(e):
    """Renders the 500 server error page.

    Args:
        e (Exception): Error object.

    Returns:
        tuple: (HTML template, status code).
    """
    return render_template("error.html", code=500, msg=str(e)), 500

# ─────────────────────────────────────────
#  Page Routes
# ─────────────────────────────────────────

@app.route("/")
def index():
    """Renders the main page.

    Returns:
        str: HTML template.

    ---
    paths:
      /:
        get:
          summary: Get main page
          description: Renders the main page of the application.
          responses:
            200:
              description: Main page HTML
              content:
                text/html:
                  schema:
                    type: string
    """
    return render_template("index.html")

@app.route("/browse")
def browse():
    """Renders the browse page.

    Returns:
        str: HTML template.

    ---
    paths:
      /browse:
        get:
          summary: Get browse page
          description: Renders the browse page for content discovery.
          responses:
            200:
              description: Browse page HTML
              content:
                text/html:
                  schema:
                    type: string
    """
    return render_template("browse.html")

@app.route("/content/<media_type>/<int:content_id>")
def content_detail(media_type, content_id):
    """Renders the content detail page.

    Args:
        media_type (str): Media type ("movie" or "tv").
        content_id (int): Content ID.

    Returns:
        tuple: (HTML template, status code) or error template.

    ---
    paths:
      /content/{media_type}/{content_id}:
        get:
          summary: Get content detail page
          description: Renders the detail page for a specific content item.
          parameters:
            - name: media_type
              in: path
              required: true
              schema:
                type: string
                enum: [movie, tv]
              description: Type of media (movie or tv)
            - name: content_id
              in: path
              required: true
              schema:
                type: integer
              description: TMDB content ID
          responses:
            200:
              description: Content detail page HTML
              content:
                text/html:
                  schema:
                    type: string
            400:
              description: Invalid media type
              content:
                text/html:
                  schema:
                    type: string
    """
    if media_type not in HANDLERS:
        return render_template("error.html", code=400, msg="Invalid content type."), 400
    return render_template("detail.html",
                           content_id=content_id,
                           media_type=media_type)

@app.route("/review")
def review_page():
    """Renders the review page.

    Returns:
        str: HTML template.

    ---
    paths:
      /review:
        get:
          summary: Get review page
          description: Renders the page for creating reviews.
          responses:
            200:
              description: Review page HTML
              content:
                text/html:
                  schema:
                    type: string
    """
    return render_template("review.html")

# ─────────────────────────────────────────
#  API — Content
# ─────────────────────────────────────────

@app.route("/api/trending")
def api_trending():
    """Returns a list of trending content.

    Returns:
        flask.Response: JSON response.

    ---
    paths:
      /api/trending:
        get:
          summary: Get trending content
          description: Returns a list of currently trending movies and TV shows.
          responses:
            200:
              description: List of trending content
              content:
                application/json:
                  schema:
                    type: array
                    items:
                      $ref: '#/components/schemas/ContentItem'
    """
    data = tmdb_get("/trending/all/week")
    if not data:
        return jsonify([])
    items = [format_content(i) for i in data.get("results", [])]
    return jsonify([i for i in items if i])  # Remove None values

@app.route("/api/browse")
def api_browse():
    """Searches or discovers content.

    Query Parameters:
        type (str): Media type ("movie" or "tv").
        genre (str): Genre ID.
        ott (str): OTT provider ID.
        q (str): Search query string.
        page (str): Page number.

    Returns:
        flask.Response: JSON response.

    ---
    paths:
      /api/browse:
        get:
          summary: Browse or search content
          description: Searches for content or discovers content based on filters.
          parameters:
            - name: type
              in: query
              schema:
                type: string
                enum: [movie, tv]
                default: movie
              description: Type of media to browse
            - name: genre
              in: query
              schema:
                type: string
              description: Genre ID(s) separated by comma
            - name: ott
              in: query
              schema:
                type: string
              description: OTT provider ID
            - name: q
              in: query
              schema:
                type: string
              description: Search query string
            - name: page
              in: query
              schema:
                type: string
                default: "1"
              description: Page number
          responses:
            200:
              description: List of content with pagination info
              content:
                application/json:
                  schema:
                    type: object
                    properties:
                      results:
                        type: array
                        items:
                          $ref: '#/components/schemas/ContentItem'
                      total_pages:
                        type: integer
            400:
              description: Invalid media type
              content:
                application/json:
                  schema:
                    type: object
                    properties:
                      error:
                        type: string
            500:
              description: Server error
              content:
                application/json:
                  schema:
                    type: object
                    properties:
                      error:
                        type: string
                      results:
                        type: array
                        items: {}
                      total_pages:
                        type: integer
    """
    media_type = request.args.get("type", "movie")
    if media_type not in HANDLERS:
        return jsonify({"error": "Invalid media_type"}), 400
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
    """Returns detailed information for a specific content.

    Args:
        media_type (str): Media type ("movie" or "tv").
        content_id (int): Content ID.

    Returns:
        flask.Response: JSON response.

    ---
    paths:
      /api/content/{media_type}/{content_id}:
        get:
          summary: Get content details
          description: Returns detailed information for a specific movie or TV show.
          parameters:
            - name: media_type
              in: path
              required: true
              schema:
                type: string
                enum: [movie, tv]
              description: Type of media
            - name: content_id
              in: path
              required: true
              schema:
                type: integer
              description: TMDB content ID
          responses:
            200:
              description: Detailed content information
              content:
                application/json:
                  schema:
                    $ref: '#/components/schemas/ContentDetail'
            400:
              description: Invalid media type
              content:
                application/json:
                  schema:
                    type: object
                    properties:
                      error:
                        type: string
            404:
              description: Content not found
              content:
                application/json:
                  schema:
                    type: object
                    properties:
                      error:
                        type: string
            500:
              description: Server error
              content:
                application/json:
                  schema:
                    type: object
                    properties:
                      error:
                        type: string
    """
    logger.info(f"Requesting content detail: {media_type}/{content_id}")
    try:
        if media_type not in HANDLERS:
            logger.error(f"Invalid media_type: {media_type}")
            return jsonify({"error": "Invalid media_type"}), 400

        # Basic Info
        logger.info("Fetching detail from TMDB")
        detail = tmdb_get(f"/{media_type}/{content_id}")
        if not detail:
            logger.error("Detail not found")
            return jsonify({"error": "Content not found."}), 404

        # Credits Info
        logger.info("Fetching credits from TMDB")
        credits_data = tmdb_get(f"/{media_type}/{content_id}/credits")
        if credits_data:
            detail["credits"] = credits_data

        # Reviews Info
        logger.info("Fetching reviews from TMDB")
        reviews_data = tmdb_get(f"/{media_type}/{content_id}/reviews")
        if reviews_data:
            detail["reviews"] = reviews_data

        # OTT Providers
        logger.info("Fetching providers from TMDB")
        providers_data = tmdb_get(f"/{media_type}/{content_id}/watch/providers")

        # Transform data using parser
        logger.info("Parsing data")
        result = parser.parse_detail(content_id, media_type, detail, providers_data)

        logger.info("Returning result")
        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in api_content_detail: {str(e)}", exc_info=True)
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route("/api/genres/<media_type>")
def api_genres(media_type):
    """Returns the list of genres for a media type.

    Args:
        media_type (str): Media type ("movie" or "tv").

    Returns:
        flask.Response: JSON response.

    ---
    paths:
      /api/genres/{media_type}:
        get:
          summary: Get genres for media type
          description: Returns the list of available genres for movies or TV shows.
          parameters:
            - name: media_type
              in: path
              required: true
              schema:
                type: string
                enum: [movie, tv]
              description: Type of media
          responses:
            200:
              description: List of genres
              content:
                application/json:
                  schema:
                    type: array
                    items:
                      type: object
                      properties:
                        id:
                          type: integer
                        name:
                          type: string
            400:
              description: Invalid media type
              content:
                application/json:
                  schema:
                    type: object
                    properties:
                      error:
                        type: string
    """
    if media_type not in HANDLERS:
        return jsonify({"error": "Invalid media_type"}), 400
    data = tmdb_get(f"/genre/{media_type}/list")
    if not data:
        return jsonify([])
    return jsonify(data.get("genres", []))

# ─────────────────────────────────────────
#  API — Site-specific Reviews
# ─────────────────────────────────────────

@app.route("/api/reviews/<media_type>/<int:content_id>", methods=["GET"])
def get_site_reviews(media_type, content_id):
    """Returns the list of site reviews for the content.

    Args:
        media_type (str): Media type ("movie" or "tv").
        content_id (int): Content ID.

    Returns:
        flask.Response: JSON response.

    ---
    paths:
      /api/reviews/{media_type}/{content_id}:
        get:
          summary: Get site reviews for content
          description: Returns the list of user reviews for a specific content item.
          parameters:
            - name: media_type
              in: path
              required: true
              schema:
                type: string
                enum: [movie, tv]
              description: Type of media
            - name: content_id
              in: path
              required: true
              schema:
                type: integer
              description: TMDB content ID
          responses:
            200:
              description: List of reviews
              content:
                application/json:
                  schema:
                    type: array
                    items:
                      $ref: '#/components/schemas/Review'
            400:
              description: Invalid media type
              content:
                application/json:
                  schema:
                    type: object
                    properties:
                      error:
                        type: string
    """
    if media_type not in HANDLERS:
        return jsonify({"error": "Invalid media_type"}), 400
    key = ContentKey(media_type, content_id)
    return jsonify(review_repo.get(key))

@app.route("/api/reviews/<media_type>/<int:content_id>", methods=["POST"])
def create_site_review(media_type, content_id):
    """Creates a new site review for the content.

    Args:
        media_type (str): Media type ("movie" or "tv").
        content_id (int): Content ID.

    Request Body:
        JSON with keys: author (str), text (str), rating (int/float), ott (str, optional).

    Returns:
        flask.Response: JSON response.

    ---
    paths:
      /api/reviews/{media_type}/{content_id}:
        post:
          summary: Create a new review
          description: Creates a new user review for a specific content item.
          parameters:
            - name: media_type
              in: path
              required: true
              schema:
                type: string
                enum: [movie, tv]
              description: Type of media
            - name: content_id
              in: path
              required: true
              schema:
                type: integer
              description: TMDB content ID
          requestBody:
            required: true
            content:
              application/json:
                schema:
                  type: object
                  required:
                    - author
                    - text
                    - rating
                  properties:
                    author:
                      type: string
                      description: Review author name
                    text:
                      type: string
                      description: Review content
                    rating:
                      type: number
                      minimum: 1
                      maximum: 5
                      description: Rating from 1 to 5
                    ott:
                      type: string
                      description: OTT provider name (optional)
          responses:
            201:
              description: Review created successfully
              content:
                application/json:
                  schema:
                    $ref: '#/components/schemas/Review'
            400:
              description: Invalid input or media type
              content:
                application/json:
                  schema:
                    type: object
                    properties:
                      error:
                        type: string
    """
    if media_type not in HANDLERS:
        return jsonify({"error": "Invalid media_type"}), 400
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "No data provided"}), 400
    author = (data.get("author") or "").strip()
    text   = (data.get("text")   or "").strip()
    rating = data.get("rating")
    ott    = data.get("ott", "")
    if not author or not text or rating is None:
        return jsonify({"error": "author, text, and rating are required"}), 400
    if not isinstance(rating, (int, float)) or not (1 <= rating <= 5):
        return jsonify({"error": "rating must be between 1 and 5"}), 400
    key = ContentKey(media_type, content_id)
    review = review_repo.add(key, {
        "author": author, "text": text, "rating": rating, "ott": ott
    })
    return jsonify(review), 201

@app.route("/api/reviews/<media_type>/<int:content_id>/<int:review_id>", methods=["DELETE"])
def delete_site_review(media_type, content_id, review_id):
    """Deletes a specific site review for the content.

    Args:
        media_type (str): Media type ("movie" or "tv").
        content_id (int): Content ID.
        review_id (int): Review ID.

    Returns:
        flask.Response: JSON response.

    ---
    paths:
      /api/reviews/{media_type}/{content_id}/{review_id}:
        delete:
          summary: Delete a review
          description: Deletes a specific user review for a content item.
          parameters:
            - name: media_type
              in: path
              required: true
              schema:
                type: string
                enum: [movie, tv]
              description: Type of media
            - name: content_id
              in: path
              required: true
              schema:
                type: integer
              description: TMDB content ID
            - name: review_id
              in: path
              required: true
              schema:
                type: integer
              description: Review ID
          responses:
            200:
              description: Review deleted successfully
              content:
                application/json:
                  schema:
                    type: object
                    properties:
                      message:
                        type: string
            400:
              description: Invalid media type
              content:
                application/json:
                  schema:
                    type: object
                    properties:
                      error:
                        type: string
            404:
              description: Review not found
              content:
                application/json:
                  schema:
                    type: object
                    properties:
                      error:
                        type: string
    """
    if media_type not in HANDLERS:
        return jsonify({"error": "Invalid media_type"}), 400
    key = ContentKey(media_type, content_id)
    if review_repo.delete(key, review_id):
        return jsonify({"message": "deleted"}), 200
    return jsonify({"error": "Not found"}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)