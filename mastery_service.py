import base64
import json
import os
from statistics import median

import requests


LCU_LOCKFILE_CANDIDATES = [
    r"C:\Riot Games\League of Legends\lockfile",
    os.path.expanduser(r"~\AppData\Local\Riot Games\League of Legends\lockfile"),
]
_PROVISIONAL_MASTERY_UPDATES = {}
_MASTERY_GAIN_HISTORY_PATH = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
    "LoLMonitor",
    "mastery_gain_samples.json",
)
_MIN_REAL_GAIN_SAMPLES_FOR_ESTIMATE = 3
_LAST_MASTERY_SNAPSHOT = {}
_MATCH_MASTERY_SNAPSHOT = {}
_LAST_GAMEFLOW_PHASE = None


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
    global _LAST_GAMEFLOW_PHASE, _MATCH_MASTERY_SNAPSHOT

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

    if phase == "InProgress" and _LAST_GAMEFLOW_PHASE != "InProgress":
        _MATCH_MASTERY_SNAPSHOT = {
            champion_id: dict(mastery)
            for champion_id, mastery in _LAST_MASTERY_SNAPSHOT.items()
        }
    _LAST_GAMEFLOW_PHASE = phase

    return {"phase": phase}, 200


def get_champion_select_pool():
    response, error = _get_lcu_response("/lol-champ-select/v1/session")
    if error:
        return error

    if response.status_code == 404:
        return {
            "available": False,
            "selectedChampionIds": [],
            "benchChampionIds": [],
        }, 200
    if response.status_code != 200:
        return {
            "error": (
                "Le client LoL a refusé la lecture de la sélection "
                f"(HTTP {response.status_code})."
            )
        }, 502

    try:
        session = response.json()
    except ValueError:
        return {"error": "Le client LoL a renvoyé une sélection invalide."}, 502

    if not isinstance(session, dict) or not isinstance(session.get("myTeam"), list):
        return {"error": "Le format de la sélection renvoyée par le client est invalide."}, 502

    bench_champions = session.get("benchChampions", [])
    if not isinstance(bench_champions, list):
        return {"error": "Le format du banc de champions renvoyé par le client est invalide."}, 502
    if any(not isinstance(player, dict) for player in session["myTeam"]):
        return {"error": "Le format de l’équipe alliée renvoyé par le client est invalide."}, 502
    if any(not isinstance(champion, dict) for champion in bench_champions):
        return {"error": "Le format du banc de champions renvoyé par le client est invalide."}, 502

    selected_champion_ids = {
        champion_id
        for player in session["myTeam"]
        if (champion_id := _read_non_negative_int(player, "championId")) is not None
        and champion_id > 0
    }
    bench_champion_ids = {
        champion_id
        for champion in bench_champions
        if (champion_id := _read_non_negative_int(champion, "championId")) is not None
        and champion_id > 0
    } - selected_champion_ids

    return {
        "available": True,
        "selectedChampionIds": sorted(selected_champion_ids),
        "benchChampionIds": sorted(bench_champion_ids),
    }, 200


def _read_non_negative_int(data, *field_names):
    value = next((data.get(field) for field in field_names if field in data), None)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        return None
    return value


def _load_mastery_gain_samples():
    try:
        with open(_MASTERY_GAIN_HISTORY_PATH, "r", encoding="utf-8") as history_file:
            samples = json.load(history_file)
    except FileNotFoundError:
        return [], None
    except (OSError, ValueError) as error:
        return [], f"Impossible de lire l’historique local des gains de maîtrise : {error}"

    if not isinstance(samples, list):
        return [], "L’historique local des gains de maîtrise a un format invalide."

    valid_samples = [
        sample
        for sample in samples
        if isinstance(sample, dict)
        and _read_non_negative_int(sample, "gameId") is not None
        and _read_non_negative_int(sample, "championId") is not None
        and _read_non_negative_int(sample, "pointsGained") is not None
        and sample["pointsGained"] > 0
    ]
    return valid_samples, None


def _record_observed_mastery_gain(update):
    samples, error = _load_mastery_gain_samples()
    if error:
        return error

    game_id = update["gameId"]
    champion_id = update["championId"]
    if any(
        sample["gameId"] == game_id and sample["championId"] == champion_id
        for sample in samples
    ):
        return None

    samples.append({
        "gameId": game_id,
        "championId": champion_id,
        "pointsGained": update["championPointsGained"],
    })
    try:
        os.makedirs(os.path.dirname(_MASTERY_GAIN_HISTORY_PATH), exist_ok=True)
        with open(_MASTERY_GAIN_HISTORY_PATH, "w", encoding="utf-8") as history_file:
            json.dump(samples[-50:], history_file, ensure_ascii=True, indent=2)
    except OSError as write_error:
        return f"Impossible d’enregistrer l’historique local des gains de maîtrise : {write_error}"
    return None


