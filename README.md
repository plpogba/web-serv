# 🎬 CineReview

> A movie & TV show discovery and review web application powered by the TMDB API.

![Python](https://img.shields.io/badge/Python-3.x-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-3.x-black?logo=flask)
![TMDB](https://img.shields.io/badge/TMDB-API-01B4E4?logo=themoviedb)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 📌 Motivation

I built CineReview to practice building a full-stack web service with a real-world public API.
The goal was to go beyond just making things work — I focused on clean architecture,
proper documentation, and a maintainable codebase that could scale.

---

## 🖼️ Demo



![demo](./assets/cinereview1.gif)
![demo](./assets/cinereview2.gif)
---

## 🛠️ Tech Stack

| Technology | Reason |
|---|---|
| **Python / Flask** | Lightweight and flexible backend framework, ideal for REST API development |
| **TMDB API** | Rich, well-documented movie & TV data with no cost barrier |
| **Vanilla JS** | Kept the frontend dependency-free to focus on core logic |
| **Flasgger (Swagger UI)** | Auto-generates interactive API docs directly from docstrings — single source of truth |
| **Sphinx** | Produces a professional HTML documentation site from code docstrings |

---

## ✨ Key Features

- 🔍 **Search & Discovery** — Search movies and TV shows, or filter by genre and OTT provider
- 🎥 **Content Detail** — View detailed info including cast, runtime, and streaming availability
- ⭐ **Review System** — Write, view, and delete reviews with a 1–5 star rating
- 📄 **API Documentation** — Interactive Swagger UI available at `/apidocs`
- 📚 **Code Documentation** — Auto-generated Sphinx docs hosted on GitHub Pages

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/plpogba/web-serv.git
cd web-serv
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the server

```bash
flask --app app.app run --port 5001
```

### 4. Open in browser

| Page | URL |
|---|---|
| Main App | http://localhost:5001 |
| Swagger UI (API Docs) | http://localhost:5001/apidocs |

---

## 📂 Project Structure

```
web-serv/
├── app/
│   ├── app.py               # Flask routes & API endpoints
│   ├── tmdb_parser.py       # TMDB API response parser
│   ├── review_repository.py # In-memory review storage
│   ├── discover_params.py   # TMDB discover query builder
│   └── media_type_handler.py
├── docs/                    # Sphinx documentation source
├── tests/                   # Unit tests
├── requirements.txt
└── run.py
```

---

## 📖 Documentation

- 📚 **Code Docs (Sphinx):** [https://plpogba.github.io/web-serv/](https://plpogba.github.io/web-serv/)
- 🔌 **API Docs (Swagger):** Run the server and visit `/apidocs`

---

## 🧪 Running Tests

```bash
pytest tests/
```

---

## 💡 Lessons Learned

The most challenging part was designing a clean **Single Source of Truth** for documentation.
Early on, the API behavior and the docs were out of sync. By integrating Flasgger directly
into the route docstrings, any change to the code automatically reflected in the Swagger UI —
eliminating the risk of stale documentation entirely.

---

## 📬 Contact

Feel free to reach out via GitHub Issues or email at <kangjinoo@knu.ac.kr>

---

*Built with ❤️ as part of the 2026 Spring Open Source Programming course at Kyungpook National University.*