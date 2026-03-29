# skin_randomizer.py
# Version corrigée – évite clés négatives et IDs invalides

import os
import time
import base64
import random
import requests
import urllib3
import json
from threading import Thread

urllib3.disable_warnings()

# ────────────────────────────────────────────────
# CONFIG
# ────────────────────────────────────────────────
EXCLUDE_DEFAULT_SKIN = True
POLL_INTERVAL = 1.8
PREFS_FILE = "skin_prefs.json"

LOCKFILE_CANDIDATES = [
    r"C:\Riot Games\League of Legends\lockfile",
    os.path.expanduser(r"~\AppData\Local\Riot Games\League of Legends\lockfile"),
    # Ajoute ici ton chemin si différent
]

AUTO_RANDOM_ENABLED = True
AUTO_SPELL_SELECTION_ENABLED = True
SNOWBALL_SPELL_ID = 32  # ID probable de Boule de neige dans l’API LCU
FLASH_SPELL_ID = 4      # Flash
# ────────────────────────────────────────────────

last_champ_id = None
prefs = {}

def log(msg):
    print(f"[SkinRandom] {time.strftime('%H:%M:%S')} | {msg}")

def load_prefs():
    if os.path.exists(PREFS_FILE):
        try:
            with open(PREFS_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log(f"Erreur lecture prefs : {e}")
    return {"version": 2, "favorites": {}, "library": {}}

def save_prefs(data):
    try:
        with open(PREFS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        log(f"skin_prefs.json sauvegardé ({len(data.get('library', {}))} champions)")
    except Exception as e:
        log(f"Erreur sauvegarde prefs : {e}")

prefs = load_prefs()

# ====================== SPELLS AUTO-SELECTION ======================
def apply_summoner_spells(base_url, headers, spell1_id, spell2_id):
    try:
        my_sel_resp = requests.get(
            f"{base_url}/lol-champ-select/v1/session/my-selection",
            headers=headers, verify=False, timeout=5
        )
        if my_sel_resp.status_code != 200:
            log(f"  → Impossible de lire my-selection (HTTP {my_sel_resp.status_code})")
            return False

        selection = my_sel_resp.json()
        payload = selection.copy()

        if "spell1Id" in selection or "spell2Id" in selection:
            payload["spell1Id"] = spell1_id
            payload["spell2Id"] = spell2_id
        elif "summonerSpellOne" in selection and "summonerSpellTwo" in selection:
            payload["summonerSpellOne"] = {"id": spell1_id}
            payload["summonerSpellTwo"] = {"id": spell2_id}
        else:
            payload["spell1Id"] = spell1_id
            payload["spell2Id"] = spell2_id

        patch_resp = requests.patch(
            f"{base_url}/lol-champ-select/v1/session/my-selection",
            json=payload, headers=headers, verify=False, timeout=5
        )

        if patch_resp.status_code in (200, 201, 204):
            log("  → Sorts appliqués : Boule de neige (D) + Flash (F)")
            return True

        log(f"  → Échec application sorts (HTTP {patch_resp.status_code})")
        return False

    except Exception as e:
        log(f"  → Erreur application sorts : {e}")
        return False

# ====================== UPDATE LIBRARY (corrigé) ======================
def update_skin_library(base_url, headers, summoner_id):
    global prefs
    log("Mise à jour complète de la bibliothèque skins...")

    try:
        resp = requests.get(
            f"{base_url}/lol-champions/v1/inventories/{summoner_id}/champions",
            headers=headers, verify=False, timeout=12
        )
        if resp.status_code != 200:
            log(f"Impossible de récupérer la bibliothèque (HTTP {resp.status_code})")
            return

        all_champs = resp.json()
        library = prefs.setdefault("library", {})
        updated = 0
        ignored = 0

        for champ in all_champs:
            champ_id_raw = champ.get("id")
            if not isinstance(champ_id_raw, int) or champ_id_raw <= 0:
                ignored += 1
                log(f"Champion ignoré (ID invalide) : {champ.get('name', 'Inconnu')}")
                continue

            champ_id = str(champ_id_raw)
            champ_name = champ.get("name", f"Champion_{champ_id}")

            skins_list = []
            for skin in champ.get("skins", []):
                skin_id = skin.get("id")
                if not isinstance(skin_id, int):
                    continue

                skin_name = skin.get("name", f"Skin_{skin_id}")
                owned = skin.get("ownership", {}).get("owned", False)

                # Forcer owned=true pour skin de base si champion possédé
                if skin_id in (0, champ_id_raw * 1000):  # patterns courants skin base
                    owned = True

                skins_list.append({
                    "id": skin_id,
                    "name": skin_name,
                    "owned": owned
                })

            if not skins_list:
                continue

            # Mise à jour ou création
            if champ_id not in library:
                library[champ_id] = skins_list
                updated += 1
                log(f"→ Nouveau champion ajouté : {champ_name} ({len(skins_list)} skins)")
            else:
                current = {s["id"]: s for s in library[champ_id]}
                changed = False
                for new_skin in skins_list:
                    sid = new_skin["id"]
                    if sid in current:
                        if current[sid]["owned"] != new_skin["owned"]:
                            current[sid]["owned"] = new_skin["owned"]
                            changed = True
                    else:
                        current[sid] = new_skin
                        changed = True
                if changed:
                    updated += 1
                library[champ_id] = list(current.values())

        prefs["library"] = library
        prefs["version"] = 2
        save_prefs(prefs)
        log(f"✅ Bibliothèque mise à jour : {len(library)} champions | {updated} modifiés | {ignored} ignorés")

    except Exception as e:
        log(f"Erreur lors de la mise à jour library : {e}")

# ====================== WORKER PRINCIPAL ======================
def random_skin_worker():
    global last_champ_id, prefs
    log("Thread démarré – polling + mise à jour automatique library")

    library_updated = False

    while True:
        if not AUTO_RANDOM_ENABLED:
            time.sleep(5)
            continue

        lock_path = next((p for p in LOCKFILE_CANDIDATES if os.path.isfile(p)), None)
        if not lock_path:
            time.sleep(4)
            continue

        try:
            with open(lock_path, "r") as f:
                parts = f.read().strip().split(":")
            lock = {"port": parts[2], "password": parts[3], "protocol": parts[4]}
        except:
            time.sleep(3)
            continue

        base_url = f"{lock['protocol']}://127.0.0.1:{lock['port']}"
        auth_raw = f"riot:{lock['password']}"
        auth_encoded = base64.b64encode(auth_raw.encode('utf-8')).decode('utf-8')

        headers = {
            "Authorization": f"Basic {auth_encoded}",
            "User-Agent": "LeagueOfLegendsClient",
            "Accept": "application/json"
        }

        try:
            # Mise à jour library une seule fois
            if not library_updated:
                me_resp = requests.get(f"{base_url}/lol-summoner/v1/current-summoner", headers=headers, verify=False, timeout=5)
                if me_resp.status_code == 200:
                    summoner_id = me_resp.json().get("summonerId")
                    if summoner_id:
                        update_skin_library(base_url, headers, summoner_id)
                        library_updated = True

            # Le reste du code pour le random skin (inchangé)
            session_resp = requests.get(f"{base_url}/lol-champ-select/v1/session", headers=headers, verify=False, timeout=4)
            if session_resp.status_code != 200:
                last_champ_id = None
                time.sleep(1.5)
                continue

            session = session_resp.json()
            my_cell = next((p for p in session.get("myTeam", []) if p.get("summonerId") == summoner_id), None)
            if not my_cell:
                last_champ_id = None
                time.sleep(1.5)
                continue

            champ_id = my_cell.get("championId", 0)
            if champ_id <= 0:
                last_champ_id = None
                time.sleep(1.5)
                continue

            if champ_id != last_champ_id:
                log(f"→ CHANGEMENT DÉTECTÉ → Champion ID {champ_id}")

                last_champ_id = champ_id

                # Récup skins possédés
                skins_url = f"{base_url}/lol-champions/v1/inventories/{summoner_id}/champions/{champ_id}/skins"
                skins_resp = requests.get(skins_url, headers=headers, verify=False, timeout=5)
                if skins_resp.status_code != 200:
                    log(f"  → Erreur récupération skins (HTTP {skins_resp.status_code})")
                    continue

                all_skins_data = skins_resp.json()
                owned_skins_info = [
                    {"id": s["id"], "name": s.get("name", f"Skin_{s['id']}"), "owned": s.get("ownership", {}).get("owned", False)}
                    for s in all_skins_data
                ]

                owned_skins = [s["id"] for s in owned_skins_info if s["owned"] and (not EXCLUDE_DEFAULT_SKIN or s["id"] != 0)]

                if not owned_skins:
                    log("  → Aucun skin possédé pour ce champion → impossible de randomiser")
                    continue

                # Logs détaillés des skins possédés
                log(f"  → Skins possédés ({len(owned_skins)}) sur lesquels le random peut se baser :")
                for s in owned_skins_info:
                    if s["owned"]:
                        log(f"     • {s['name']} (ID {s['id']})")

                # Favoris
                favorites = prefs.get("favorites", {}).get(str(champ_id), [])
                eligible_favs = [sid for sid in favorites if sid in owned_skins]

                if favorites:
                    log(f"  → Favoris définis ({len(favorites)}) : {favorites}")
                    if eligible_favs:
                        log(f"  → Favoris possédés ({len(eligible_favs)}) : {eligible_favs}")
                        skin_id = random.choice(eligible_favs)
                        chosen_name = next((s["name"] for s in owned_skins_info if s["id"] == skin_id), f"Skin_{skin_id}")
                        log(f"  → Skin choisi parmi les favoris possédés : {chosen_name} (ID {skin_id})")
                    else:
                        log("  → Aucun favori possédé → fallback sur tous les skins possédés")
                        skin_id = random.choice(owned_skins)
                        chosen_name = next((s["name"] for s in owned_skins_info if s["id"] == skin_id), f"Skin_{skin_id}")
                        log(f"  → Skin choisi (fallback) : {chosen_name} (ID {skin_id})")
                else:
                    log("  → Aucun favori défini → random parmi tous les skins possédés")
                    skin_id = random.choice(owned_skins)
                    chosen_name = next((s["name"] for s in owned_skins_info if s["id"] == skin_id), f"Skin_{skin_id}")
                    log(f"  → Skin choisi : {chosen_name} (ID {skin_id})")

                # Application
                if skin_id:
                    payload = {"selectedSkinId": skin_id}
                    patch_resp = requests.patch(
                        f"{base_url}/lol-champ-select/v1/session/my-selection",
                        json=payload, headers=headers, verify=False, timeout=5
                    )
                    if patch_resp.status_code in (200, 204):
                        log(f"  → SKIN APPLIQUÉ AVEC SUCCÈS : {chosen_name} (ID {skin_id})")
                    else:
                        log(f"  → ÉCHEC APPLICATION (HTTP {patch_resp.status_code})")
                else:
                    log("  → Aucun skin sélectionnable")

                if AUTO_SPELL_SELECTION_ENABLED:
                    if not apply_summoner_spells(base_url, headers, SNOWBALL_SPELL_ID, FLASH_SPELL_ID):
                        log("  → Échec de la sélection auto des sorts D/F")
        except Exception as e:
            log(f"Erreur dans le polling : {str(e)}")

        time.sleep(POLL_INTERVAL)


def run_skin_randomizer():
    log("Démarrage module random skin + auto-update library")
    t = Thread(target=random_skin_worker, daemon=True)
    t.start()
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        log("Arrêt demandé")


if __name__ == "__main__":
    run_skin_randomizer()