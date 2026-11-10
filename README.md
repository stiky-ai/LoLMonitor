# LoLMonitor

Ce projet permet de monitorer et personnaliser l'affichage du HUD et des skins dans League of Legends Teamfight Tactics.

## Structure du projet
- `main.py`, `lol_hud.py`, `hud_monitor.py` : Scripts principaux
- `skin_randomizer.py`, `tft_randomizer.py` : Scripts de randomisation de skins
- `prefs_manager.py` : Gestion des préférences
- `skin_prefs.json`, `tft_prefs.json` : Fichiers de préférences utilisateurs
- `build/` : Dossiers de build générés automatiquement (à ignorer)
- `__pycache__/` : Fichiers de cache Python (à ignorer)

## Installation
1. Cloner ce dépôt
2. Installer les dépendances nécessaires (Python 3.x recommandé)

## Utilisation
Lancer le script principal selon la fonctionnalité souhaitée :
```bash
python main.py
```

Dans le HUD, ouvrez **Maîtrise** pour afficher les maîtrises du compte actuellement connecté au client LoL. Le client doit être ouvert et connecté. La liste est triée par XP restante; le filtre de niveau et le seuil de proximité (1 000 XP par défaut) sont réglables dans la vue.

## À ignorer dans le dépôt
- Fichiers de build
- Caches Python
- Fichiers de préférences utilisateurs (contenant des infos personnelles)

## Licence
MIT
