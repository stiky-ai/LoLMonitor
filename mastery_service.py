import base64
import os

import requests


LCU_LOCKFILE_CANDIDATES = [
    r"C:\Riot Games\League of Legends\lockfile",
    os.path.expanduser(r"~\AppData\Local\Riot Games\League of Legends\lockfile"),
]


def load_champion_catalog():
    try:
        versions_response = requests.get(
            "https://ddragon.leagueoflegends.com/api/versions.json",
            timeout=10,
        )
        versions_response.raise_for_status()
        versions = versions_response.json()
        version = versions[0]
        champion_response = requests.get(
            f"https://ddragon.leagueoflegends.com/cdn/{version}/data/fr_FR/champion.json",
            timeout=10,
        )
        champion_response.raise_for_status()
        champions = champion_response.json()["data"].values()
        names = {int(champion["key"]): champion["name"] for champion in champions}
        images = {
            int(champion["key"]): champion["image"]["full"]
            for champion in champions
            if champion.get("image", {}).get("full")
        }
        return names, images, version
    except (requests.RequestException, ValueError, KeyError, IndexError, TypeError) as error:
        print(f"Erreur Data Dragon maîtrises : {error}")
        return {}, {}, "latest"


def _get_lcu_response(endpoint):
    lock_path = next((path for path in LCU_LOCKFILE_CANDIDATES if os.path.isfile(path)), None)
    if not lock_path:
        error = {"error": "Client LoL introuvable. Ouvre le client et connecte-toi pour charger les maîtrises."}
        return None, (error, 503)

    try:
        with open(lock_path, "r", encoding="utf-8") as lockfile:
            parts = lockfile.read().strip().split(":")
    except OSError:
        error = {"error": "Impossible de lire le fichier lockfile du client LoL."}
        return None, (error, 503)

    if len(parts) < 5 or parts[4] not in ("http", "https"):
        error = {"error": "Le fichier lockfile du client LoL est invalide."}
        return None, (error, 503)

    try:
        port = int(parts[2])
    except ValueError:
        error = {"error": "Le port du client LoL dans le lockfile est invalide."}
        return None, (error, 503)
    if not 1 <= port <= 65535:
        error = {"error": "Le port du client LoL dans le lockfile est invalide."}
        return None, (error, 503)

    auth_raw = f"riot:{parts[3]}"
    auth_encoded = base64.b64encode(auth_raw.encode("utf-8")).decode("ascii")
    headers = {
        "Authorization": f"Basic {auth_encoded}",
        "User-Agent": "LeagueOfLegendsClient",
        "Accept": "application/json",
    }

    try:
        response = requests.get(
            f"{parts[4]}://127.0.0.1:{port}{endpoint}",
            headers=headers,
            verify=False,
            timeout=5,
        )
    except requests.RequestException:
        error = {"error": "Impossible de joindre le client LoL. Vérifie qu'il est ouvert et connecté."}
        return None, (error, 503)

    return response, None


def get_gameflow_phase():
    response, error = _get_lcu_response("/lol-gameflow/v1/gameflow-phase")
    if error:
        return error

    if response.status_code != 200:
        return {"error": f"Le client LoL a refusé la lecture de l’état de partie (HTTP {response.status_code})."}, 502

    try:
        phase = response.json()
    except ValueError:
        return {"error": "Le client LoL a renvoyé un état de partie invalide."}, 502

    if not isinstance(phase, str):
        return {"error": "Le format de l’état de partie renvoyé par le client est invalide."}, 502

    return {"phase": phase}, 200


def get_mastery_data(champ_names, champ_images, version):
    response, error = _get_lcu_response(
        "/lol-champion-mastery/v1/local-player/champion-mastery"
    )
    if error:
        return error

    if response.status_code != 200:
        return {"error": f"Le client LoL a refusé la lecture des maîtrises (HTTP {response.status_code})."}, 502

    try:
        mastery_data = response.json()
    except ValueError:
        return {"error": "Le client LoL a renvoyé des données de maîtrise invalides."}, 502

    if not isinstance(mastery_data, list):
        return {"error": "Le format des données de maîtrise renvoyées par le client est invalide."}, 502

    champions = []
    required_fields = (
        "championId",
        "championLevel",
        "championPoints",
        "championPointsUntilNextLevel",
        "markRequiredForNextLevel",
        "tokensEarned",
    )
    for mastery_item in mastery_data:
        if not isinstance(mastery_item, dict) or any(
            not isinstance(mastery_item.get(field), int) or isinstance(mastery_item.get(field), bool)
            for field in required_fields
        ):
            return {"error": "Une entrée de maîtrise renvoyée par le client est invalide."}, 502

        champion_id = mastery_item["championId"]
        xp_until_next_level = mastery_item["championPointsUntilNextLevel"]
        marks_required = max(0, mastery_item["markRequiredForNextLevel"])
        tokens_earned = max(0, mastery_item["tokensEarned"])
        has_next_level = xp_until_next_level > 0 or marks_required > 0

        champions.append({
            "championId": champion_id,
            "name": champ_names.get(champion_id, f"ID LCU non reconnu ({champion_id})"),
            "isRecognized": champion_id in champ_names,
            "image": f"https://ddragon.leagueoflegends.com/cdn/{version}/img/champion/{champ_images[champion_id]}" if champion_id in champ_images else None,
            "championLevel": mastery_item["championLevel"],
            "championPoints": mastery_item["championPoints"],
            "xpRemaining": max(0, xp_until_next_level) if has_next_level else None,
            "hasNextLevel": has_next_level,
            "markRequiredForNextLevel": marks_required,
            "tokensEarned": tokens_earned,
        })

    return {"champions": champions}, 200
