# main.py
# Lanceur corrigé – import TFT avant utilisation

import os
import sys
from threading import Thread
import time

for stream_name in ("stdout", "stderr"):
    stream = getattr(sys, stream_name)
    if stream is None:
        setattr(sys, stream_name, open(os.devnull, "w", encoding="utf-8"))
    elif hasattr(stream, "reconfigure"):
        stream.reconfigure(errors="backslashreplace")

# Imports LoL (existant)
from hud_monitor import run_hud
from skin_randomizer import run_skin_randomizer

# Import TFT – placé en haut pour éviter UnboundLocalError
try:
    from tft_randomizer import run_tft_randomizer
except ImportError:
    print("ATTENTION : tft_randomizer.py non trouvé ou non valide")
    run_tft_randomizer = None  # sécurité

def run_mastery_server():
    from lol_mastery import run_mastery_app
    run_mastery_app(open_browser=False)

def main():
    mode = "both" if len(sys.argv) == 1 else sys.argv[1].lower()

    if mode in ("both", "all"):
        print("Lancement complet : HUD LoL + Maîtrises + Skin Randomizer + TFT Randomizer")

        t_mastery = Thread(target=run_mastery_server, daemon=True)
        t_mastery.start()
        
        # LoL HUD (principal, bloque le thread)
        t_hud = Thread(target=run_hud, daemon=True)
        t_hud.start()
        
        # Skin Random LoL
        t_skin = Thread(target=run_skin_randomizer, daemon=True)
        t_skin.start()
        
        # TFT Randomizer (si le module existe)
        if run_tft_randomizer:
            t_tft = Thread(target=run_tft_randomizer, daemon=True)
            t_tft.start()
        else:
            print("TFT Randomizer désactivé (module non chargé)")
        
        # Garde le programme vivant
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            print("Arrêt demandé (Ctrl+C)")

    elif mode == "hud":
        print("Lancement du HUD LoL et des maîtrises")
        t_mastery = Thread(target=run_mastery_server, daemon=True)
        t_mastery.start()
        run_hud()

    elif mode == "skin":
        print("Lancement Skin Randomizer LoL uniquement")
        run_skin_randomizer()

    elif mode == "tft":
        print("Lancement TFT Randomizer uniquement")
        if run_tft_randomizer:
            run_tft_randomizer()
        else:
            print("Erreur : tft_randomizer.py non trouvé")

    elif mode == "mastery":
        print("Lancement LoLMastery uniquement")
        from lol_mastery import run_mastery_app
        run_mastery_app()

    else:
        print("Modes disponibles :")
        print("  python main.py          → tout (HUD + Maîtrises + Skin + TFT)")
        print("  python main.py hud      → HUD LoL et maîtrises")
        print("  python main.py mastery  → LoLMastery seul")
        print("  python main.py skin     → random skin LoL seul")
        print("  python main.py tft      → random TFT seul")

if __name__ == "__main__":
    main()