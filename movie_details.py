"""Récupérer les informations principales d'un film avec l'API TMDB."""

import os

import httpx
from dotenv import load_dotenv

# Charge les variables définies dans le fichier .env.
load_dotenv()


def get_movie_details(movie_id):
    """Retourne les principales informations du film identifié par movie_id."""
    if not isinstance(movie_id, int) or isinstance(movie_id, bool) or movie_id <= 0:
        raise ValueError("L'identifiant du film doit être un entier positif.")

    token = os.getenv("TMDB_READ_ACCESS_TOKEN")
    if not token:
        raise ValueError("Le jeton TMDB_READ_ACCESS_TOKEN est absent du fichier .env.")

    url = f"https://api.themoviedb.org/3/movie/{movie_id}"
    headers = {"Authorization": f"Bearer {token}"}
    response = httpx.get(url, headers=headers, params={"language": "fr-FR"}, timeout=10.0)
    response.raise_for_status()
    data = response.json()

    return {
        "titre": data.get("title"),
        "date_de_sortie": data.get("release_date"),
        "genres": [genre["name"] for genre in data.get("genres", [])],
        "popularite": data.get("popularity"),
        "note_moyenne": data.get("vote_average"),
    }


if __name__ == "__main__":
    try:
        film = get_movie_details(550)
        print(f"Titre : {film['titre']}")
        print(f"Date de sortie : {film['date_de_sortie']}")
        print(f"Genres : {', '.join(film['genres'])}")
        print(f"Popularité : {film['popularite']}")
        print(f"Note moyenne : {film['note_moyenne']} / 10")
    except (ValueError, httpx.HTTPError) as erreur:
        print(f"Impossible de récupérer le film : {erreur}")
