# tft_randomizer.py
# =========================================================
# 🎮 TFT Randomizer - Version FINALE corrigée (mars 2026)
# =========================================================

import os
import time
import base64
import random
import requests
import urllib3
import json
from threading import Thread

urllib3.disable_warnings()

POLL_INTERVAL = 2.0
PREFS_FILE = "tft_prefs.json"
LOCKFILE_CANDIDATES = [
    r"C:\Riot Games\League of Legends\lockfile",
    os.path.expanduser(r"~\AppData\Local\Riot Games\League of Legends\lockfile"),
]

AUTO_TFT_RANDOM_ENABLED = True
SET_NAME = "current"
ARAM_COMPANION_ID = 67001  # Ribamboule de Poros

last_lobby_state = "OTHER"
prefs = {}

def log(msg):
    print(f"[TFT-Random] {time.strftime('%H:%M:%S')} | {msg}")

def load_prefs():
    if os.path.exists(PREFS_FILE):
        try:
            with open(PREFS_FILE, encoding="utf-8") as f:
                data = json.load(f)
                data.setdefault("automation_enabled", True)
                return data
        except Exception as e:
            log(f"Erreur lecture prefs : {e}")
    template = {
        "version": 1,
        "automation_enabled": True,
        "favorites": {
            "companions": [],
            "map_skins": [],
            "damage_skins": [],
            "zoom_skins": []
        },
        "library": {
            "companions": [],
            "map_skins": [],
            "damage_skins": [],
            "zoom_skins": []
        }
    }
    with open(PREFS_FILE, "w", encoding="utf-8") as f:
        json.dump(template, f, indent=4, ensure_ascii=False)
    log("tft_prefs.json créé")
    return template

