"""Affiche les informations d'un film TMDB dans le navigateur."""
import httpx
import psycopg
import streamlit as st
from projet.base_films import enregistrer_film
from projet.movie_details import get_movie_details

st.title("Recherche de films TMDB")
st.write("Saisis l'identifiant TMDB d'un film pour afficher sa fiche.")
with st.form("recherche"):
    movie_id = st.number_input("Identifiant du film", min_value=1, value=550, step=1)
    rechercher = st.form_submit_button("Rechercher")

if rechercher:
    try:
        film = get_movie_details(int(movie_id))
        st.subheader(film["titre"] or "Titre indisponible")
        st.write("Date de sortie :", film["date_de_sortie"] or "Non renseignée")
        st.write("Genres :", ", ".join(film["genres"]) or "Non renseignés")
        st.write("Popularité :", film["popularite"])
        st.write("Note moyenne :", film["note_moyenne"], "/ 10")
        try:
            enregistrer_film(int(movie_id), film)
            st.success("Fiche enregistrée dans la base de données.")
        except (ValueError, psycopg.Error):
            st.warning("Fiche affichée, mais son enregistrement dans la base a échoué.")
    except (ValueError, RuntimeError, httpx.HTTPError) as erreur:
        st.error(f"Impossible de récupérer le film : {erreur}")

st.caption("Données fournies par TMDB.")
