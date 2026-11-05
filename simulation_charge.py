"""Q2 : simuler de nombreuses requêtes sans contacter un vrai serveur."""

import argparse
import asyncio
import time

import httpx

ROUTES = [
    "https://api.example.com/data1",
    "https://api.example.com/data2",
    "https://api.example.com/data3",
]
MAX_TENTATIVES = 4


async def serveur_fictif(request):
    """Simule une API : certaines requêtes échouent à leur première tentative."""
    numero = int(request.headers["X-Request-Number"])
    tentative = int(request.headers["X-Attempt"])
    await asyncio.sleep(0)  # Laisse les autres tâches avancer.
    # Une requête sur 100 échoue une fois pour démontrer le mécanisme de retry.
    if numero % 100 == 0 and tentative == 1:
        return httpx.Response(503, json={"erreur": "serveur temporairement indisponible"})
    return httpx.Response(200, json={"route": request.url.path, "numero": numero})


async def appeler_api(client, url, numero, stats):
    """Réessaie les erreurs temporaires, sans bloquer les autres workers."""
    for tentative in range(1, MAX_TENTATIVES + 1):
        try:
            response = await client.get(
                url,
                headers={"X-Request-Number": str(numero), "X-Attempt": str(tentative)},
                timeout=10.0,
            )
            if response.is_success:
                stats["reussites"] += 1
                return
            temporaire = response.status_code in (429, 500, 502, 503, 504)
            if not temporaire:
                stats["echecs"] += 1
                return
        except httpx.RequestError:
            pass  # Une erreur de connexion peut être temporaire.

        if tentative < MAX_TENTATIVES:
            stats["nouvelles_tentatives"] += 1
            # await laisse les autres tâches avancer pendant cette pause.
            await asyncio.sleep(0.01 * 2 ** (tentative - 1))
    stats["echecs"] += 1


async def worker(file, client, stats):
    """Traite les requêtes de la file jusqu'au signal d'arrêt (None)."""
    while True:
        travail = await file.get()
        try:
            if travail is None:
                return
            numero, url = travail
            await appeler_api(client, url, numero, stats)
        finally:
            file.task_done()


async def simuler(nombre, nombre_workers):
    stats = {"reussites": 0, "echecs": 0, "nouvelles_tentatives": 0}
    # La file limite la mémoire même si le nombre de requêtes est très grand.
    file = asyncio.Queue(maxsize=nombre_workers * 2)
    # MockTransport intercepte les appels : aucune requête réseau réelle n'est envoyée.
    transport = httpx.MockTransport(serveur_fictif)
    debut = time.perf_counter()

    async with httpx.AsyncClient(transport=transport) as client:
        # On crée seulement le nombre de tâches demandé, pas une tâche par requête.
        workers = [asyncio.create_task(worker(file, client, stats)) for _ in range(nombre_workers)]
        for numero in range(1, nombre + 1):
            await file.put((numero, ROUTES[(numero - 1) % len(ROUTES)]))
        for _ in workers:
            # Un signal None indique à chaque worker qu'il peut s'arrêter.
            await file.put(None)
        await file.join()
        await asyncio.gather(*workers)

    duree = time.perf_counter() - debut
    print(f"Requêtes demandées : {nombre:,}".replace(",", " "))
    print(f"Workers : {nombre_workers}")
    print(f"Durée : {duree:.2f} secondes")
    print(f"Débit : {nombre / duree:.0f} requêtes par seconde")
    print(f"Réussites : {stats['reussites']}")
    print(f"Échecs : {stats['echecs']}")
    print(f"Nouvelles tentatives : {stats['nouvelles_tentatives']}")


def entier_positif(valeur):
    nombre = int(valeur)
    if nombre <= 0:
        raise argparse.ArgumentTypeError("La valeur doit être un entier positif.")
    return nombre


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulation locale de requêtes concurrentes")
    parser.add_argument("--nombre", type=entier_positif, default=1000, help="Nombre de requêtes (défaut : 1000)")
    parser.add_argument("--workers", type=entier_positif, default=50, help="Nombre de workers (défaut : 50)")
    args = parser.parse_args()
    asyncio.run(simuler(args.nombre, args.workers))
