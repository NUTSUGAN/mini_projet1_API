"""Télécharge l'export TMDB et le charge par lots dans PostgreSQL."""
import argparse
import gzip
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pandas as pd
import psycopg
from dotenv import load_dotenv
from psycopg.types.json import Jsonb

load_dotenv()


def importer_export(date_export=None, chemin=None, taille_lot=5000):
    """Importe un export complet. Une erreur annule toutes les modifications SQL."""
    if taille_lot <= 0:
        raise ValueError("La taille du lot doit être positive.")
    url_base = os.getenv("SUPABASE_DB_URL")
    if not url_base:
        raise ValueError("SUPABASE_DB_URL est absent du fichier .env.")
    date_export = date_export or datetime.now(timezone.utc).date()
    url = f"https://files.tmdb.org/p/exports/movie_ids_{date_export:%m_%d_%Y}.json.gz"

    with tempfile.TemporaryDirectory() as dossier:
        if chemin is None:
            chemin = Path(dossier) / "films.json.gz"
            print(f"Téléchargement de l'export du {date_export}...")
            with httpx.stream("GET", url, timeout=60.0, follow_redirects=True) as response:
                response.raise_for_status()
                with open(chemin, "wb") as fichier:
                    for bloc in response.iter_bytes():
                        fichier.write(bloc)
        total = 0
        with psycopg.connect(url_base, connect_timeout=15) as connexion:
            with connexion.cursor() as curseur:
                curseur.execute("""
                    CREATE TABLE IF NOT EXISTS movie_exports (
                        id BIGINT PRIMARY KEY,
                        original_title TEXT,
                        popularity DOUBLE PRECISION,
                        adult BOOLEAN,
                        video BOOLEAN,
                        data JSONB NOT NULL,
                        date_export DATE NOT NULL
                    )
                """)
                curseur.execute("CREATE TEMP TABLE export_temp (LIKE movie_exports INCLUDING DEFAULTS) ON COMMIT DROP")
                with gzip.open(chemin, "rt", encoding="utf-8") as fichier:
                    lot = []
                    for ligne in fichier:
                        if not ligne.strip():
                            continue
                        lot.append(json.loads(ligne))
                        if total == 0 and len(lot) <= 5:
                            print("Exemple :", lot[-1])
                        if len(lot) >= taille_lot:
                            total += inserer_lot(curseur, lot, date_export)
                            lot.clear()
                    if lot:
                        total += inserer_lot(curseur, lot, date_export)
                if total == 0:
                    raise ValueError("L'export est vide : aucune modification enregistrée.")
                curseur.execute("""
                    INSERT INTO movie_exports (id, original_title, popularity, adult, video, data, date_export)
                    SELECT id, original_title, popularity, adult, video, data, date_export FROM export_temp
                    ON CONFLICT (id) DO UPDATE SET
                        original_title = EXCLUDED.original_title, popularity = EXCLUDED.popularity,
                        adult = EXCLUDED.adult, video = EXCLUDED.video,
                        data = EXCLUDED.data, date_export = EXCLUDED.date_export
                """)
        print(f"Import terminé : {total} films traités.")
        return total


def inserer_lot(curseur, films, date_export):
    """Transforme une liste JSON en DataFrame, puis insère ses lignes."""
    dataframe = pd.DataFrame(films)
    print(f"Traitement d'un lot de {len(dataframe)} films...")
    lignes = []
    for film in dataframe.to_dict(orient="records"):
        # Remplacer les valeurs manquantes de pandas par None pour PostgreSQL/JSON.
        film = {cle: (None if pd.isna(valeur) else valeur) for cle, valeur in film.items()}
        lignes.append((film["id"], film.get("original_title"), film.get("popularity"),
                       film.get("adult"), film.get("video"), Jsonb(film), date_export))
    curseur.executemany(
        "INSERT INTO export_temp (id, original_title, popularity, adult, video, data, date_export) VALUES (%s, %s, %s, %s, %s, %s, %s)",
        lignes,
    )
    return len(lignes)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Importer l'export des films TMDB")
    parser.add_argument("--date", type=lambda valeur: datetime.strptime(valeur, "%Y-%m-%d").date(), help="Date UTC YYYY-MM-DD")
    parser.add_argument("--fichier", help="Fichier .gz local, pour essais")
    args = parser.parse_args()
    try:
        importer_export(args.date, args.fichier)
    except (ValueError, OSError, httpx.HTTPError, psycopg.Error) as erreur:
        print(f"Import impossible : {type(erreur).__name__}")
        raise SystemExit(1) from erreur
