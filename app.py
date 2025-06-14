from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from datetime import datetime
import threading
import os

app = Flask(__name__)
CORS(app)

TMDB_API_KEY = "29dfffa9ae088178fa088680b67ce583"
TMDB_BASE_URL = "https://api.themoviedb.org/3"

catalog_configs = {
    "malayalam": {
        "lang": "ml",
        "name": "Malayalam",
        "description": "Latest Malayalam Movies on OTT",
        "cache": []
    },
    "hindi": {
        "lang": "hi",
        "name": "Hindi",
        "description": "Latest Hindi Movies on OTT",
        "cache": []
    },
    "trending-indian": {
        "lang": None,  # uses multiple languages
        "name": "Trending Indian",
        "description": "Trending Indian Movies on OTT (Hindi, Malayalam, Tamil, Telugu, Kannada)",
        "cache": []
    }
}

INDIAN_LANGUAGES = {"hi", "ml", "ta", "te", "kn"}

def fetch_and_cache_movies(catalog_id):
    config = catalog_configs[catalog_id]
    print(f"[CACHE] Fetching {config['name']} OTT movies...")
    today = datetime.now().strftime("%Y-%m-%d")
    final_movies = []
    seen_ids = set()

    page = 1
    while len(final_movies) < 1000 and page < 1000:
        params = {
            "api_key": TMDB_API_KEY,
            "sort_by": "release_date.desc" if catalog_id != "trending-indian" else "popularity.desc",
            "release_date.lte": today,
            "region": "IN",
            "page": page
        }

        if config['lang']:
            params["with_original_language"] = config['lang']

        try:
            response = requests.get(f"{TMDB_BASE_URL}/discover/movie", params=params)
            results = response.json().get("results", [])
            if not results:
                break

            for movie in results:
                movie_id = movie.get("id")
                title = movie.get("title")
                lang = movie.get("original_language")

                if not movie_id or not title:
                    continue

                if catalog_id == "trending-indian" and lang not in INDIAN_LANGUAGES:
                    continue

                # Check OTT availability
                providers_url = f"{TMDB_BASE_URL}/movie/{movie_id}/watch/providers"
                prov_response = requests.get(providers_url, params={"api_key": TMDB_API_KEY})
                prov_data = prov_response.json()

                if "results" in prov_data and "IN" in prov_data["results"]:
                    if "flatrate" in prov_data["results"]["IN"]:
                        # IMDb ID
                        ext_url = f"{TMDB_BASE_URL}/movie/{movie_id}/external_ids"
                        ext_response = requests.get(ext_url, params={"api_key": TMDB_API_KEY})
                        ext_data = ext_response.json()
                        imdb_id = ext_data.get("imdb_id")

                        if imdb_id and imdb_id.startswith("tt") and imdb_id not in seen_ids:
                            seen_ids.add(imdb_id)
                            movie["imdb_id"] = imdb_id
                            final_movies.append(movie)
        except Exception as e:
            print(f"[ERROR] Page {page} failed: {e}")
            break

        page += 1

    catalog_configs[catalog_id]['cache'] = final_movies
    print(f"[CACHE] Fetched {len(final_movies)} {config['name']} movies ✅")

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
        print(f"[ERROR] to_stremio_meta failed: {e}")
        return None

@app.route("/manifest.json")
def manifest():
    return jsonify({
        "id": "org.amen.catalog",
        "version": "1.0.0",
        "name": "Amen's Indian Catalogs",
        "description": "Combined Malayalam, Hindi & Trending Indian movie catalogs",
        "resources": ["catalog"],
        "types": ["movie"],
        "catalogs": [
            {"type": "movie", "id": k, "name": v["name"]}
            for k, v in catalog_configs.items()
        ],
        "idPrefixes": ["tt"]
    })

@app.route("/catalog/movie/<catalog_id>.json")
def catalog(catalog_id):
    if catalog_id not in catalog_configs:
        return jsonify({"metas": []})

    print(f"[INFO] Catalog requested: {catalog_id}")
    try:
        metas = [meta for meta in (to_stremio_meta(m) for m in catalog_configs[catalog_id]['cache']) if meta]
        return jsonify({"metas": metas})
    except Exception as e:
        print(f"[ERROR] Catalog error: {e}")
        return jsonify({"metas": []})

@app.route("/refresh/<catalog_id>")
def refresh_single(catalog_id):
    if catalog_id not in catalog_configs:
        return jsonify({"error": "Invalid catalog ID"})

    def do_refresh():
        fetch_and_cache_movies(catalog_id)

    threading.Thread(target=do_refresh).start()
    return jsonify({"status": f"Refresh started for {catalog_id}"})

@app.route("/refresh/all")
def refresh_all():
    def do_all():
        for key in catalog_configs:
            fetch_and_cache_movies(key)
    threading.Thread(target=do_all).start()
    return jsonify({"status": "All catalogs refreshing"})

# Fetch on startup
for key in catalog_configs:
    fetch_and_cache_movies(key)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7000))
    app.run(host="0.0.0.0", port=port)
