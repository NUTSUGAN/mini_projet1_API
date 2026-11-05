# Mini-projet TMDB

Ce projet utilise l'API The Movie Database pour consulter des films, simuler des requêtes et enregistrer des données dans PostgreSQL sur Supabase.

## Organisation

- `app.py` : interface Streamlit.
- `projet/` : récupération des films, accès à la base, import et mise à jour.
- `demonstrations/` : simulations de la charge et du cache.
- `.env.example` : modèle des variables à renseigner dans `.env`.
- `requirements.txt` : bibliothèques Python nécessaires.

Les commandes suivantes se lancent depuis le dossier racine du projet.

## Préparation

Créer `.env` à partir de `.env.example`, puis renseigner localement le jeton TMDB et l'URI PostgreSQL Supabase (session pooler). Ne pas partager ces secrets.

```powershell
Copy-Item .env.example .env
notepad .env
```

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Interface

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Saisir un identifiant (550 pour Fight Club), puis cliquer sur Rechercher. La fiche est affichée et enregistrée dans `movie_details` si la base est disponible.

## Questions communes : erreurs, concurrence et cache

- **Q1 — erreurs et nouvelles tentatives :** `movie_details.py` récupère le film 550. Il réessaie jusqu'à quatre fois en cas d'erreur temporaire et utilise `Retry-After` quand il est fourni.
- **Q2 — concurrence :** `simulation_charge.py` utilise une file bornée et des workers asyncio. Le serveur est fictif : aucun appel n'est envoyé aux routes example.com.
- **Q3 — cache :** `cache_api.py` présente un client asynchrone avec cache en mémoire d'une heure et regroupement des appels simultanés identiques. La démonstration utilise une horloge simulée. Ce client est indépendant de la recherche Streamlit, qui utilise actuellement la fonction synchrone de Q1.

```powershell
.\.venv\Scripts\python.exe -m projet.movie_details
.\.venv\Scripts\python.exe -m demonstrations.simulation_charge --nombre 1000 --workers 50
.\.venv\Scripts\python.exe -m demonstrations.simulation_charge --nombre 1000000 --workers 50
.\.venv\Scripts\python.exe -m demonstrations.cache_api
```

Le débit de Q2 correspond à une simulation locale : il ne représente pas les performances réelles de TMDB.

## Export des films

```powershell
.\.venv\Scripts\python.exe -m projet.import_films
```

Le script télécharge l'export du jour en UTC, affiche cinq exemples, lit le fichier JSON ligne par ligne et le transforme en listes JSON puis en DataFrames par lots. Il insère les films dans `movie_exports` : un même identifiant est mis à jour sans créer de doublon. L'import complet est validé en une transaction ; en cas d'erreur il est annulé. Il n'efface pas les films absents des exports suivants.

L'export du jour peut être indisponible avant 8 h UTC. Pour choisir une date ou tester un petit fichier :

```powershell
.\.venv\Scripts\python.exe -m projet.import_films --date 2026-11-04
.\.venv\Scripts\python.exe -m projet.import_films --fichier chemin\export.json.gz
```

L'export complet peut être volumineux : vérifier l'espace disponible et les limites du projet Supabase avant de le lancer. Les fichiers d'export contiennent des identifiants et quelques attributs, pas les fiches complètes.

## Mise à jour tous les trois mois

```powershell
.\.venv\Scripts\python.exe -m projet.mise_a_jour
```

Le script importe l'export du jour, puis actualise les fiches déjà enregistrées. Si l'import échoue, les fiches ne sont pas actualisées. Si une fiche échoue, les autres sont traitées et le script se termine avec un code d'erreur ; l'import déjà réussi reste enregistré.

Dans le Planificateur de tâches Windows : créer une tâche, définir un déclencheur mensuel les 1er janvier, avril, juillet et octobre à 12 h (heure locale), puis cocher « Exécuter la tâche dès que possible après un démarrage planifié manqué ». Dans Actions, choisir « Démarrer un programme » :

- Programme : chemin absolu vers `.venv\Scripts\python.exe` dans ce projet.
- Arguments : `-m projet.mise_a_jour`.
- Démarrer dans : chemin absolu du dossier du projet, sans guillemets.

Tester d'abord la commande manuellement. L'ordinateur, la connexion Internet et les services doivent être disponibles. L'exécution automatique n'est pas créée par le script.
