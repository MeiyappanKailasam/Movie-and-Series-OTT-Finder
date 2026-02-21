from flask import Flask, render_template, request,jsonify
from datetime import datetime
import requests
import time

app = Flask(__name__)

API_KEY = "ed8de1745c899cd4d45c6d275bfce10b"

def get_movie_data(movie_name):
    search_url = f"https://api.themoviedb.org/3/search/multi?api_key={API_KEY}&query={movie_name}"

    try:
        response = requests.get(search_url, timeout=5)
        data = response.json()

        if "results" not in data:
            return None

        movie = None
        for item in data["results"]:
            if item.get("media_type") in ["movie", "tv"]:
                movie = item
                break

        if not movie:
            return None

        movie_id = movie["id"]
        media_type = movie["media_type"]

        # Get release date
        release_date = movie.get("release_date") or movie.get("first_air_date")

        is_released = True

        if release_date:
            try:
                release_dt = datetime.strptime(release_date, "%Y-%m-%d")
                if release_dt > datetime.today():
                    is_released = False
            except:
                pass

        india_providers = []

        # Only fetch providers if released
        if is_released:
            provider_url = f"https://api.themoviedb.org/3/{media_type}/{movie_id}/watch/providers?api_key={API_KEY}"
            provider_response = requests.get(provider_url, timeout=5).json()
            india_providers = provider_response.get("results", {}).get("IN", {}).get("flatrate", [])

        return {
            "title": movie.get("title") or movie.get("name"),
            "rating": movie.get("vote_average"),
            "overview": movie.get("overview"),
            "poster": f"https://image.tmdb.org/t/p/w500{movie['poster_path']}"
                      if movie.get("poster_path") else None,
            "providers": india_providers,
            "release_date": release_date,
            "is_released": is_released
        }

    except Exception as e:
        print("Error:", e)
        return None

# 🔥 NEW AUTOCOMPLETE ROUTE
last_call_time = 0

@app.route("/autocomplete")
def autocomplete():
    global last_call_time

    query = request.args.get("q")

    if not query or len(query) < 2:
        return jsonify([])

    # Prevent rapid-fire calls (simple rate limit)
    current_time = time.time()
    if current_time - last_call_time < 0.5:
        return jsonify([])

    last_call_time = current_time

    search_url = f"https://api.themoviedb.org/3/search/multi?api_key={API_KEY}&query={query}"

    try:
        response = requests.get(search_url, timeout=5)

        if response.status_code != 200:
            return jsonify([])

        data = response.json()

        suggestions = []

        for result in data.get("results", [])[:5]:
            title = result.get("title") or result.get("name")
            if title:
                suggestions.append(title)

        return jsonify(suggestions)

    except requests.exceptions.RequestException as e:
        print("Autocomplete network error:", e)
        return jsonify([])
@app.route("/", methods=["GET", "POST"])
def home():
    movie_data = None
    if request.method == "POST":
        movie_name = request.form["movie"]
        movie_data = get_movie_data(movie_name)

    return render_template("index.html", movie=movie_data)


if __name__ == "__main__":
    app.run(debug=True)