def _read_current_champion_mastery(champion_id):
    response, error = _get_lcu_response(
        "/lol-champion-mastery/v1/local-player/champion-mastery"
    )
    if error:
        return None, error[0].get("error")
    if response.status_code != 200:
        return None, f"Lecture actuelle des maîtrises refusée (HTTP {response.status_code})."

    try:
        mastery_data = response.json()
    except ValueError:
        return None, "Le client a renvoyé des maîtrises invalides."
    if not isinstance(mastery_data, list):
        return None, "Le format des maîtrises renvoyées par le client est invalide."

    for mastery in mastery_data:
        if (
            isinstance(mastery, dict)
            and _read_non_negative_int(mastery, "championId") == champion_id
            and _read_non_negative_int(mastery, "championLevel") is not None
            and _read_non_negative_int(mastery, "championPoints") is not None
        ):
            return mastery, None
    return None, None


def _estimate_post_game_mastery_update(game_id, champion_id, warning=None):
    baseline = _MATCH_MASTERY_SNAPSHOT.get(champion_id)
    if baseline is not None:
        current_mastery, read_error = _read_current_champion_mastery(champion_id)
        if (
            current_mastery is not None
            and current_mastery["championPoints"] > baseline["championPoints"]
        ):
            observed_update = {
                "gameId": game_id,
                "championId": champion_id,
                "championLevel": current_mastery["championLevel"],
                "championPointsBeforeGame": baseline["championPoints"],
                "championPointsGained": (
                    current_mastery["championPoints"] - baseline["championPoints"]
                ),
                "championPointsUntilNextLevelAfterGame": _read_non_negative_int(
                    current_mastery,
                    "championPointsUntilNextLevel",
                ),
                "championLevelUp": (
                    current_mastery["championLevel"] > baseline["championLevel"]
                ),
                "pointsIntoLevel": None,
                "_fallbackBeforeGamePoints": baseline["championPoints"],
                "_isEstimated": False,
            }
            _PROVISIONAL_MASTERY_UPDATES[champion_id] = observed_update
            history_warning = _record_observed_mastery_gain(observed_update)
            public_update = {
                key: value
                for key, value in observed_update.items()
                if not key.startswith("_")
            }
            public_update["source"] = "observed-delta"
            if history_warning:
                public_update["warning"] = history_warning
            return {"available": True, **public_update}, 200
        if warning is None and read_error:
            warning = read_error

    samples, error = _load_mastery_gain_samples()
    if error:
        return {"error": error}, 500

    observed_gains = [sample["pointsGained"] for sample in samples]
    sample_count = len(observed_gains)
    if sample_count < _MIN_REAL_GAIN_SAMPLES_FOR_ESTIMATE or baseline is None:
        result = {
            "available": False,
            "estimatePending": True,
            "observedGainSamples": sample_count,
            "requiredGainSamples": _MIN_REAL_GAIN_SAMPLES_FOR_ESTIMATE,
            "pendingReason": (
                "missing-match-snapshot"
                if baseline is None
                else "insufficient-real-gains"
            ),
        }
        if warning:
            result["warning"] = warning
        return result, 200

    points_gained = int(round(median(observed_gains[-7:])))
    update = {
        "gameId": game_id,
        "championId": champion_id,
        "championLevel": baseline["championLevel"],
        "championPointsBeforeGame": baseline["championPoints"],
        "championPointsGained": points_gained,
        "championPointsUntilNextLevelAfterGame": (
            baseline["championPointsUntilNextLevel"] - points_gained
            if baseline.get("championPointsUntilNextLevel") is not None
            and baseline["championPointsUntilNextLevel"] > points_gained
            else None
        ),
        "championLevelUp": False,
        "pointsIntoLevel": None,
        "_fallbackBeforeGamePoints": baseline["championPoints"],
        "_isEstimated": True,
        "_estimateSampleCount": sample_count,
    }
    _PROVISIONAL_MASTERY_UPDATES[champion_id] = update
    public_update = {
        key: value
        for key, value in update.items()
        if not key.startswith("_")
    }
    public_update["isEstimated"] = True
    public_update["estimateSampleCount"] = sample_count
    if warning:
        public_update["warning"] = warning
    return {"available": True, **public_update}, 200


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
    points_since_last_level_before_game = _read_non_negative_int(
        data,
        "championPointsSinceLastLevelBeforeGame",
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
    elif not level_up and points_since_last_level_before_game is not None:
        points_into_level = points_since_last_level_before_game + points_gained

    if not level_up and points_until_next_level is None and points_until_next_level_before_game is not None:
        points_until_next_level = max(0, points_until_next_level_before_game - points_gained)

    return {
        "gameId": game_id,
        "championId": champion_id,
        "championLevel": level,
        "championPointsBeforeGame": points_before_game,
        "championPointsGained": points_gained,
        "championPointsUntilNextLevelAfterGame": points_until_next_level,
        "championLevelUp": level_up,
        "pointsIntoLevel": points_into_level,
        "_fallbackBeforeGamePoints": None,
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
        return _estimate_post_game_mastery_update(
            game_id,
            champion_id,
            "Le client n’a pas fourni le gain réel de maîtrise.",
        )
    if mastery_response.status_code in (204, 404):
        return _estimate_post_game_mastery_update(game_id, champion_id)
    if mastery_response.status_code != 200:
        return _estimate_post_game_mastery_update(
            game_id,
            champion_id,
            f"Le client a refusé le gain réel de maîtrise (HTTP {mastery_response.status_code}).",
        )

    try:
        mastery_update = mastery_response.json()
    except ValueError:
        return _estimate_post_game_mastery_update(
            game_id,
            champion_id,
            "Le client a renvoyé un gain de maîtrise invalide.",
        )

    normalized_update = _normalize_post_game_mastery_update(
        mastery_update,
        champion_id,
        game_id,
    )
    if normalized_update is None:
        return _estimate_post_game_mastery_update(
            game_id,
            champion_id,
            "Le client n’a pas fourni de gain réel exploitable.",
        )

    normalized_update["_isEstimated"] = False
    previous_update = _PROVISIONAL_MASTERY_UPDATES.get(champion_id)
    if previous_update and previous_update["gameId"] == game_id:
        if normalized_update["championPointsBeforeGame"] is None:
            normalized_update["_fallbackBeforeGamePoints"] = previous_update[
                "_fallbackBeforeGamePoints"
            ]
    _PROVISIONAL_MASTERY_UPDATES[champion_id] = normalized_update
    history_warning = _record_observed_mastery_gain(normalized_update)
    public_update = {
        key: value
        for key, value in normalized_update.items()
        if not key.startswith("_")
    }
    if history_warning:
        public_update["warning"] = history_warning
    return {"available": True, **public_update}, 200


def get_mastery_data(champ_names, champ_images, version):
    global _LAST_MASTERY_SNAPSHOT

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

    _LAST_MASTERY_SNAPSHOT = {
        item["championId"]: {
            "championLevel": item["championLevel"],
            "championPoints": item["championPoints"],
            "championPointsUntilNextLevel": (
                item["championPointsUntilNextLevel"]
                if isinstance(item.get("championPointsUntilNextLevel"), int)
                and not isinstance(item.get("championPointsUntilNextLevel"), bool)
                and item["championPointsUntilNextLevel"] >= 0
                else None
            ),
        }
        for item in mastery_data
        if isinstance(item, dict)
        and all(
            isinstance(item.get(field), int) and not isinstance(item.get(field), bool)
            for field in ("championId", "championLevel", "championPoints")
        )
    }

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
        if points_before_game is None:
            points_before_game = update["_fallbackBeforeGamePoints"]
        if points_before_game is None:
            if (
                champion
                and not update["championLevelUp"]
                and update["championPointsUntilNextLevelAfterGame"] is not None
                and champion["championLevel"] == update["championLevel"]
                and champion["xpRemaining"] == update["championPointsUntilNextLevelAfterGame"]
            ):
                del _PROVISIONAL_MASTERY_UPDATES[champion_id]
                continue
            points_before_game = current_points
            update["_fallbackBeforeGamePoints"] = points_before_game
        expected_points = (
            points_before_game + update["championPointsGained"]
            if points_before_game is not None
            else current_points
        )
        already_synchronized = (
            current_level >= update["championLevel"]
            and current_points >= expected_points
        )
        if update.get("_isEstimated") and champion:
            already_synchronized = already_synchronized or (
                current_level > update["championLevel"]
                or current_points > points_before_game
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
            if not update.get("_isEstimated"):
                champion["championLevel"] = update["championLevel"]
            champion["championPoints"] = expected_points
            if update["championPointsUntilNextLevelAfterGame"] is not None:
                champion["xpRemaining"] = update["championPointsUntilNextLevelAfterGame"]
                champion["hasNextLevel"] = bool(champion["xpRemaining"]) or champion["markRequiredForNextLevel"] > 0

        champion["isProvisional"] = True
        champion["championPointsGained"] = update["championPointsGained"]
        champion["pointsIntoLevel"] = update["pointsIntoLevel"]
        if update.get("_isEstimated"):
            champion["isEstimated"] = True
            champion["estimateSampleCount"] = update["_estimateSampleCount"]

    return {"champions": champions}, 200
