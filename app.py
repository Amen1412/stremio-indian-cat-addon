from flask import Flask, jsonify
from flask_cors import CORS
import requests
import asyncio

app = Flask(__name__)
CORS(app)

TMDB_API_KEY = 'f55ae99b4c3e8cb87a9bcd6b73b7c121'  # Your API key already included

# Delay helper to avoid rate limit (300ms between calls)
async def delay():
    await asyncio.sleep(0.3)

def fetch_until_limit(url, limit=100):
    movies = []
    page = 1
    while len(movies) < limit:
        response = requests.get(url + f"&page={page}")
        data = response.json()
        if "results" not in data or not data["results"]:
            break
        for movie in data["results"]:
            if movie.get("poster_path") and movie.get("release_date"):
                movies.append({
                    "id": movie["id"],
                    "name": movie["title"],
                    "poster": f"https://image.tmdb.org/t/p/w500{movie['poster_path']}",
                    "releaseInfo": movie["release_date"]
                })
                if len(movies) == limit:
                    break
        page += 1
        asyncio.run(delay())
    return movies

def fetch_all_available(url):
    movies = []
    page = 1
    while True:
        response = requests.get(url + f"&page={page}")
        data = response.json()
        if "results" not in data or not data["results"]:
            break
        for movie in data["results"]:
            if movie.get("poster_path") and movie.get("release_date"):
                movies.append({
                    "id": movie["id"],
                    "name": movie["title"],
                    "poster": f"https://image.tmdb.org/t/p/w500{movie['poster_path']}",
                    "releaseInfo": movie["release_date"]
                })
        page += 1
        if page > 100:  # safety stop
            break
        asyncio.run(delay())
    return movies

@app.route("/catalog/<type>/<id>.json")
def catalog(type, id):
    metas = []

    if id == "trending_indian":
        url = f"https://api.themoviedb.org/3/trending/movie/week?api_key={TMDB_API_KEY}&language=hi-IN&region=IN"
        metas = fetch_until_limit(url, limit=100)

    elif id in ["hindi", "malayalam"]:
        lang_code = "hi" if id == "hindi" else "ml"
        url = f"https://api.themoviedb.org/3/discover/movie?api_key={TMDB_API_KEY}&with_original_language={lang_code}&sort_by=release_date.desc&region=IN&with_watch_monetization_types=flatrate"
        metas = fetch_all_available(url)

    return jsonify({"metas": metas})

@app.route("/manifest.json")
def manifest():
    return jsonify({
        "id": "org.indian.catalog",
        "version": "1.0.0",
        "name": "Indian Catalog",
        "description": "Includes trending Indian movies and all available Hindi & Malayalam movies released on OTT platforms.",
        "resources": ["catalog"],
        "types": ["movie"],
        "catalogs": [
            {
                "type": "movie",
                "id": "trending_indian",
                "name": "Trending Indian Movies"
            },
            {
                "type": "movie",
                "id": "hindi",
                "name": "All Hindi Movies"
            },
            {
                "type": "movie",
                "id": "malayalam",
                "name": "All Malayalam Movies"
            }
        ]
    })

if __name__ == "__main__":
    app.run()
