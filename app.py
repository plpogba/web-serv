from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/movies")
def movies():
    movie_list = [
        {"title": "인터스텔라", "genre": "SF", "rating": 4.8, "year": 2014},
        {"title": "기생충", "genre": "드라마", "rating": 4.9, "year": 2019},
        {"title": "어벤져스", "genre": "액션", "rating": 4.5, "year": 2018},
        {"title": "라라랜드", "genre": "로맨스", "rating": 4.6, "year": 2016},
        {"title": "조커", "genre": "드라마", "rating": 4.7, "year": 2019},
        {"title": "듄", "genre": "SF", "rating": 4.5, "year": 2021},
    ]
    return render_template("movies.html", movies=movie_list)

@app.route("/review")
def review():
    return render_template("review.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)