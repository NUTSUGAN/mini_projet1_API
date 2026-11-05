"""Récupérer les informations principales d'un film avec l'API TMDB."""

import os
import random
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import httpx
from dotenv import load_dotenv

# Charge les variables définies dans le fichier .env.
load_dotenv()


def attendre_avant_retry(response, tentative):
    """Attend selon Retry-After, ou applique un délai exponentiel."""
    valeur = response.headers.get("Retry-After") if response is not None else None
    if valeur:
        try:
            delai = max(0, float(valeur))
        except ValueError:
            try:
                date = parsedate_to_datetime(valeur)
                delai = max(0, (date - datetime.now(timezone.utc)).total_seconds())
            except (ValueError, TypeError, OverflowError):
                delai = 2 ** (tentative - 1) + random.uniform(0, 1)
    else:
        # Les délais augmentent : environ 1, puis 2, puis 4 secondes.
        delai = 2 ** (tentative - 1) + random.uniform(0, 1)
    print(f"Nouvelle tentative dans {delai:.1f} seconde(s)...")
    time.sleep(delai)


def requete_avec_retry(url, headers, params):
    """Effectue au maximum quatre tentatives pour les erreurs temporaires."""
    for tentative in range(1, 5):
        response = None
        try:
            response = httpx.get(url, headers=headers, params=params, timeout=10.0)
        except httpx.RequestError as erreur:
            if tentative == 4:
                raise RuntimeError("Connexion impossible après 4 tentatives.") from erreur
        else:
            if response.is_success:
                return response

            messages = {
                400: "Requête invalide.",
                401: "Jeton TMDB absent ou invalide.",
                403: "Accès refusé par TMDB.",
                404: "Film introuvable : vérifie son identifiant.",
            }
            if response.status_code in messages:
                # Ces erreurs demandent une correction, donc on ne réessaie pas.
                raise RuntimeError(messages[response.status_code])
            if response.status_code not in (429, 500, 502, 503, 504):
                raise RuntimeError(f"Erreur HTTP inattendue : {response.status_code}.")
            if tentative == 4:
                raise RuntimeError(f"TMDB renvoie HTTP {response.status_code} après 4 tentatives.")

        attendre_avant_retry(response, tentative)


def get_movie_details(movie_id):
    """Retourne les principales informations du film identifié par movie_id."""
    # Un booléen est aussi un entier en Python : on le refuse explicitement.
    if not isinstance(movie_id, int) or isinstance(movie_id, bool) or movie_id <= 0:
        raise ValueError("L'identifiant du film doit être un entier positif.")

    # Le jeton reste dans .env et n'est pas écrit dans le code source.
    token = os.getenv("TMDB_READ_ACCESS_TOKEN")
    if not token:
        raise ValueError("Le jeton TMDB_READ_ACCESS_TOKEN est absent du fichier .env.")

    url = f"https://api.themoviedb.org/3/movie/{movie_id}"
    headers = {"Authorization": f"Bearer {token}"}
    response = requete_avec_retry(url, headers, {"language": "fr-FR"})
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
    except (ValueError, RuntimeError, httpx.HTTPError) as erreur:
        print(f"Impossible de récupérer le film : {erreur}")
