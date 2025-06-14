from flask import Flask, jsonify
from flask_cors import CORS
import requests
import threading
from datetime import datetime
import os
import time

app = Flask(__name__)
CORS(app)

TMDB_API_KEY = "29dfffa9ae088178fa088680b67ce583"
TMDB_BASE_URL = "https://api.themoviedb.org/3"
INDIAN_LANGUAGES = {"hi", "ml", "ta", "te", "kn"}

malayalam_movies_cache = []
hindi_movies_cache = []
trending_movies_cache = []

# ---------------------- Fetch Functions ----------------------

def fetch_malayalam_movies():
    global malayalam_movies_cache
    today = datetime.now().strftime("%Y-%m-%d")
    final_movies = []
    for page in range(1, 1000):
        time.sleep(0.5)  # Prevent TMDB ratelimit
        params = {
            "api_key": TMDB_API_KEY,
            "with_original_language": "ml",
            "sort_by": "release_date.desc",
            "release_date.lte": today,
            "region": "IN",
            "page": page
        }
        try:
            response = requests.get(f"{TMDB_BASE_URL}/discover/movie", params=params)
            results = response.json().get("results", [])
            if not results:
                break
            for movie in results:
                movie_id = movie.get("id")
                title = movie.get("title")
                if not movie_id or not title:
                    continue
                prov_response = requests.get(f"{TMDB_BASE_URL}/movie/{movie_id}/watch/providers", params={"api_key": TMDB_API_KEY})
                prov_data = prov_response.json()
                if "results" in prov_data and "IN" in prov_data["results"] and "flatrate" in prov_data["results"]["IN"]:
                    ext_response = requests.get(f"{TMDB_BASE_URL}/movie/{movie_id}/external_ids", params={"api_key": TMDB_API_KEY})
                    imdb_id = ext_response.json().get("imdb_id")
                    if imdb_id and imdb_id.startswith("tt"):
                        movie["imdb_id"] = imdb_id
                        final_movies.append(movie)
        except Exception as e:
            print("Error (malayalam)", e)
            break
    # Deduplicate
    seen = set()
    malayalam_movies_cache = [m for m in final_movies if not (m["imdb_id"] in seen or seen.add(m["imdb_id"]))]
    print(f"[CACHE] Fetched {len(malayalam_movies_cache)} Malayalam movies ✅")

def fetch_hindi_movies():
    global hindi_movies_cache
    today = datetime.now().strftime("%Y-%m-%d")
    final_movies = []
    for page in range(1, 1000):
        time.sleep(0.5)
        params = {
            "api_key": TMDB_API_KEY,
            "with_original_language": "hi",
            "sort_by": "release_date.desc",
            "release_date.lte": today,
            "region": "IN",
            "page": page
        }
        try:
            response = requests.get(f"{TMDB_BASE_URL}/discover/movie", params=params)
            results = response.json().get("results", [])
            if not results:
                break
            for movie in results:
                movie_id = movie.get("id")
                title = movie.get("title")
                if not movie_id or not title:
                    continue
                prov_response = requests.get(f"{TMDB_BASE_URL}/movie/{movie_id}/watch/providers", params={"api_key": TMDB_API_KEY})
                prov_data = prov_response.json()
                if "results" in prov_data and "IN" in prov_data["results"] and "flatrate" in prov_data["results"]["IN"]:
                    ext_response = requests.get(f"{TMDB_BASE_URL}/movie/{movie_id}/external_ids", params={"api_key": TMDB_API_KEY})
                    imdb_id = ext_response.json().get("imdb_id")
                    if imdb_id and imdb_id.startswith("tt"):
                        movie["imdb_id"] = imdb_id
                        final_movies.append(movie)
        except Exception as e:
            print("Error (hindi)", e)
            break
    seen = set()
    hindi_movies_cache = [m for m in final_movies if not (m["imdb_id"] in seen or seen.add(m["imdb_id"]))]
    print(f"[CACHE] Fetched {len(hindi_movies_cache)} Hindi movies ✅")

