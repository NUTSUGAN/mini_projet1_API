"""Q3 : cache asynchrone d'une heure et démonstration locale."""

import asyncio
import random
import time
from collections import OrderedDict
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import httpx


class ClientAvecCache:
    """Client GET avec cache limité et partage des requêtes en cours."""

    def __init__(self, client, duree=3600, limite=1000, horloge=time.monotonic):
        if duree <= 0 or limite <= 0:
            raise ValueError("La durée et la limite doivent être positives.")
        self.client = client
        self.duree = duree
        self.limite = limite
        self.horloge = horloge
        self.cache = OrderedDict()
        self.en_cours = {}

    async def get(self, url, params=None):
        # L'URL complète inclut les paramètres et sert de clé au cache.
        adresse = httpx.URL(url)
        cle = str(adresse.copy_merge_params(params)) if params is not None else str(adresse)
        entree = self.cache.get(cle)
        if entree is not None:
            expiration, response = entree
            if self.horloge() < expiration:
                self.cache.move_to_end(cle)
                return response
            del self.cache[cle]

        if cle not in self.en_cours:
            self.en_cours[cle] = asyncio.create_task(self._charger(cle))
        # Si un appelant est annulé, les autres peuvent toujours recevoir la réponse.
        return await asyncio.shield(self.en_cours[cle])

    async def _charger(self, cle):
        try:
            for tentative in range(1, 5):
                response = None
                try:
                    response = await self.client.get(cle, timeout=10.0)
                    if response.is_success:
                        self.cache[cle] = (self.horloge() + self.duree, response)
                        self.cache.move_to_end(cle)
                        if len(self.cache) > self.limite:
                            self.cache.popitem(last=False)
                        return response
                    if response.status_code not in (429, 500, 502, 503, 504):
                        response.raise_for_status()
                    if tentative == 4:
                        response.raise_for_status()
                except httpx.RequestError:
                    if tentative == 4:
                        raise
                delai = 2 ** (tentative - 1) + random.uniform(0, 1)
                valeur = response.headers.get("Retry-After") if response is not None else None
                if valeur:
                    try:
                        delai = max(0, float(valeur))
                    except ValueError:
                        try:
                            date = parsedate_to_datetime(valeur)
                            delai = max(0, (date - datetime.now(timezone.utc)).total_seconds())
                        except (ValueError, TypeError, OverflowError):
                            pass
                await asyncio.sleep(delai)
        finally:
            self.en_cours.pop(cle, None)


async def demonstration():
    """Une horloge contrôlée remplace l'attente réelle d'une heure."""
    maintenant = [0.0]
    appels = [0]

    async def serveur_fictif(request):
        appels[0] += 1
        return httpx.Response(200, json={"appel": appels[0]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(serveur_fictif)) as client:
        api = ClientAvecCache(client, horloge=lambda: maintenant[0])
        url = "https://api.example.com/data1"
        params = {"langue": "fr"}

        premiere = await api.get(url, params)
        print(f"Premier appel : réponse {premiere.json()}, appels simulés = {appels[0]}")
        seconde = await api.get(url, params)
        print(f"Depuis le cache : réponse {seconde.json()}, appels simulés = {appels[0]}")
        maintenant[0] += 3600
        troisieme = await api.get(url, params)
        print(f"Après une heure : réponse {troisieme.json()}, appels simulés = {appels[0]}")


if __name__ == "__main__":
    asyncio.run(demonstration())