def save_prefs(data):
    try:
        if os.path.exists(PREFS_FILE):
            with open(PREFS_FILE, encoding="utf-8") as f:
                latest_data = json.load(f)
            data["automation_enabled"] = latest_data.get("automation_enabled", data.get("automation_enabled", True))
        with open(PREFS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        log(f"tft_prefs.json sauvegardé ({len(data.get('library', {}))} catégories)")
    except Exception as e:
        log(f"Erreur sauvegarde : {e}")

prefs = load_prefs()

# ====================== SCAN ======================
def get_tft_inventory(base_url, headers):
    inventory = {
        "companions": [],
        "map_skins": [],
        "damage_skins": [],
        "zoom_skins": []
    }

    # 1. Scan inventaire classique
    endpoint_templates = {
        "companions": f"/lol-cosmetics/v1/inventories/{SET_NAME}/companions",
        "map_skins": f"/lol-cosmetics/v1/inventories/{SET_NAME}/map-skins",
        "damage_skins": f"/lol-cosmetics/v1/inventories/{SET_NAME}/damage-skins",
        "zoom_skins": f"/lol-cosmetics/v1/inventories/{SET_NAME}/zoom-skins"
    }

    for cat, path in endpoint_templates.items():
        try:
            r = requests.get(f"{base_url}{path}", headers=headers, verify=False, timeout=6)
            if r.status_code == 200:
                data = r.json()
                log(f"  → SUCCÈS inventaire {cat.replace('_', ' ').title()}")

                groups = data.get("groups", [])
                owned_items = []

                for group in groups:
                    items = group.get("items", [])
                    for item in items:
                        if item.get("owned", False):
                            item_id = item.get("itemId") or item.get("contentId")
                            if item_id is None:
                                log(f"    → Item ignoré (pas d'ID) : {item.get('name', 'sans nom')}")
                                continue

                            name = item.get("name", f"{cat}_{item_id}")
                            companion_type = item.get("companionType", "unknown")

                            owned_items.append({
                                "id": item_id,
                                "name": name,
                                "owned": True,
                                "type": companion_type,
                                "level": item.get("level", 1),
                                "source": "inventory"
                            })

                inventory[cat] = owned_items
                log(f"    → {cat.replace('_', ' ').title()} depuis inventaire : {len(owned_items)}")
            else:
                log(f"  → inventaire {cat.replace('_', ' ').title()} : HTTP {r.status_code}")
        except Exception as e:
            log(f"  → Erreur inventaire {cat.replace('_', ' ').title()} : {str(e)}")

    # 2. FORCAGE : Ajout des companions depuis FAVORITES (tes Chibi manuels)
    try:
        fav_path = "/lol-cosmetics/v1/favorites/tft/companions"
        log(f"  → [FAVORIS] Tentative GET {fav_path}")
        r_fav = requests.get(f"{base_url}{fav_path}", headers=headers, verify=False, timeout=6)
        
        log(f"  → [FAVORIS] Réponse HTTP : {r_fav.status_code}")
        if r_fav.status_code != 200:
            log(f"  → [FAVORIS] Erreur HTTP {r_fav.status_code} - Contenu : {r_fav.text[:500] or '[vide]'}")
            raise Exception(f"HTTP {r_fav.status_code}")

        fav_data = r_fav.json()
        log(f"  → [FAVORIS] Type de réponse : {type(fav_data).__name__}")

        # Log complet de la réponse brute
        fav_raw = json.dumps(fav_data, indent=2, ensure_ascii=False)
        log(f"  → [FAVORIS] Réponse complète (brut JSON) :\n{fav_raw}")

        # Détection structure
        if isinstance(fav_data, list):
            log(f"  → [FAVORIS] Structure LIST directe détectée : {len(fav_data)} favoris lus")
            fav_list = fav_data
        elif isinstance(fav_data, dict):
            log(f"  → [FAVORIS] Structure DICT détectée : {len(fav_data)} clés")
            possible_keys = ["favoriteItems", "items", "data", "favorites", "content", "companions"]
            fav_list = []
            for key in possible_keys:
                if key in fav_data and isinstance(fav_data[key], list):
                    fav_list = fav_data[key]
                    log(f"  → [FAVORIS] Liste trouvée dans clé '{key}' : {len(fav_list)} favoris")
                    break
            if not fav_list:
                log(f"  → [FAVORIS] Aucune liste trouvée dans le dict ! Clés disponibles : {list(fav_data.keys())}")
                fav_list = []
        else:
            log(f"  → [FAVORIS] Format inattendu : {type(fav_data).__name__}")
            fav_list = []

        log(f"  → [FAVORIS] Nombre total de favoris lus : {len(fav_list)}")

        fav_items = []
        skipped = 0
        chibi_fav = 0

        for idx, fav in enumerate(fav_list):
            log(f"  → [FAVORIS] Traitement favori #{idx+1}")

            item_id = fav.get("itemId") or fav.get("contentId")
            if item_id is None:
                log(f"    → Ignoré : pas d'itemId ni contentId → {json.dumps(fav, indent=2)[:200]}...")
                skipped += 1
                continue

            name = fav.get("name", f"companion_{item_id}")
            companion_type = fav.get("companionType", "unknown")
            level = fav.get("level", 1)
            owned = fav.get("owned", True)

            log(f"    → ID: {item_id} | Nom: {name} | Type: {companion_type} | Owned: {owned}")

            fav_items.append({
                "id": item_id,
                "name": name,
                "owned": owned,
                "type": companion_type,
                "level": level,
                "source": "favorites"
            })

            if companion_type == "kChibi":
                chibi_fav += 1
                log(f"    → Chibi détecté : {name} ({item_id})")

        log(f"  → [FAVORIS] Favoris valides créés : {len(fav_items)} (dont {chibi_fav} Chibi)")
        if skipped > 0:
            log(f"  → [FAVORIS] {skipped} favoris ignorés (pas d'ID)")

        # Fusion sans doublons
        existing_ids = {str(item["id"]) for item in inventory["companions"]}
        new_fav = []
        for item in fav_items:
            id_str = str(item["id"])
            if id_str not in existing_ids:
                new_fav.append(item)
                existing_ids.add(id_str)
                log(f"  → [FAVORIS] Ajouté : {item['name']} ({item['id']}) - Type: {item['type']}")
            else:
                log(f"  → [FAVORIS] Ignoré (déjà présent) : {item['name']} ({item['id']})")

        inventory["companions"].extend(new_fav)

        chibi_from_fav = sum(1 for item in new_fav if item["type"] == "kChibi")
        log(f"  → [FAVORIS] Ajout forcé depuis favoris : {len(new_fav)} nouveaux (dont {chibi_from_fav} Chibi)")

        if len(new_fav) > 0:
            log(f"  → [FAVORIS] Exemple premier ajouté :\n{json.dumps(new_fav[0], indent=2)}")

    except Exception as e:
        log(f"  → [FAVORIS] Erreur complète lors du traitement favoris companions : {str(e)}")

    # Log final
    total_comp = len(inventory["companions"])
    chibi_total = sum(1 for item in inventory["companions"] if item.get("type") == "kChibi")
    log(f"  → TOTAL Companions possédés (inventaire + favoris forcés) : {total_comp} (dont {chibi_total} Chibi)")

    return inventory

# ====================== APPLICATION ======================
def apply_random_selection(base_url, headers, category, item_id):
    endpoints = {
        "companions": f"{base_url}/lol-cosmetics/v1/selection/companion",
        "map_skins": f"{base_url}/lol-cosmetics/v1/selection/tft-map-skin",
        "damage_skins": f"{base_url}/lol-cosmetics/v1/selection/tft-damage-skin",
        "zoom_skins": f"{base_url}/lol-cosmetics/v1/selection/tft-zoom-skin"
    }
    if category not in endpoints:
        log(f"  → Catégorie inconnue : {category}")
        return False

    payload = item_id  # brut (entier)

    try:
        r = requests.put(endpoints[category], json=payload, headers=headers, verify=False, timeout=5)
        log(f"  → PUT {category} → HTTP {r.status_code} | Payload brut : {payload}")
        if r.status_code in (200, 201, 204):
            log(f"  → Succès ! {category} appliqué")
            return True
        else:
            log(f"  → Erreur PUT : {r.text[:400]}...")
            return False
    except Exception as e:
        log(f"  → Erreur PUT {category} : {str(e)}")
        return False

# ====================== WORKER ======================
def tft_random_worker():
    global last_lobby_state, prefs
    log("TFT Randomizer démarré")

    while True:
        prefs = load_prefs()
        if not AUTO_TFT_RANDOM_ENABLED or prefs.get("automation_enabled", True) is not True:
            last_lobby_state = "OTHER"
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
        headers = {"Authorization": f"Basic {auth_encoded}", "User-Agent": "LeagueOfLegendsClient"}

        try:
            lobby = requests.get(f"{base_url}/lol-lobby/v2/lobby", headers=headers, verify=False, timeout=4).json()
            game_mode = str(lobby.get("gameMode", "")).upper()
            current_is_tft = game_mode == "TFT" or "TFT" in str(lobby).upper()
            current_is_aram = "ARAM" in game_mode or "ARAM" in str(lobby).upper()

            if current_is_tft and last_lobby_state != "TFT":
                log("→ ENTRÉE FRAÎCHE EN LOBBY TFT → Scan + random...")

                inventory = get_tft_inventory(base_url, headers)
                if any(len(lst) > 0 for lst in inventory.values()):
                    library = prefs.setdefault("library", {})
                    updated = False
                    for cat in inventory:
                        if inventory[cat] != library.get(cat, []):
                            library[cat] = inventory[cat]
                            updated = True
                            log(f"  → {cat.replace('_', ' ').title()} mis à jour : {len(inventory[cat])}")

                    if updated:
                        prefs["library"] = library
                        save_prefs(prefs)
                        log("→ tft_prefs.json mis à jour")
                else:
                    log("→ Inventaire vide")

                # Random unique
                automation_disabled = False
                for category in ["companions", "map_skins", "damage_skins", "zoom_skins"]:
                    if load_prefs().get("automation_enabled", True) is not True:
                        automation_disabled = True
                        break
                    items = inventory.get(category, [])
                    if not items:
                        log(f"  → Aucun {category.replace('_', ' ')} possédé")
                        continue

                    fav_ids = prefs.get("favorites", {}).get(category, [])
                    eligible = [item for item in items if item["id"] in fav_ids]

                    if eligible:
                        chosen = random.choice(eligible)
                        log(f"  → Random favori ({len(eligible)}) pour {category}")
                    else:
                        chosen = random.choice(items)
                        log(f"  → Random parmi {len(items)} possédés pour {category}")

                    item_id = chosen["id"]
                    item_name = chosen["name"]

                    if load_prefs().get("automation_enabled", True) is not True:
                        automation_disabled = True
                        break
                    if apply_random_selection(base_url, headers, category, item_id):
                        log(f"  → {category.upper().replace('_', ' ')} APPLIQUÉ : {item_name} (ID {item_id})")
                    else:
                        log(f"  → Échec {category}")

                if automation_disabled:
                    last_lobby_state = "OTHER"
                    continue
                last_lobby_state = "TFT"

            elif current_is_aram and last_lobby_state != "ARAM":
                log("→ ENTRÉE FRAÎCHE EN LOBBY ARAM / ARAM MAYHEM → Sélection automatique de Ribamboule de Poros")
                if load_prefs().get("automation_enabled", True) is not True:
                    last_lobby_state = "OTHER"
                elif apply_random_selection(base_url, headers, "companions", ARAM_COMPANION_ID):
                    log(f"  → COMPANION APPLIQUÉ : Ribamboule de Poros (ID {ARAM_COMPANION_ID})")
                    last_lobby_state = "ARAM"
                else:
                    log("  → Échec application compagnon ARAM")
                    last_lobby_state = "ARAM"

            elif not current_is_tft and not current_is_aram and last_lobby_state in ("TFT", "ARAM"):
                log("→ Sortie lobby TFT/ARAM")
                last_lobby_state = "OTHER"

        except Exception as e:
            log(f"Erreur check lobby: {str(e)}")
            pass

        time.sleep(POLL_INTERVAL)


def run_tft_randomizer():
    log("Démarrage TFT Randomizer")
    t = Thread(target=tft_random_worker, daemon=True)
    t.start()
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        log("Arrêt")

if __name__ == "__main__":
    run_tft_randomizer()