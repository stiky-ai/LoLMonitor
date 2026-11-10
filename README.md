# LoLMonitor

**HUD local et sélection automatique de cosmétiques pour League of Legends et Teamfight Tactics.**

LoLMonitor réunit un HUD accessible dans le navigateur, des outils de suivi et des fonctions de sélection de cosmétiques s'appuyant sur l'API locale du client Riot (LCU). Le programme s'exécute sur votre PC : il ne s'agit pas d'un service hébergé.

[Télécharger la dernière version Windows](https://github.com/stiky-ai/LoLMonitor/releases/latest)

> **À savoir :** LoLMonitor est un projet communautaire non officiel, sans affiliation ni approbation de Riot Games. Certaines fonctions utilisent l'API locale du client Riot, qui n'est pas une API publique stable. Elles peuvent cesser de fonctionner après une mise à jour du jeu ou du client.

## Sommaire

- [Fonctionnalités](#fonctionnalités)
- [Démarrage rapide — version Windows](#démarrage-rapide--version-windows)
- [Lancer depuis les sources](#lancer-depuis-les-sources)
- [Données locales et confidentialité](#données-locales-et-confidentialité)
- [Dépannage](#dépannage)
- [Développement et publication](#développement-et-publication)
- [Licence](#licence)
- [English](#english)

## Fonctionnalités

- **HUD LoL dans le navigateur** : suivi en direct des équipes, estimation de l'or à partir des objets, différence d'or et minuteurs de sorts.
- **Maîtrises** : consultation des maîtrises du compte connecté et filtres disponibles dans l'interface.
- **Préférences LoL** : bibliothèque de skins et favoris, avec sélection automatique de skins et de sorts d'invocateur pendant la sélection des champions.
- **Icônes d'invocateur** : préférences d'icône par défaut ou par champion.
- **Cosmétiques TFT** : favoris et sélection automatique de compagnons, skins de carte, dégâts et zoom; sélection du compagnon prévue par le programme en ARAM.

Le HUD web est servi localement sur **http://127.0.0.1:5000**. Il n'est pas nécessaire de rendre ce port accessible depuis Internet.

## Démarrage rapide — version Windows

1. Ouvrez la page [Dernière version](https://github.com/stiky-ai/LoLMonitor/releases/latest) et téléchargez `LoLMonitor-windows-x64.zip`.
2. Extrayez **tout** le contenu du ZIP dans un dossier, par exemple `Documents\LoLMonitor`.
3. Lancez `LoLMonitor.exe`. Une fenêtre de console reste ouverte pendant l'exécution.
4. Ouvrez **http://127.0.0.1:5000** dans votre navigateur.
5. Pour les fonctions qui utilisent le client Riot, démarrez League of Legends et connectez-vous. Pour les données en partie, lancez également une partie.

Fermez la fenêtre de console pour arrêter LoLMonitor. L'exécutable Windows est autonome : Python n'a pas besoin d'être installé.

### Prérequis et limites

- Windows 64 bits.
- Le client Riot doit être ouvert et connecté pour les fonctions qui lisent ou appliquent des sélections via la LCU.
- Une connexion Internet est utilisée pour récupérer les noms, versions et images publiques de **Data Dragon**. Sans réseau, certaines images ou informations peuvent manquer.
- Le HUD et le client utilisent des ports locaux fixes (HUD : `5000`; API de données de partie : `2999`). Si le port du HUD est déjà occupé, le serveur ne pourra pas démarrer.

## Lancer depuis les sources

Pour le développement ou pour exécuter le projet avec Python :

1. Installez Python **3.10 ou plus récent**.
2. Récupérez le code source (par exemple en clonant le dépôt).
3. À la racine du projet, installez les dépendances :

   ```powershell
   python -m pip install -r requirements.txt
   ```

4. Lancez le programme complet :

   ```powershell
   python main.py
   ```

Modes disponibles :

```powershell
python main.py hud   # HUD LoL uniquement
python main.py skin  # sélection automatique LoL uniquement
python main.py tft   # sélection automatique TFT uniquement
```

Le mode par défaut (sans argument) démarre le HUD, le randomizer LoL et le randomizer TFT. Pour les développeurs, `lol_hud.py` est également un HUD LoL autonome.

### Repères dans le code

| Fichier | Rôle |
|---|---|
| `main.py` | Lance le HUD et les randomizers, ou un mode individuel. |
| `hud_monitor.py` | HUD LoL/TFT, routes web locales, maîtrises et préférences. |
| `skin_randomizer.py` | Sélection LoL des skins, sorts et icônes via la LCU. |
| `tft_randomizer.py` | Sélection des cosmétiques TFT via la LCU. |
| `prefs_manager.py` | Fonctions de gestion des préférences LoL. |
| `test_tft_endpoints.py` | Diagnostic manuel des endpoints TFT; nécessite un client Riot actif et écrit un journal. |

## Données locales et confidentialité

- L'application communique avec le client Riot via son interface locale (LCU) sur le PC. Certaines fonctions appliquent des sélections au client, notamment des skins, sorts, icônes ou cosmétiques : elles ne sont pas uniquement en lecture.
- Le mot de passe temporaire du fichier `lockfile` Riot sert à authentifier les requêtes locales à la LCU. Il n'est pas nécessaire de le copier dans la configuration de LoLMonitor. Ne le partagez pas, et ne partagez pas de journaux qui pourraient contenir des réponses du client.
- Data Dragon fournit des données et images publiques. Le projet peut nécessiter Internet pour les récupérer; les appels à Data Dragon ne nécessitent pas les identifiants LCU.
- Les préférences sont enregistrées dans `skin_prefs.json` et `tft_prefs.json`, dans le répertoire de travail de l'application. Ces fichiers sont créés ou mis à jour à l'utilisation et ne sont **pas** inclus dans l'archive de release. Conservez-en une copie si vous souhaitez sauvegarder favoris et préférences.
- Fermez l'application si vous ne souhaitez plus qu'elle interroge le client local.

## Dépannage

| Problème | À essayer |
|---|---|
| La page ne s'ouvre pas | Vérifiez que la fenêtre de console est toujours ouverte et que le démarrage n'indique pas un port déjà utilisé. Essayez `http://127.0.0.1:5000`. |
| Aucune donnée de partie | Démarrez une partie de League of Legends. Les données en direct ne sont pas disponibles dans le lobby. |
| Bibliothèque ou maîtrises indisponibles | Vérifiez que le client Riot est ouvert, que vous êtes connecté et que le compte attendu est actif. |
| Images/noms manquants | Vérifiez votre connexion Internet et réessayez plus tard; ces ressources proviennent de Data Dragon. |
| La sélection automatique ne fonctionne plus | Une mise à jour du client peut modifier la LCU. Consultez les journaux de la console et les notes de la release; ne partagez pas les réponses du client contenant des informations personnelles. |

## Développement et publication

Les releases Windows sont construites par GitHub Actions. Pour publier une nouvelle version, un mainteneur crée et pousse un tag versionné, par exemple :

```powershell
git tag v1.0.0
git push origin v1.0.0
```

Le workflow construit `LoLMonitor.exe` sur Windows et publie `LoLMonitor-windows-x64.zip` dans une GitHub Release. Le ZIP contient l'exécutable et ce README, pas les préférences locales. Pour exécuter les vérifications Python de base :

```powershell
python -m py_compile main.py hud_monitor.py skin_randomizer.py tft_randomizer.py prefs_manager.py
```

## Licence

Le projet est distribué sous licence MIT (voir [`LICENSE`](LICENSE)).

---

## English

**A local browser HUD and automatic cosmetic selection tools for League of Legends and Teamfight Tactics.**

LoLMonitor combines a browser-based HUD, game data views, and cosmetic selection features that use the Riot Client's local API (LCU). It runs on your PC; it is not a hosted service.

[Download the latest Windows release](https://github.com/stiky-ai/LoLMonitor/releases/latest)

> **Please note:** LoLMonitor is an unofficial community project, not affiliated with or endorsed by Riot Games. Some features rely on the Riot Client's local API, which is not a stable public API. They may stop working after a game or client update.

### Features

- **League HUD in your browser:** live team data, item-based gold estimates, gold difference, and summoner-spell timers.
- **Masteries:** view mastery data for the account connected to the client, with filters in the interface.
- **League preferences:** skin library and favorites, with automatic skin and summoner-spell selection during champion select.
- **Summoner icons:** default and per-champion icon preferences.
- **TFT cosmetics:** favorites and automatic selection for companions, map, damage, and zoom skins; the program also selects a companion in ARAM.

The web HUD runs locally at **http://127.0.0.1:5000**. You do not need to expose this port to the Internet.

### Quick start — Windows release

1. Open [Latest release](https://github.com/stiky-ai/LoLMonitor/releases/latest) and download `LoLMonitor-windows-x64.zip`.
2. Extract **all** files from the ZIP into a folder, such as `Documents\LoLMonitor`.
3. Run `LoLMonitor.exe`. A console window stays open while the app is running.
4. Open **http://127.0.0.1:5000** in your browser.
5. For features that use the Riot Client, start League of Legends and sign in. For live match data, also start a game.

Close the console window to stop LoLMonitor. The Windows executable is standalone; Python does not need to be installed.

### Requirements and limitations

- 64-bit Windows.
- The Riot Client must be open and signed in for features that read or apply selections through the LCU.
- An Internet connection is used to retrieve public **Data Dragon** names, versions, and images. Some images or information may be missing while offline.
- The HUD and client use fixed local ports (HUD: `5000`; in-game data API: `2999`). If the HUD port is already in use, its server cannot start.

### Run from source

For development or to run the project with Python:

1. Install Python **3.10 or newer**.
2. Obtain the source code (for example, by cloning the repository).
3. From the project root, install the dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

4. Start all features:

   ```powershell
   python main.py
   ```

Available modes:

```powershell
python main.py hud   # League HUD only
python main.py skin  # League automatic selection only
python main.py tft   # TFT automatic selection only
```

With no argument, the default mode starts the HUD, League randomizer, and TFT randomizer. Developers can also run `lol_hud.py` as a standalone League HUD.

### Code map

| File | Purpose |
|---|---|
| `main.py` | Starts the HUD and randomizers, or one individual mode. |
| `hud_monitor.py` | League/TFT HUD, local web routes, masteries, and preferences. |
| `skin_randomizer.py` | League skin, spell, and icon selection through the LCU. |
| `tft_randomizer.py` | TFT cosmetic selection through the LCU. |
| `prefs_manager.py` | League preference helpers. |
| `test_tft_endpoints.py` | Manual TFT endpoint diagnostic; requires an active Riot Client and writes a log. |

### Local data and privacy

- The app communicates with the Riot Client through its local API (LCU) on your PC. Some features apply selections to the client, including skins, spells, icons, or cosmetics; they are not read-only.
- The temporary password in Riot's `lockfile` authenticates local LCU requests. You do not need to copy it into LoLMonitor's configuration. Do not share it or logs that may contain client responses.
- Data Dragon provides public data and images. The project may need Internet access to retrieve them; Data Dragon requests do not require LCU credentials.
- Preferences are stored in `skin_prefs.json` and `tft_prefs.json` in the application's working directory. They are created or updated during use and are **not** included in the release archive. Keep a backup if you want to preserve favorites and preferences.
- Close the app if you no longer want it to query the local client.

### Troubleshooting

| Problem | Try this |
|---|---|
| The page will not open | Make sure the console window is still open and check for a port-in-use error. Try `http://127.0.0.1:5000`. |
| No match data | Start a League of Legends game. Live match data is unavailable in the lobby. |
| Masteries or library unavailable | Make sure the Riot Client is open, signed in, and using the expected account. |
| Missing images or names | Check your Internet connection and try again later; these resources come from Data Dragon. |
| Automatic selection stopped working | A client update may have changed the LCU. Check the console output and release notes; do not share client responses that may contain personal information. |

### Development and releases

Windows releases are built by GitHub Actions. To publish a new version, a maintainer creates and pushes a version tag, for example:

```powershell
git tag v1.0.0
git push origin v1.0.0
```

The workflow builds `LoLMonitor.exe` on Windows and publishes `LoLMonitor-windows-x64.zip` in a GitHub Release. The ZIP contains the executable and this README, not local preferences. To run the basic Python syntax checks:

```powershell
python -m py_compile main.py hud_monitor.py skin_randomizer.py tft_randomizer.py prefs_manager.py
```

### License

The project is distributed under the MIT License (see [`LICENSE`](LICENSE)).
