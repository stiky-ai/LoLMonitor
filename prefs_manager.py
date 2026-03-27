# prefs_manager.py
# Gestion centralisée de skin_prefs.json (favorites + library auto-update)

import os
import json
import requests
import base64
import urllib3

urllib3.disable_warnings()

PREFS_FILE = "skin_prefs.json"
DEFAULT_PREFS = {
    "version": 2,
    "favorites": {},          # { "1": [123456, 789012], ... } → tes choix manuels
    "library": {}             # { "1": [ {"id":0, "name":"Default", "owned":true}, ... ], ... }
}

def load_prefs():
    if os.path.exists(PREFS_FILE):
        try:
            with open(PREFS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Migration simple si ancienne version
                if "library" not in data:
                    data["library"] = {}
                if "favorites" not in data:
                    data["favorites"] = {}
                return data
        except Exception as e:
            print(f"[Prefs] Erreur lecture JSON : {e}")
    return DEFAULT_PREFS.copy()

def save_prefs(data):
    try:
        with open(PREFS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"[Prefs] Sauvegardé : {len(data.get('library', {}))} champions dans library")
    except Exception as e:
        print(f"[Prefs] Erreur sauvegarde : {e}")

def update_library_from_lcu(base_url, headers, summoner_id):
    """
    Scan complet de la bibliothèque via LCU et met à jour 'library'
    Ne touche PAS 'favorites'
    """
    print("[Prefs] Mise à jour bibliothèque skins depuis LCU...")
    try:
        resp = requests.get(
            f"{base_url}/lol-champions/v1/inventories/{summoner_id}/champions",
            headers=headers, verify=False, timeout=10
        )
        if resp.status_code != 200:
            print(f"[Prefs] Échec récupération champions (HTTP {resp.status_code})")
            return False

        all_champs = resp.json()
        prefs = load_prefs()
        library = prefs.setdefault("library", {})
        changes = False

        for champ in all_champs:
            champ_id_str = str(champ["id"])
            champ_name = champ.get("name", f"Champion_{champ_id_str}")

            current_skins = {s["id"]: s for s in library.get(champ_id_str, [])}

            for skin in champ.get("skins", []):
                skin_id = skin["id"]
                skin_name = skin.get("name", f"Skin_{skin_id}")
                owned = skin.get("ownership", {}).get("owned", False)

                if skin_id not in current_skins:
                    current_skins[skin_id] = {
                        "id": skin_id,
                        "name": skin_name,
                        "owned": owned
                    }
                    changes = True
                else:
                    # Mise à jour owned si changé (ex: skin acheté)
                    if current_skins[skin_id]["owned"] != owned:
                        current_skins[skin_id]["owned"] = owned
                        changes = True

            if champ_id_str not in library or changes:
                library[champ_id_str] = list(current_skins.values())
                changes = True

        if changes:
            prefs["library"] = library
            save_prefs(prefs)
            print(f"[Prefs] Bibliothèque mise à jour ({len(library)} champions)")
            return True
        else:
            print("[Prefs] Bibliothèque déjà à jour")
            return False

    except Exception as e:
        print(f"[Prefs] Erreur update library : {e}")
        return False

def get_favorites_for_champ(champ_id):
    prefs = load_prefs()
    return prefs.get("favorites", {}).get(str(champ_id), [])

def set_favorites_for_champ(champ_id, fav_list):
    prefs = load_prefs()
    prefs.setdefault("favorites", {})[str(champ_id)] = fav_list
    save_prefs(prefs)