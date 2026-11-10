# Consignes pour les agents

## Présentation du projet

LoLMonitor est une application Python pour League of Legends et Teamfight Tactics (TFT). Elle combine un HUD Flask, le suivi des données du jeu et la sélection de cosmétiques via l'API locale du client Riot (LCU).

## Structure

- `main.py` : lance le HUD et les randomizers ensemble ou séparément (`hud`, `skin`, `tft`).
- `hud_monitor.py` : HUD Flask LoL/TFT, préférences et interface web.
- `lol_hud.py` : HUD Flask LoL autonome.
- `skin_randomizer.py` : skins LoL, sorts et icônes d'invocateur.
- `tft_randomizer.py` : cosmétiques TFT.
- `prefs_manager.py` : fonctions de lecture, sauvegarde et mise à jour des préférences LoL.
- `test_tft_endpoints.py` : script manuel de diagnostic des endpoints de cosmétiques TFT.
- `README.md` : aperçu et lancement du projet.

## Modifications

- Préserver le comportement existant et faire des changements ciblés; garder les noms et conventions du projet lorsque possible.
- Le code et les messages destinés à l'utilisateur sont principalement en français.
- Si une question de clarification ou un choix nécessaire se présente, demander la réponse avec le menu interactif (outil `ask_user`) pendant le traitement, comme en mode plan; ne pas poser la question en texte libre dans le chat. Attendre la réponse avant de prendre une décision qui dépend de celle-ci.
- Les fichiers `skin_prefs.json` et `tft_prefs.json` sont des données locales utilisateur : ne pas les réinitialiser, remplacer ou inclure dans les changements sans demande explicite.
- Ne pas modifier les sorties générées (`build/`, `dist/`, caches, journaux) pour implémenter une fonctionnalité. `dist/` peut ne pas être ignoré par Git : vérifier l'état du dépôt avant toute opération de nettoyage ou de packaging.
- Préserver les changements déjà présents dans l'arbre de travail; ne pas annuler ou écraser du travail sans rapport avec la demande.

## Fin de traitement et opérations Git

- Après chaque demande entraînant des modifications, terminer le travail et ses vérifications, puis présenter un récapitulatif clair des changements et des validations.
- Dans le même traitement, demander ensuite le choix de l'utilisateur avec un menu interactif (`ask_user`) : **committer et pousser**, **committer seulement** ou **ne rien faire de plus**.
- N'effectuer aucun commit ni push avant le choix explicite de l'utilisateur. Si l'utilisateur choisit une action Git, ne porter que les changements de la tâche et préserver les autres modifications présentes dans l'arbre de travail.
- Si le choix de pousser ne peut pas être exécuté (par exemple, branche distante ou authentification indisponible), expliquer le blocage et ne pas prétendre que le push a réussi.

## LCU et données sensibles

- Le client Riot doit être lancé pour utiliser la LCU; les scripts recherchent son fichier `lockfile` et utilisent ses informations d'authentification.
- Ne jamais afficher, enregistrer dans les journaux, committer ou partager le mot de passe du `lockfile`, l'en-tête `Authorization`, ni des réponses contenant des données personnelles.
- Ne pas lancer d'actions de modification dans le client, de tests en direct ou de requêtes réseau sans que la tâche l'exige. Ne pas changer les endpoints ni les paramètres d'authentification pour contourner les contrôles du client.
- Les requêtes à Data Dragon utilisent le réseau. Garder les validations hors ligne quand c'est possible et ne pas envoyer de données du compte à un service externe.

## Validation

- Aucun manifeste de dépendances, configuration de formateur ou suite de tests automatisée générale n'est présent. Ne pas supposer de commande d'installation ou de test qui n'est pas définie par le dépôt.
- Pour une modification Python, lancer au minimum `python -m py_compile <fichiers-modifiés.py>` si l'interpréteur Python est disponible.
- `test_tft_endpoints.py` est un script manuel, pas une suite de tests hors ligne : il requiert le client Riot actif, interroge la LCU et écrit `tft_cosmetics_test.log`. Ne le lancer que si le diagnostic en direct est nécessaire et autorisé.
- Pour les changements du HUD, privilégier une vérification qui n'appelle pas le client en direct; signaler explicitement toute validation manuelle qui reste nécessaire.

<!-- rtk-instructions v2 -->
# RTK — Token-Optimized CLI

**rtk** is a CLI proxy that filters and compresses command outputs, cutting 60-90% of bash output.

## Rule

Prefix external programs with `rtk`:

```bash
# Instead of:              Use:
git status                 rtk git status
git log -10                rtk git log -10
cargo test                 rtk cargo test
docker ps                  rtk docker ps
kubectl get pods           rtk kubectl get pods
```

Do not prefix shell builtins or keywords — `test`, `[`, `read`, `cd`, `echo`,
`export`, `eval`, `source`, `printf`. Commands such as `test`, `read`, and
`env` also have RTK subcommands with different meanings; invoke the native
command directly when you need it.

## Meta commands (use directly)

```bash
rtk gain              # Token savings dashboard
rtk gain --history    # Per-command savings history
rtk discover          # Find missed rtk opportunities
rtk bypass <cmd>      # Run raw (no filtering) but track usage
```
<!-- /rtk-instructions -->
