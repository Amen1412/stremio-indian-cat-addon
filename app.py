from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from datetime import datetime
import time  # For introducing delays
import threading

app = Flask(__name__)
CORS(app)

TMDB_API_KEY = "29dfffa9ae088178fa088680b67ce583"
TMDB_BASE_URL = "https://api.themoviedb.org/3"

# Global movie caches
malayalam_movies_cache = []
hindi_movies_cache = []
trending_movies_cache = []

# Fetch Malayalam movies
def fetch_malayalam_movies():
    global malayalam_movies_cache
    print("[CACHE] Fetching Malayalam movies...")
    
    today = datetime.now().strftime("%Y-%m-%d")
    final_movies = []

    for page in range(1, 1000):
        time.sleep(1)  # Respecting API rate limits
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

                # OTT availability check
                providers_url = f"{TMDB_BASE_URL}/movie/{movie_id}/watch/providers"
                prov_response = requests.get(providers_url, params={"api_key": TMDB_API_KEY})
                prov_data = prov_response.json()

                if "results" in prov_data and "IN" in prov_data["results"]:
                    if "flatrate" in prov_data["results"]["IN"]:
                        # Get IMDb ID
                        ext_url = f"{TMDB_BASE_URL}/movie/{movie_id}/external_ids"
                        ext_response = requests.get(ext_url, params={"api_key": TMDB_API_KEY})
                        ext_data = ext_response.json()
                        imdb_id = ext_data.get("imdb_id")

                        if imdb_id and imdb_id.startswith("tt"):
                            movie["imdb_id"] = imdb_id
                            final_movies.append(movie)

        except Exception as e:
            print(f"[ERROR] Fetch failed: {e}")
            break

    # Deduplicate movies
    seen_ids = set()
    malayalam_movies_cache = [movie for movie in final_movies if movie["imdb_id"] not in seen_ids and not seen_ids.add(movie["imdb_id"])]
    print(f"[CACHE] Fetched {len(malayalam_movies_cache)} Malayalam movies ✅")

# Fetch Hindi movies
def fetch_hindi_movies():
    global hindi_movies_cache
    print("[CACHE] Fetching Hindi movies...")
    
    today = datetime.now().strftime("%Y-%m-%d")
    final_movies = []

    for page in range(1, 1000):
        time.sleep(1)  # Respecting API rate limits
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

                # OTT availability check
                providers_url = f"{TMDB_BASE_URL}/movie/{movie_id}/watch/providers"
                prov_response = requests.get(providers_url, params={"api_key": TMDB_API_KEY})
                prov_data = prov_response.json()

                if "results" in prov_data and "IN" in prov_data["results"]:
                    if "flatrate" in prov_data["results"]["IN"]:
                        # Get IMDb ID
                        ext_url = f"{TMDB_BASE_URL}/movie/{movie_id}/external_ids"
                        ext_response = requests.get(ext_url, params={"api_key": TMDB_API_KEY})
                        ext_data = ext_response.json()
                        imdb_id = ext_data.get("imdb_id")

                        if imdb_id and imdb_id.startswith("tt"):
                            movie["imdb_id"] = imdb_id
                            final_movies.append(movie)

        except Exception as e:
            print(f"[ERROR] Fetch failed: {e}")
            break

    # Deduplicate movies
    seen_ids = set()
    hindi_movies_cache = [movie for movie in final_movies if movie["imdb_id"] not in seen_ids and not seen_ids.add(movie["imdb_id"])]
    print(f"[CACHE] Fetched {len(hindi_movies_cache)} Hindi movies ✅")

# Fetch trending Indian movies (till max 100)
def fetch_trending_movies():
    global trending_movies_cache
    print("[CACHE] Fetching trending Indian movies...")
    
    today = datetime.now().strftime("%Y-%m-%d")
    final_movies = []
    seen_ids = set()

    page = 1
    while len(final_movies) < 100:
        time.sleep(1)  # Respecting API rate limits
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
                if not movie_id or lang not in {"hi", "ml", "ta", "te", "kn"}:
                    continue

                # OTT availability check
                providers_url = f"{TMDB_BASE_URL}/movie/{movie_id}/watch/providers"
                prov_response = requests.get(providers_url, params={"api_key": TMDB_API_KEY})
                prov_data = prov_response.json()

                if "results" in prov_data and "IN" in prov_data["results"]:
                    if "flatrate" in prov_data["results"]["IN"]:
                        # Get IMDb ID
                        ext_url = f"{TMDB_BASE_URL}/movie/{movie_id}/external_ids"
                        ext_response = requests.get(ext_url, params={"api_key": TMDB_API_KEY})
                        ext_data = ext_response.json()
                        imdb_id = ext_data.get("imdb_id")

                        if imdb_id and imdb_id not in seen_ids:
                            movie["imdb_id"] = imdb_id
                            seen_ids.add(imdb_id)
                            final_movies.append(movie)

        except Exception as e:
            print(f"[ERROR] Fetch failed: {e}")
            break

        page += 1

    trending_movies_cache = final_movies
    print(f"[CACHE] Fetched {len(trending_movies_cache)} Trending Movies ✅")

# Stremio catalog function
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
        print(f"[ERROR] Metadata conversion failed: {e}")
        return None

# Manifest and catalog routes
@app.route("/manifest.json")
def manifest():
    return jsonify({
        "id": "org.indian.catalog",
        "version": "1.0.0",
        "name": "Indian Catalog",
        "description": "A catalog combining Malayalam, Hindi, and Trending Indian movies.",
        "resources": ["catalog"],
        "types": ["movie"],
        "catalogs": [
            {"type": "movie", "id": "indian", "name": "Indian"}
        ],
        "idPrefixes": ["tt"]
    })

@app.route("/catalog/movie/indian.json")
def catalog():
    try:
        metas = [meta for meta in (to_stremio_meta(m) for m in malayalam_movies_cache + hindi_movies_cache + trending_movies_cache) if meta]
        print(f"[INFO] Returning {len(metas)} movies ✅")
        return jsonify({"metas": metas})
    except Exception as e:
        print(f"[ERROR] Catalog error: {e}")
        return jsonify({"metas": []})

@app.route("/refresh")
def refresh():
    def do_refresh():
        try:
            fetch_malayalam_movies()
            fetch_hindi_movies()
            fetch_trending_movies()
            print("[REFRESH] Data refreshed ✅")
        except Exception as e:
            print(f"[REFRESH ERROR] {e}")

    threading.Thread(target=do_refresh).start()
    return jsonify({"status": "Refreshing in background..."})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7000)
