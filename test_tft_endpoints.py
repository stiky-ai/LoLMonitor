# test_all_cosmetics_endpoints.py
# Version très verbeuse + LOG FILE complet (tout le JSON brut)

import os
import base64
import requests
import urllib3
import json
import time
from datetime import datetime

urllib3.disable_warnings()

# Fichier log
LOG_FILE = "tft_cosmetics_test.log"

# Chemins lockfile (ajuste si besoin)
LOCKFILE_CANDIDATES = [
    r"C:\Riot Games\League of Legends\lockfile",
    os.path.expanduser(r"~\AppData\Local\Riot Games\League of Legends\lockfile"),
]

def log_to_file(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {msg}\n")

def get_client_info():
    lock_path = next((p for p in LOCKFILE_CANDIDATES if os.path.isfile(p)), None)
    if not lock_path:
        msg = "ERREUR : Aucun fichier lockfile trouvé\nAssure-toi que le client League est lancé"
        print(msg)
        log_to_file(msg)
        return None, None

    with open(lock_path, "r") as f:
        parts = f.read().strip().split(":")
    port = parts[2]
    password = parts[3]
    protocol = parts[4]

    base_url = f"{protocol}://127.0.0.1:{port}"
    auth_raw = f"riot:{password}"
    auth_encoded = base64.b64encode(auth_raw.encode('utf-8')).decode('utf-8')
    headers = {
        "Authorization": f"Basic {auth_encoded}",
        "User-Agent": "LeagueOfLegendsClient",
        "Accept": "application/json"
    }

    msg = f"Client détecté :\n  Base URL : {base_url}\n  Auth : Basic {auth_encoded[:20]}..."
    print(msg)
    log_to_file(msg)

    return base_url, headers

def test_endpoint(base_url, headers, path):
    url = f"{base_url}{path}"
    header = f"\n{'='*100}\nTEST ENDPOINT : {path}\nURL : {url}\n{'='*100}"
    print(header)
    log_to_file(header)

    try:
        start_time = time.time()
        r = requests.get(url, headers=headers, verify=False, timeout=10)
        duration = time.time() - start_time

        status_msg = f"Statut HTTP : {r.status_code} | Temps : {duration:.3f}s | Content-Type : {r.headers.get('Content-Type', 'inconnu')}"
        print(status_msg)
        log_to_file(status_msg)

        if r.status_code != 200:
            error_msg = f"Réponse erreur :\n{r.text[:4000] or '[vide]'}\n{'-'*80}"
            print(error_msg)
            log_to_file(error_msg)
            return

        # Réponse 200 → on affiche et log TOUT
        full_response_header = "\nRÉPONSE 200 - AFFICHAGE COMPLET DE LA RÉPONSE JSON :"
        print(full_response_header)
        log_to_file(full_response_header)

        try:
            data = r.json()
            json_str = json.dumps(data, indent=2, ensure_ascii=False)
            print(json_str)               # console (peut être tronqué si très long)
            log_to_file(json_str)         # fichier : TOUT sans limite
        except json.JSONDecodeError:
            raw_msg = "La réponse n'est PAS du JSON valide !\nContenu brut :\n" + r.text[:4000]
            print(raw_msg)
            log_to_file(raw_msg)

        # Résumé structuré (console + log)
        summary = "\nRÉSUMÉ STRUCTURÉ :"
        if isinstance(data, dict):
            summary += f"\nType : dictionnaire | Clés racine : {len(data)}"
            summary += "\nClés principales : " + ", ".join(list(data.keys())[:15])
            if "groups" in data:
                groups = data["groups"]
                summary += f"\nGroupes : {len(groups)}"
                if groups and "items" in groups[0]:
                    summary += f"\nItems dans premier groupe : {len(groups[0]['items'])}"
        elif isinstance(data, list):
            summary += f"\nType : liste | Éléments : {len(data)}"
            if data:
                summary += "\nPremier élément : " + json.dumps(data[0], indent=2)[:500] + "..."
        else:
            summary += f"\nType inattendu : {type(data).__name__}"
        print(summary)
        log_to_file(summary)

        print("-"*100 + "\n")
        log_to_file("-"*100 + "\n")

    except Exception as e:
        err_msg = f"EXCEPTION : {str(e)}"
        print(err_msg)
        log_to_file(err_msg)
        print("-"*100 + "\n")
        log_to_file("-"*100 + "\n")

def main():
    base_url, headers = get_client_info()
    if not base_url:
        return

    print("\n" + "="*100)
    print("TEST COMPLET DES ENDPOINTS COSMETICS TFT (GET seulement)")
    print("Date : 21 mars 2026")
    print("Client League doit être lancé et connecté")
    print("TOUT est loggé dans : tft_cosmetics_test.log (JSON brut complet)")
    print("="*100 + "\n")

    # Vidange du log au démarrage
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"TEST DÉBUTÉ LE {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

    # Liste des endpoints (seulement GET)
    endpoints = [
        "/lol-cosmetics/v1/favorites/tft/companions",
        "/lol-cosmetics/v1/favorites/tft/damage-skins",
        "/lol-cosmetics/v1/favorites/tft/map-skins",
        "/lol-cosmetics/v1/favorites/tft/zoom-skins",
        "/lol-cosmetics/v1/inventories/current/augment-pillars",
        "/lol-cosmetics/v1/inventories/current/companions",
        "/lol-cosmetics/v1/inventories/current/damage-skins",
        "/lol-cosmetics/v1/inventories/current/map-skins",
        "/lol-cosmetics/v1/inventories/current/playbooks",
        "/lol-cosmetics/v1/inventories/current/zoom-skins",
    ]

    for path in endpoints:
        test_endpoint(base_url, headers, path)
        time.sleep(1)  # pause pour ne pas flooder

    end_msg = "\n" + "="*100 + "\nFIN DU TEST\nRegarde tft_cosmetics_test.log pour TOUTES les réponses JSON brutes\n" + "="*100
    print(end_msg)
    log_to_file(end_msg)

if __name__ == "__main__":
    main()