def fetch_trending_movies():
    global trending_movies_cache
    today = datetime.now().strftime("%Y-%m-%d")
    final_movies = []
    seen_ids = set()
    page = 1
    while len(final_movies) < 100:
        time.sleep(0.5)
        params = {
            "api_key": TMDB_API_KEY,
            "sort_by": "popularity.desc",
            "release_date.lte": today,
            "watch_region": "IN",
            "page": page
        }
        try:
            response = requests.get(f"{TMDB_BASE_URL}/discover/movie", params=params)
            results = response.json().get("results", [])
            if not results:
                break
            for movie in results:
                if len(final_movies) >= 100:
                    break
                movie_id = movie.get("id")
                lang = movie.get("original_language")
                if not movie_id or lang not in INDIAN_LANGUAGES:
                    continue
                prov_response = requests.get(f"{TMDB_BASE_URL}/movie/{movie_id}/watch/providers", params={"api_key": TMDB_API_KEY})
                prov_data = prov_response.json()
                if "results" in prov_data and "IN" in prov_data["results"] and "flatrate" in prov_data["results"]["IN"]:
                    ext_response = requests.get(f"{TMDB_BASE_URL}/movie/{movie_id}/external_ids", params={"api_key": TMDB_API_KEY})
                    imdb_id = ext_response.json().get("imdb_id")
                    if imdb_id and imdb_id.startswith("tt") and imdb_id not in seen_ids:
                        seen_ids.add(imdb_id)
                        movie["imdb_id"] = imdb_id
                        final_movies.append(movie)
        except Exception as e:
            print("Error (trending)", e)
            break
        page += 1
    trending_movies_cache = final_movies
    print(f"[CACHE] Fetched {len(trending_movies_cache)} Trending movies ✅")

def to_stremio_meta(movie):
    try:
        imdb_id = movie.get("imdb_id")
        title = movie.get("title")
        if not imdb_id or not title:
            return None
        return {
            "id": imdb_id,
            "type": "movie",
            "name": title,
            "poster": f"https://image.tmdb.org/t/p/w500{movie['poster_path']}" if movie.get("poster_path") else None,
            "description": movie.get("overview", ""),
            "releaseInfo": movie.get("release_date", ""),
            "background": f"https://image.tmdb.org/t/p/w780{movie['backdrop_path']}" if movie.get("backdrop_path") else None
        }
    except Exception as e:
        print("to_stremio_meta error", e)
        return None

@app.route("/manifest.json")
def manifest():
    return jsonify({
        "id": "org.indian.catalog",
        "version": "1.0.0",
        "name": "Indian Catalog",
        "description": "Combined Malayalam, Hindi, and Trending Indian Movies on OTT",
        "resources": ["catalog"],
        "types": ["movie"],
        "catalogs": [
            {"type": "movie", "id": "malayalam", "name": "Malayalam"},
            {"type": "movie", "id": "hindi", "name": "Hindi"},
            {"type": "movie", "id": "trending-indian", "name": "Trending Indian"}
        ],
        "idPrefixes": ["tt"]
    })

@app.route("/catalog/movie/malayalam.json")
def mal_catalog():
    try:
        metas = [m for m in (to_stremio_meta(mm) for mm in malayalam_movies_cache) if m]
        return jsonify({"metas": metas})
    except Exception:
        return jsonify({"metas": []})

@app.route("/catalog/movie/hindi.json")
def hindi_catalog():
    try:
        metas = [m for m in (to_stremio_meta(mm) for mm in hindi_movies_cache) if m]
        return jsonify({"metas": metas})
    except Exception:
        return jsonify({"metas": []})

@app.route("/catalog/movie/trending-indian.json")
def trending_catalog():
    try:
        metas = [m for m in (to_stremio_meta(mm) for mm in trending_movies_cache) if m]
        return jsonify({"metas": metas})
    except Exception:
        return jsonify({"metas": []})

@app.route("/refresh")
def refresh():
    def do_refresh():
        try:
            fetch_malayalam_movies()
            fetch_hindi_movies()
            fetch_trending_movies()
        except Exception as e:
            print(f"REFRESH ERROR {e}")
    threading.Thread(target=do_refresh).start()
    return jsonify({"status": "refresh started in background"})

# Fetch on startup
fetch_malayalam_movies()
fetch_hindi_movies()
fetch_trending_movies()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
