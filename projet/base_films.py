"""Conservation des fiches de films dans Supabase PostgreSQL."""
import os
import psycopg
from dotenv import load_dotenv
from psycopg.types.json import Jsonb

load_dotenv()


def connexion_base():
    url = os.getenv("SUPABASE_DB_URL")
    if not url:
        raise ValueError("SUPABASE_DB_URL est absent du fichier .env.")
    return psycopg.connect(url, connect_timeout=15)


def preparer_table(connexion):
    with connexion.cursor() as curseur:
        curseur.execute("""CREATE TABLE IF NOT EXISTS movie_details (
            id BIGINT PRIMARY KEY,
            details JSONB NOT NULL,
            mis_a_jour TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )""")


def enregistrer_film(movie_id, film):
    with connexion_base() as connexion:
        preparer_table(connexion)
        with connexion.cursor() as curseur:
            curseur.execute("""INSERT INTO movie_details (id, details, mis_a_jour)
                VALUES (%s, %s, NOW())
                ON CONFLICT (id) DO UPDATE SET details = EXCLUDED.details, mis_a_jour = NOW()
            """, (movie_id, Jsonb(film)))


def identifiants_enregistres():
    with connexion_base() as connexion:
        preparer_table(connexion)
        with connexion.cursor() as curseur:
            curseur.execute("SELECT id FROM movie_details ORDER BY id")
            return [ligne[0] for ligne in curseur.fetchall()]
