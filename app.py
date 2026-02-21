from flask import Flask, render_template, request,jsonify
import requests
import time
import urllib.parse
import os
app = Flask(__name__)

API_KEY = os.environ.get("TMDB_API_KEY")

def get_movie_data(movie_name):
    from datetime import datetime

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

        # 🔥 GET VIDEOS (Trailer > Teaser > Promo)
        video_url = f"https://api.themoviedb.org/3/{media_type}/{movie_id}/videos?api_key={API_KEY}"
        video_response = requests.get(video_url, timeout=5).json()

        video_key = None
        preferred_order = ["Trailer", "Teaser", "Promo"]

        for video_type in preferred_order:
            for vid in video_response.get("results", []):
                if vid["type"] == video_type and vid["site"] == "YouTube":
                    video_key = vid["key"]
                    break
            if video_key:
                break

        # Release logic
        release_date = movie.get("release_date") or movie.get("first_air_date")
        is_released = True

        if release_date:
            try:
                release_dt = datetime.strptime(release_date, "%Y-%m-%d")
                if release_dt > datetime.today():
                    is_released = False
            except:
                pass
        detail_url = f"https://api.themoviedb.org/3/{media_type}/{movie_id}?api_key={API_KEY}"
        detail_response = requests.get(detail_url, timeout=5).json()

        genres = [g["name"] for g in detail_response.get("genres", [])]
        genre_text = ", ".join(genres)
        providers = []

        if is_released:
            provider_url = f"https://api.themoviedb.org/3/{media_type}/{movie_id}/watch/providers?api_key={API_KEY}"
            provider_response = requests.get(provider_url, timeout=5).json()

            country_data = provider_response.get("results", {}).get("IN", {})

            provider_link = country_data.get("link")

            movie_title = movie.get("title") or movie.get("name")
            encoded_title = urllib.parse.quote(movie_title)

            for provider in country_data.get("flatrate", []):
                provider_name = provider.get("provider_name")
                
                # Generate direct search link
                if provider_name.lower() == "jiohotstar":
                    direct_link = f"https://www.jiohotstar.com/search?q={encoded_title}"
                elif provider_name.lower() == "netflix":
                    direct_link = f"https://www.netflix.com/search?q={encoded_title}"
                elif provider_name.lower() == "amazon prime video":
                    direct_link = f"https://www.primevideo.com/search/ref=atv_nb_sr?phrase={encoded_title}"
                else:
                    direct_link = f"https://www.google.com/search?q=Watch+{encoded_title}+on+{provider_name}"

                providers.append({
                    "name": provider_name,
                    "logo": provider.get("logo_path"),
                    "link": direct_link
                })
        return {
            "title": movie.get("title") or movie.get("name"),
            "rating": movie.get("vote_average"),
            "overview": movie.get("overview"),
            "poster": f"https://image.tmdb.org/t/p/w500{movie['poster_path']}"
                      if movie.get("poster_path") else None,
            "providers": providers,
            "genres":genre_text,
            "release_date": release_date,
            "is_released": is_released,
            "video_key": video_key
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