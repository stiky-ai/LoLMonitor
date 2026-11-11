import base64
import os

import requests


LCU_LOCKFILE_CANDIDATES = [
    r"C:\Riot Games\League of Legends\lockfile",
    os.path.expanduser(r"~\AppData\Local\Riot Games\League of Legends\lockfile"),
]
_PROVISIONAL_MASTERY_UPDATES = {}


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


def _read_non_negative_int(data, *field_names):
    value = next((data.get(field) for field in field_names if field in data), None)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        return None
    return value


def _normalize_post_game_mastery_update(data, champion_id, game_id):
    if not isinstance(data, dict):
        return None

    update_game_id = _read_non_negative_int(data, "gameId")
    updated_champion_id = _read_non_negative_int(data, "championId")
    level = _read_non_negative_int(data, "championLevel", "level")
    points_gained = _read_non_negative_int(data, "championPointsGained", "pointsGained")
    points_before_game = _read_non_negative_int(data, "championPointsBeforeGame")
    points_until_next_level = _read_non_negative_int(
        data,
        "championPointsUntilNextLevelAfterGame",
        "pointsUntilNextLevelAfterGame",
    )
    points_until_next_level_before_game = _read_non_negative_int(
        data,
        "championPointsUntilNextLevelBeforeGame",
    )
    level_up = data.get("championLevelUp", data.get("hasLeveledUp"))

    if (
        update_game_id != game_id
        or (updated_champion_id is not None and updated_champion_id != champion_id)
        or level is None
        or level < 1
        or points_gained is None
        or not isinstance(level_up, bool)
    ):
        return None

    points_into_level = None
    if level_up and points_until_next_level_before_game is not None:
        points_into_level = max(0, points_gained - points_until_next_level_before_game + 1)

    return {
        "gameId": game_id,
        "championId": champion_id,
        "championLevel": level,
        "championPointsBeforeGame": points_before_game,
        "championPointsGained": points_gained,
        "championPointsUntilNextLevelAfterGame": points_until_next_level,
        "championLevelUp": level_up,
        "pointsIntoLevel": points_into_level,
    }


def get_post_game_mastery_update():
    stats_response, error = _get_lcu_response("/lol-end-of-game/v1/eog-stats-block")
    if error:
        return error
    if stats_response.status_code in (204, 404):
        return {"available": False}, 200
    if stats_response.status_code != 200:
        return {"error": f"Le client LoL a refusé la lecture des résultats (HTTP {stats_response.status_code})."}, 502

    try:
        stats = stats_response.json()
    except ValueError:
        return {"error": "Le client LoL a renvoyé des résultats de partie invalides."}, 502
    if not isinstance(stats, dict):
        return {"error": "Le format des résultats de partie renvoyés par le client est invalide."}, 502

    game_id = _read_non_negative_int(stats, "gameId")
    local_player = stats.get("localPlayer")
    champion_id = _read_non_negative_int(local_player, "championId") if isinstance(local_player, dict) else None
    if game_id is None or champion_id is None:
        return {"available": False}, 200

    mastery_response, error = _get_lcu_response(
        "/lol-end-of-game/v1/champion-mastery-updates"
    )
    if error:
        return error
    if mastery_response.status_code in (204, 404):
        return {"available": False}, 200
    if mastery_response.status_code != 200:
        return {"error": f"Le client LoL a refusé la lecture des gains de maîtrise (HTTP {mastery_response.status_code})."}, 502

    try:
        mastery_update = mastery_response.json()
    except ValueError:
        return {"error": "Le client LoL a renvoyé des gains de maîtrise invalides."}, 502

    normalized_update = _normalize_post_game_mastery_update(
        mastery_update,
        champion_id,
        game_id,
    )
    if normalized_update is None:
        return {"available": False}, 200

    _PROVISIONAL_MASTERY_UPDATES[champion_id] = normalized_update
    return {"available": True, **normalized_update}, 200


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

    champion_by_id = {champion["championId"]: champion for champion in champions}
    for champion_id, update in list(_PROVISIONAL_MASTERY_UPDATES.items()):
        champion = champion_by_id.get(champion_id)
        current_level = champion["championLevel"] if champion else 0
        current_points = champion["championPoints"] if champion else 0
        points_before_game = update["championPointsBeforeGame"]
        expected_points = (
            points_before_game + update["championPointsGained"]
            if points_before_game is not None
            else current_points + update["championPointsGained"]
        )
        already_synchronized = current_level >= update["championLevel"] and (
            current_points >= expected_points or points_before_game is None
        )
        if already_synchronized:
            del _PROVISIONAL_MASTERY_UPDATES[champion_id]
            continue

        if champion is None:
            champion = {
                "championId": champion_id,
                "name": champ_names.get(champion_id, f"ID LCU non reconnu ({champion_id})"),
                "isRecognized": champion_id in champ_names,
                "image": f"https://ddragon.leagueoflegends.com/cdn/{version}/img/champion/{champ_images[champion_id]}" if champion_id in champ_images else None,
                "championLevel": update["championLevel"],
                "championPoints": expected_points,
                "xpRemaining": update["championPointsUntilNextLevelAfterGame"],
                "hasNextLevel": bool(update["championPointsUntilNextLevelAfterGame"]),
                "markRequiredForNextLevel": 0,
                "tokensEarned": 0,
            }
            champions.append(champion)
            champion_by_id[champion_id] = champion
        else:
            champion["championLevel"] = update["championLevel"]
            champion["championPoints"] = expected_points
            if update["championPointsUntilNextLevelAfterGame"] is not None:
                champion["xpRemaining"] = update["championPointsUntilNextLevelAfterGame"]
                champion["hasNextLevel"] = bool(champion["xpRemaining"]) or champion["markRequiredForNextLevel"] > 0

        champion["isProvisional"] = True
        champion["championPointsGained"] = update["championPointsGained"]
        champion["pointsIntoLevel"] = update["pointsIntoLevel"]

    return {"champions": champions}, 200
