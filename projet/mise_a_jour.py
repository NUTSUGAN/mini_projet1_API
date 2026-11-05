"""Mise à jour trimestrielle de l'export et des fiches enregistrées."""
import sys
import httpx
import psycopg
from projet.base_films import enregistrer_film, identifiants_enregistres
from projet.import_films import importer_export
from projet.movie_details import get_movie_details


def actualiser():
    importer_export()
    erreurs = 0
    for movie_id in identifiants_enregistres():
        try:
            enregistrer_film(movie_id, get_movie_details(movie_id))
            print(f"Film {movie_id} actualisé.")
        except (ValueError, RuntimeError, httpx.HTTPError, psycopg.Error):
            erreurs += 1
            print(f"Film {movie_id} : mise à jour impossible.")
    if erreurs:
        raise RuntimeError(f"{erreurs} fiche(s) non actualisée(s).")
    print("Mise à jour terminée.")


if __name__ == "__main__":
    try:
        actualiser()
    except (ValueError, RuntimeError, OSError, httpx.HTTPError, psycopg.Error) as erreur:
        print(f"Mise à jour impossible : {type(erreur).__name__}")
        sys.exit(1)
