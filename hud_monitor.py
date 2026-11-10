# hud_monitor.py
# =========================================================
# 🎮 LoL/TFT HUD - Monitoring + LoL Skins + TFT Random
# =========================================================

from flask import Flask, jsonify, render_template_string, request
import requests
import urllib3
import json
import os
import base64

urllib3.disable_warnings()

app = Flask(__name__)

LOL_PREFS_FILE = "skin_prefs.json"
TFT_PREFS_FILE = "tft_prefs.json"
LCU_LOCKFILE_CANDIDATES = [
    r"C:\Riot Games\League of Legends\lockfile",
    os.path.expanduser(r"~\AppData\Local\Riot Games\League of Legends\lockfile"),
]

CHAMP_NAMES = {}
CHAMP_IMAGES = {}
DD_VERSION = "latest"

def load_champ_names():
    global CHAMP_NAMES, CHAMP_IMAGES, DD_VERSION
    try:
        versions = requests.get("https://ddragon.leagueoflegends.com/api/versions.json").json()
        DD_VERSION = versions[0]
        data = requests.get(f"https://ddragon.leagueoflegends.com/cdn/{DD_VERSION}/data/fr_FR/champion.json").json()
        CHAMP_NAMES = {int(ch["key"]): ch["name"] for ch in data["data"].values()}
        CHAMP_IMAGES = {
            int(champion["key"]): champion["image"]["full"]
            for champion in data["data"].values()
            if champion.get("image", {}).get("full")
        }
        print(f"✅ {len(CHAMP_NAMES)} noms de champions chargés ({DD_VERSION})")
    except Exception as e:
        print(f"⚠️ Erreur Data Dragon : {e}")

load_champ_names()

def load_prefs(file_path):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                data.setdefault("favorites", {})
                data.setdefault("library", {})
                icon_prefs = data.setdefault("summoner_icon", {})
                icon_prefs.setdefault("default", None)
                icon_prefs.setdefault("champion_overrides", {})
                icon_prefs.setdefault("inventory", [])
                return data
        except Exception as e:
            print(f"Erreur lecture {file_path} : {e}")
            return {"favorites": {}, "library": {}, "summoner_icon": {"default": None, "champion_overrides": {}, "inventory": []}}
    print(f"Fichier {file_path} introuvable, template vide retourné")
    return {"favorites": {}, "library": {}, "summoner_icon": {"default": None, "champion_overrides": {}, "inventory": []}}

def save_prefs(data, file_path):
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"{file_path} sauvegardé")
    except Exception as e:
        print(f"Erreur sauvegarde {file_path} : {e}")

MAIN_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>LoL/TFT HUD</title>
<style>
body {background:#020617;color:white;font-family:Arial,sans-serif;margin:0;}
.header {text-align:center;padding:15px;}
h1 {margin:10px 0;font-size:2.4rem;}
.diff {font-size:28px;font-weight:bold;color:#facc15;margin:15px 0;}
.nav-buttons {margin:20px 0;}
.nav-btn {padding:12px 24px;margin:0 10px;font-size:1.2rem;border:none;border-radius:10px;cursor:pointer;background:#334155;color:white;}
.nav-btn.active {background:#1e40af;}
.nav-btn:hover {background:#475569;}
.container {display:flex;justify-content:space-between;padding:0 20px;gap:30px;width:100%;box-sizing:border-box;}
.team {width:48%;background:#0f172a;padding:18px;border-radius:14px;box-shadow:0 4px 15px rgba(0,0,0,0.5);}
.player {background:#1e293b;margin:12px 0;padding:14px;border-radius:10px;}
.gold {color:#facc15;font-weight:bold;font-size:1.15rem;}
.timer {color:#22c55e;font-weight:bold;}
.team-header {
    margin: 0 0 15px 0;
    font-size: 1.8rem;
    font-weight: bold;
    padding: 8px 0;
}
.align-right {text-align: right !important;}
.align-left {text-align: left !important;}
.gold-green {color: #22c55e !important;}
.gold-red {color: #ef4444 !important;}
#lol-settings, #tft-settings {display:none;padding:30px;background:#0f172a;border-radius:14px;margin:25px;}
#mastery-settings {display:none;padding:30px;background:#0f172a;border-radius:14px;margin:25px;}
.search {width:100%;padding:16px;margin-bottom:25px;background:#1e293b;border:none;border-radius:12px;color:white;font-size:1.15rem;box-sizing:border-box;}
#lol-prefs-list, #tft-prefs-list, #mastery-list {display:grid;grid-template-columns:repeat(auto-fill, minmax(300px, 1fr));gap:20px;}
.champ-card, .tft-card {background:#1e293b;border-radius:12px;overflow:hidden;box-shadow:0 4px 15px rgba(0,0,0,0.5);}
.mastery-card {background:#1e293b;border:1px solid #334155;border-radius:12px;padding:16px;box-shadow:0 4px 15px rgba(0,0,0,0.35);}
.mastery-card.close-to-level {border:2px solid #facc15;box-shadow:0 0 0 2px rgba(250,204,21,0.18);}
.mastery-card.max-level {border-color:#64748b;}
.mastery-card-header {display:flex;align-items:center;gap:14px;}
.mastery-card-header img {width:64px;height:64px;border:1px solid #475569;border-radius:10px;object-fit:cover;}
.mastery-card h3 {margin:0;color:#93c5fd;}
.mastery-summary {display:flex;align-items:center;justify-content:space-between;gap:12px;}
.mastery-title {display:flex;align-items:center;gap:12px;min-width:0;}
.mastery-title h3 {overflow-wrap:anywhere;}
.mastery-title.unknown-champion h3 {color:#cbd5e1;}
.mastery-missing-image {display:grid;place-items:center;width:64px;height:64px;flex-shrink:0;border:1px dashed #64748b;border-radius:10px;background:#0f172a;color:#94a3b8;font-size:1.6rem;}
.mastery-toggle {display:flex;align-items:center;gap:8px;flex-shrink:0;padding:8px 10px;border:1px solid #475569;border-radius:8px;background:#0f172a;color:#cbd5e1;cursor:pointer;}
.mastery-toggle:hover {background:#334155;color:white;}
.mastery-toggle:focus-visible {outline:2px solid #38bdf8;outline-offset:2px;}
.mastery-chevron {width:14px;height:14px;transition:transform .18s ease;}
.mastery-toggle[aria-expanded="true"] .mastery-chevron {transform:rotate(180deg);}
.mastery-details {margin-top:14px;padding-top:10px;border-top:1px solid #334155;}
.mastery-level {flex-shrink:0;padding:5px 9px;border-radius:999px;background:#1e3a8a;color:#bfdbfe;font-size:.9rem;font-weight:700;}
.mastery-card p {margin:8px 0;color:#e2e8f0;}
.mastery-badge {display:inline-block;margin-bottom:8px;padding:4px 9px;border-radius:999px;background:#713f12;color:#fde68a;font-size:.85rem;font-weight:700;}
.mastery-controls {display:flex;flex-wrap:wrap;gap:14px;align-items:end;margin:16px 0;}
.mastery-controls label {display:flex;flex-direction:column;gap:6px;color:#cbd5e1;}
.mastery-controls .mastery-checkbox-label {flex-direction:row;align-items:center;gap:8px;}
.mastery-controls select,.mastery-controls input {padding:10px;border:1px solid #334155;border-radius:8px;background:#020617;color:white;}
.mastery-controls input[type="checkbox"] {width:18px;height:18px;margin:0;padding:0;accent-color:#38bdf8;}
.mastery-controls button {padding:10px 16px;border:0;border-radius:8px;background:#2563eb;color:white;cursor:pointer;}
.mastery-controls .mastery-expand-button {background:#334155;}
.mastery-controls .mastery-expand-button:hover {background:#475569;}
.mastery-status {margin:12px 0;color:#cbd5e1;}
.card-header {background:#0f172a;padding:16px 20px;font-size:1.35rem;font-weight:bold;color:#60a5fa;border-bottom:1px solid #334155;}
.grid-container {padding:12px;display:grid;grid-template-columns:repeat(auto-fit, minmax(160px, 1fr));gap:12px;}
.item, .skin-item {display:flex;justify-content:space-between;align-items:center;background:#0f172a;padding:10px 14px;border-radius:8px;font-size:1.05rem;}
.item-name, .skin-name {flex:1;}
.heart {font-size:1.9rem;cursor:pointer;transition:all 0.2s;padding:4px 10px;}
.heart.red {color:#ef4444;}
.heart.gray {color:#64748b;}
.heart:hover {transform:scale(1.35);}
.icon-grid {display:grid;grid-template-columns:repeat(auto-fit, minmax(180px, 1fr));gap:18px;}
.icon-card {background:#1e293b;border-radius:14px;overflow:hidden;box-shadow:0 4px 18px rgba(0,0,0,0.5);padding:16px;display:flex;flex-direction:column;align-items:center;gap:10px;}
.icon-card img {width:80px;height:80px;border-radius:18px;object-fit:cover;border:1px solid #334155;background:#0f172a;}
.icon-card .item-name {font-size:1rem;font-weight:700;text-align:center;}
.icon-card .icon-actions {display:flex;flex-wrap:wrap;gap:10px;justify-content:center;width:100%;}
.icon-card button {padding:8px 12px;border:none;border-radius:10px;background:#2563eb;color:white;cursor:pointer;}
.icon-card button.secondary {background:#475569;}
.icon-card.selected {border:2px solid #38bdf8;box-shadow:0 0 0 2px rgba(56,213,248,0.2);}
.icon-card.selected img {border-color:#38bdf8;}
.selection-toolbar {display:flex;flex-wrap:wrap;gap:10px;align-items:center;justify-content:flex-start;margin-top:12px;}
.selection-toolbar .count {color:#a5f3fc;font-weight:700;}
.icon-override-form {display:flex;flex-wrap:wrap;gap:12px;margin-bottom:18px;}
.icon-override-form input, .icon-override-form select {padding:12px;border-radius:12px;border:1px solid #334155;background:#020617;color:white;flex:1;min-width:180px;}
.icon-override-form button {padding:12px 18px;border:none;border-radius:12px;background:#16a34a;color:white;cursor:pointer;}
.champ-suggestions {border:1px solid #334155;background:#0f172a;border-radius:12px;max-height:260px;overflow-y:auto;margin-top:8px;}
.champ-suggestion {padding:10px 12px;cursor:pointer;border-bottom:1px solid #334155;color:#e2e8f0;}
.champ-suggestion:hover, .champ-suggestion.selected {background:#1e293b;color:#ffffff;}
.selected-champ-box {padding:16px;border-radius:14px;background:#0f172a;min-height:180px;display:flex;flex-direction:column;justify-content:space-between;}
.selected-champ-box .meta {color:#cbd5e1;line-height:1.6;}
</style>
</head>
<body>
<div class="header">
    <h1>LoL/TFT HUD</h1>
    <div class="nav-buttons">
        <button class="nav-btn active" onclick="showSection('monitoring')">Monitoring Game</button>
        <button class="nav-btn" onclick="showSection('lol-settings')">LoL Skins</button>
        <button class="nav-btn" onclick="showSection('mastery-settings')">Maîtrise</button>
        <button class="nav-btn" onclick="showSection('tft-settings')">TFT Random</button>
    </div>
</div>

<div id="monitoring-view">
    <div class="diff" id="diff"></div>
    <div id="monitoring" class="container">
        <div id="blue" class="team"></div>
        <div id="red" class="team"></div>
    </div>
</div>

<div id="lol-settings">
    <h2>⚙️ LoL Skin Random Preferences</h2>
    <input type="text" id="lol-search" class="search" placeholder="🔎 Filtrer par champion..." onkeyup="filterLoL()">
    <div id="lol-prefs-list"></div>
</div>

<div id="mastery-settings">
    <h2>Maîtrise des champions</h2>
    <p>Maîtrises du compte connecté au client LoL. La liste est triée par XP restante; les champions proches du prochain niveau sont mis en évidence. Les IDs sans correspondance dans Data Dragon sont masqués par défaut.</p>
    <div class="mastery-controls">
        <label for="mastery-level-filter">Niveau de maîtrise
            <select id="mastery-level-filter" onchange="renderMastery()">
                <option value="">Tous les niveaux</option>
            </select>
        </label>
        <label class="mastery-checkbox-label" for="mastery-show-unknown">
            <input id="mastery-show-unknown" type="checkbox" onchange="renderMastery()">
            Afficher les IDs non reconnus
        </label>
        <label for="mastery-xp-threshold">Seuil de proximité (XP restantes)
            <input id="mastery-xp-threshold" type="number" min="0" step="100" value="1000" oninput="renderMastery()">
        </label>
        <button class="mastery-expand-button" type="button" onclick="setMasteryDetailsExpanded(true)">Tout développer</button>
        <button class="mastery-expand-button" type="button" onclick="setMasteryDetailsExpanded(false)">Tout réduire</button>
        <button onclick="loadMastery()">Actualiser</button>
    </div>
    <div id="mastery-status" class="mastery-status" role="status">Cliquez sur « Actualiser » pour charger les maîtrises.</div>
    <div id="mastery-list"></div>
</div>

<div id="tft-settings">
    <h2>⚙️ TFT Random Preferences</h2>
    <input type="text" id="tft-search" class="search" placeholder="🔎 Filtrer par catégorie..." onkeyup="filterTFT()">
    <div id="tft-prefs-list"></div>
</div>

<div id="icon-settings" style="display:none;padding:30px;background:#0f172a;border-radius:14px;margin:25px;">
    <h2>⚙️ Préférences d'icônes Invocateur</h2>
    <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:12px;align-items:center;">
        <input type="text" id="icon-search" class="search" placeholder="🔎 Filtrer par icône..." onkeyup="filterIcons()" style="flex:1;min-width:240px;" />
        <button class="nav-btn" style="margin:0;" onclick="loadIconPrefs()">🔄 Rafraîchir la liste</button>
        <button id="toggle-hidden-btn" class="nav-btn" style="margin:0;" onclick="toggleShowHiddenIcons()">Afficher les cachées</button>
    </div>
    <div class="selection-toolbar">
        <span class="count" id="selected-icon-count">0 sélectionnée</span>
        <button class="nav-btn" style="margin:0;" onclick="hideSelectedIcons()">Masquer la sélection</button>
        <button class="nav-btn" style="margin:0;" onclick="clearIconSelection()">Effacer la sélection</button>
    </div>
    <div class="icon-override-form">
        <div style="flex:1;min-width:260px;">
            <input type="text" id="champ-search" class="search" placeholder="🔎 Rechercher un champion..." oninput="updateChampionSuggestions()" autocomplete="off" />
            <div id="champ-suggestions" class="champ-suggestions"></div>
        </div>
        <div style="flex:1;min-width:260px;">
            <div id="selected-champ-card" class="selected-champ-box">
                <div style="font-weight:700;color:#60a5fa;">Aucun champion sélectionné</div>
                <div class="meta">Recherchez un champion ci-dessus pour l'associer à une icône. Cliquez ensuite sur une icône dans la liste.</div>
            </div>
        </div>
    </div>
    <div id="icon-prefs-list"></div>
    <div id="icon-overrides-list" style="margin-top:24px;"></div>
</div>

<script>
// Navigation
function showSection(sectionId) {
    document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');

    document.getElementById('monitoring-view').style.display = sectionId === 'monitoring' ? 'block' : 'none';
    document.getElementById('lol-settings').style.display = sectionId === 'lol-settings' ? 'block' : 'none';
    document.getElementById('mastery-settings').style.display = sectionId === 'mastery-settings' ? 'block' : 'none';
    document.getElementById('tft-settings').style.display = sectionId === 'tft-settings' ? 'block' : 'none';
    document.getElementById('icon-settings').style.display = sectionId === 'icon-settings' ? 'block' : 'none';

    if (sectionId === 'lol-settings') loadLoLPrefs();
    if (sectionId === 'mastery-settings') loadMastery();
    if (sectionId === 'tft-settings') loadTFTPrefs();
    if (sectionId === 'icon-settings') loadIconPrefs();
}

let masteryChampions = [];
let visibleMasteryChampions = [];
const expandedMasteryChampions = new Set();
let masteryLoaded = false;

function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, char => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
    })[char]);
}

async function loadMastery() {
    const status = document.getElementById("mastery-status");
    const list = document.getElementById("mastery-list");
    masteryLoaded = false;
    status.textContent = "Chargement des maîtrises...";
    list.innerHTML = "";

    try {
        const response = await fetch('/mastery');
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
        if (!Array.isArray(data.champions)) throw new Error("Format de réponse des maîtrises invalide.");

        masteryChampions = data.champions;
        masteryLoaded = true;

        const levelFilter = document.getElementById("mastery-level-filter");
        const previousLevel = levelFilter.value;
        const levels = [...new Set(masteryChampions.map(champion => champion.championLevel))].sort((a, b) => a - b);
        levelFilter.innerHTML = '<option value="">Tous les niveaux</option>';
        levels.forEach(level => {
            const option = document.createElement("option");
            option.value = String(level);
            option.textContent = `Niveau ${level}`;
            levelFilter.appendChild(option);
        });
        if (levels.includes(Number(previousLevel))) levelFilter.value = previousLevel;

        status.textContent = `${masteryChampions.length} maîtrises chargées.`;
        renderMastery();
    } catch (error) {
        masteryLoaded = false;
        status.textContent = `Impossible de charger les maîtrises : ${error.message}`;
        list.innerHTML = "";
    }
}

function renderMastery() {
    if (!masteryLoaded) return;

    const levelFilter = document.getElementById("mastery-level-filter").value;
    const showUnknown = document.getElementById("mastery-show-unknown").checked;
    const thresholdInput = document.getElementById("mastery-xp-threshold");
    const threshold = Math.max(0, Number(thresholdInput.value) || 0);
    const hiddenUnknownCount = masteryChampions.filter(champion => !champion.isRecognized).length;
    const champions = masteryChampions
        .filter(champion => showUnknown || champion.isRecognized)
        .filter(champion => !levelFilter || champion.championLevel === Number(levelFilter))
        .sort((a, b) => {
            if (a.hasNextLevel !== b.hasNextLevel) return a.hasNextLevel ? -1 : 1;
            if (!a.hasNextLevel) return a.name.localeCompare(b.name);
            return a.xpRemaining - b.xpRemaining || a.name.localeCompare(b.name);
        });
    visibleMasteryChampions = champions;

    const status = document.getElementById("mastery-status");
    const list = document.getElementById("mastery-list");
    if (champions.length === 0) {
        status.textContent = showUnknown
            ? "Aucune maîtrise pour ce filtre."
            : `Aucune maîtrise pour ce filtre.${hiddenUnknownCount ? ` ${hiddenUnknownCount} ID(s) non reconnu(s) sont masqué(s).` : ""}`;
        list.innerHTML = "";
        return;
    }

    const hiddenUnknownMessage = !showUnknown && hiddenUnknownCount
        ? ` ${hiddenUnknownCount} ID(s) non reconnu(s) masqué(s).`
        : "";
    status.textContent = `${champions.length} entrée(s) affichée(s).${hiddenUnknownMessage} Le cadre jaune signale ${threshold} XP ou moins avant le prochain niveau.`;
    list.innerHTML = champions.map(champion => {
        const isClose = champion.hasNextLevel && champion.xpRemaining <= threshold;
        const isExpanded = expandedMasteryChampions.has(String(champion.championId));
        const classes = ["mastery-card"];
        if (isClose) classes.push("close-to-level");
        if (!champion.hasNextLevel) classes.push("max-level");

        const progress = champion.hasNextLevel
            ? `<p>XP restantes : <strong>${champion.xpRemaining.toLocaleString('fr-FR')} XP</strong></p>`
            : '<p>Niveau maximal atteint · aucun niveau suivant</p>';
        const marks = champion.markRequiredForNextLevel > 0 || champion.tokensEarned > 0
            ? `<p>Jetons / marques de maîtrise : ${champion.tokensEarned} disponible(s) / ${champion.markRequiredForNextLevel} requis(s)</p>`
            : "";
        const badge = isClose ? `<span class="mastery-badge">Proche du niveau suivant</span>` : "";
        const detailsId = `mastery-details-${champion.championId}`;

        const imageUrl = champion.image ? escapeHtml(champion.image) : "";
        const championImage = imageUrl
            ? `<img src="${imageUrl}" alt="${escapeHtml(champion.name)}" loading="lazy">`
            : `<span class="mastery-missing-image" aria-hidden="true">?</span>`;
        const titleClasses = champion.isRecognized ? "mastery-title" : "mastery-title unknown-champion";

        return `<article class="${classes.join(' ')}">
            ${badge}
            <div class="mastery-summary">
                <div class="${titleClasses}">
                    ${championImage}
                    <h3>${escapeHtml(champion.name)}</h3>
                </div>
                <span class="mastery-level">Niveau ${champion.championLevel}</span>
                <button class="mastery-toggle" type="button" aria-expanded="${isExpanded}" aria-controls="${detailsId}" onclick="toggleMasteryDetails(${champion.championId})">
                    <svg class="mastery-chevron" viewBox="0 0 16 16" aria-hidden="true"><path d="m3.5 6 4.5 4 4.5-4" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8"/></svg>
                    <span>${isExpanded ? "Réduire" : "Détails"}</span>
                </button>
            </div>
            <div class="mastery-details" id="${detailsId}" ${isExpanded ? "" : "hidden"}>
                ${progress}
                ${marks}
                <p>Points de maîtrise : ${champion.championPoints.toLocaleString('fr-FR')}</p>
            </div>
        </article>`;
    }).join("");
}

function toggleMasteryDetails(championId) {
    const key = String(championId);
    if (expandedMasteryChampions.has(key)) {
        expandedMasteryChampions.delete(key);
    } else {
        expandedMasteryChampions.add(key);
    }
    renderMastery();
}

function setMasteryDetailsExpanded(expanded) {
    visibleMasteryChampions.forEach(champion => {
        const key = String(champion.championId);
        if (expanded) {
            expandedMasteryChampions.add(key);
        } else {
            expandedMasteryChampions.delete(key);
        }
    });
    renderMastery();
}

let timers = {};
const SPELL_COOLDOWNS = {
    "Flash":300,"Saut éclair":300,"Ignite":180,"Embrasement":180,
    "Teleport":360,"Téléportation":360,"Heal":240,"Soins":240,
    "Ghost":210,"Fantôme":210,"Smite":90,"Châtiment":90
};

function startTimer(player, spell){
    const key = player + "_" + spell;
    const cd = SPELL_COOLDOWNS[spell] || 180;
    timers[key] = Date.now() + cd * 1000;
}

function getRemaining(player, spell){
    const key = player + "_" + spell;
    if (!timers[key]) return "";
    let rem = Math.floor((timers[key] - Date.now()) / 1000);
    if (rem <= 0) { delete timers[key]; return "READY"; }
    return rem + "s";
}

async function updateHUD(){
    try {
        const res = await fetch('/data');
        const data = await res.json();
        document.getElementById("diff").innerText = `Gold Diff: ${data.diff > 0 ? '+' : ''}${data.diff}`;
        document.getElementById("diff").style.color = data.diff > 0 ? "#22c55e" : data.diff < 0 ? "#ef4444" : "#ffffff";

        function render(id, team, total){
            // Calcul de la couleur
            const diff = document.getElementById("diff").innerText.match(/(-?\\d+)/)?.[0] || "0";
            const diffNum = parseInt(diff);

            let colorClass = "";
            if (id === "blue") {
                colorClass = diffNum > 0 ? "gold-green" : diffNum < 0 ? "gold-red" : "";
            } else { // red
                colorClass = diffNum < 0 ? "gold-green" : diffNum > 0 ? "gold-red" : "";
            }

            // Alignement : BLUE à droite, RED à gauche
            let alignClass = id === "blue" ? "align-right" : "align-left";

            // Texte inversé : BLUE (total) vs (total) RED
            let texttotal;
            if (id === "blue") {
                texttotal = `${id.toUpperCase()} (${total})`;
            } else {
                texttotal = `(${total}) ${id.toUpperCase()}`;
            }

            let html = `<h2 class="team-header ${colorClass} ${alignClass}">${texttotal}</h2>`;
            team.forEach(p => {
                let spellsHtml = p.spells.map(sp => {
                    const rem = getRemaining(p.name, sp);
                    return `<div>${sp} <span class="timer">${rem}</span> <button onclick="startTimer('${p.name}','${sp}')">Start</button></div>`;
                }).join('');
                html += `
                <div class="player">
                    <div>${p.name}</div>
                    <div class="gold">${p.gold} gold</div>
                    ${spellsHtml}
                </div>`;
            });
            document.getElementById(id).innerHTML = html;
        }
        render("blue", data.blue, data.blue_total);
        render("red", data.red, data.red_total);
    } catch(e) {}
}

setInterval(updateHUD, 1500);
updateHUD();

// LoL Skins (inchangé)
let lolChampions = [];
async function loadLoLPrefs(){
    document.getElementById("lol-prefs-list").innerHTML = "<p>Chargement LoL...</p>";
    try {
        const res = await fetch('/prefs?type=lol');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        console.log("Données LoL reçues :", data);

        const prefs = data.prefs || {};
        const champNames = data.champ_names || {};

        lolChampions = [];
        const library = prefs.library || {};
        const favorites = prefs.favorites || {};

        for (const [champIdStr, skins] of Object.entries(library)) {
            const champIdNum = parseInt(champIdStr);
            const champName = champNames[champIdNum] || `Champion ${champIdStr}`;

            const ownedSkins = skins.filter(s => s.owned === true);
            const favList = (favorites[champIdStr] || []).map(Number);

            lolChampions.push({
                id: champIdStr,
                name: champName,
                skins: ownedSkins,
                favs: new Set(favList)
            });
        }

        renderLoL();
    } catch (e) {
        console.error("Erreur load LoL :", e);
        document.getElementById("lol-prefs-list").innerHTML = `<p style="color:#ef4444;">Erreur LoL : ${e.message}</p>`;
    }
}

function renderLoL(filtered = null){
    let html = "";
    const list = filtered || lolChampions;

    if (list.length === 0) {
        html = "<p>Aucun champion possédé.</p>";
    } else {
        list.forEach(champ => {
            let skinsHtml = "";
            champ.skins.forEach(skin => {
                const isFav = champ.favs.has(skin.id);
                skinsHtml += `
                <div class="skin-item">
                    <span class="skin-name">${skin.name}</span>
                    <span class="heart ${isFav ? 'red' : 'gray'}" onclick="toggleLoLFavorite('${champ.id}', ${skin.id}, this)">
                        ${isFav ? '❤️' : '♡'}
                    </span>
                </div>`;
            });

            html += `
            <div class="champ-card">
                <div class="card-header">${champ.name} (ID ${champ.id})</div>
                <div class="grid-container">
                    ${skinsHtml || '<div style="padding:20px;text-align:center;color:#64748b;">Aucun skin possédé</div>'}
                </div>
            </div>`;
        });
    }

    document.getElementById("lol-prefs-list").innerHTML = html;
}

function filterLoL(){
    const term = document.getElementById("lol-search").value.toLowerCase().trim();
    if (!term) return renderLoL();
    const filtered = lolChampions.filter(c => c.name.toLowerCase().includes(term) || String(c.id).includes(term));
    renderLoL(filtered);
}

async function toggleLoLFavorite(champId, skinId, heart){
    const isFav = heart.classList.contains("red");
    try {
        const res = await fetch('/toggle_favorite', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({champId, skinId, add: !isFav})
        });
        if (!res.ok) throw new Error(await res.text());
        heart.classList.toggle("red", !isFav);
        heart.classList.toggle("gray", isFav);
        heart.textContent = !isFav ? '❤️' : '♡';
    } catch (e) {
        console.error("Erreur toggle LoL :", e);
        alert("Erreur sauvegarde LoL");
    }
}

// TFT Random (inchangé)
let tftCategories = [];
async function loadTFTPrefs(){
    document.getElementById("tft-prefs-list").innerHTML = "<p>Chargement TFT...</p>";
    try {
        const res = await fetch('/prefs?type=tft');
        console.log("Réponse HTTP TFT :", res.status);
        if (!res.ok) {
            const errText = await res.text();
            throw new Error(`HTTP ${res.status} - ${errText}`);
        }

        const data = await res.json();
        console.log("Données TFT reçues :", data);

        const prefs = data.prefs || {};
        const library = prefs.library || {};
        const favorites = prefs.favorites || {};

        tftCategories = [];
        const categories = [
            {key: "companions", name: "Companions (Tacticiens)"},
            {key: "map_skins", name: "Map Skins (Arènes)"},
            {key: "damage_skins", name: "Damage Skins"},
            {key: "zoom_skins", name: "Zoom Skins"}
        ];

        categories.forEach(c => {
            const items = (library[c.key] || []).filter(i => i.owned === true);
            const favList = favorites[c.key] || [];

            tftCategories.push({
                category: c.key,
                displayName: c.name,
                items: items,
                favs: new Set(favList)
            });
        });

        renderTFT();
    } catch (e) {
        console.error("Erreur load TFT :", e);
        document.getElementById("tft-prefs-list").innerHTML = `
            <p style="color:#ef4444;">Erreur chargement TFT : ${e.message}</p>
            <p>Vérifie que tft_randomizer.py a bien généré tft_prefs.json</p>
        `;
    }
}

function renderTFT(filtered = null){
    let html = "";
    const list = filtered || tftCategories;

    if (list.length === 0) {
        html = "<p>Aucune catégorie TFT détectée.</p>";
    } else {
        list.forEach(cat => {
            let itemsHtml = "";
            cat.items.forEach(item => {
                const isFav = cat.favs.has(item.id);
                itemsHtml += `
                <div class="item">
                    <span class="item-name">${item.name}</span>
                    <span class="heart ${isFav ? 'red' : 'gray'}" onclick="toggleTFTFavorite('${cat.category}', '${item.id}', this)">
                        ${isFav ? '❤️' : '♡'}
                    </span>
                </div>`;
            });

            html += `
            <div class="tft-card">
                <div class="card-header">${cat.displayName}</div>
                <div class="grid-container">
                    ${itemsHtml || '<div style="padding:20px;text-align:center;color:#64748b;">Aucun possédé</div>'}
                </div>
            </div>`;
        });
    }

    document.getElementById("tft-prefs-list").innerHTML = html;
}

function filterTFT(){
    const term = document.getElementById("tft-search").value.toLowerCase().trim();
    if (!term) return renderTFT();
    const filtered = tftCategories.filter(c => c.displayName.toLowerCase().includes(term));
    renderTFT(filtered);
}

let iconInventory = [];
let iconOverrides = {};
let iconDefaultId = null;
let ownedChampions = [];
let selectedChampionId = null;
let iconChampNames = {};
let DD_VERSION = null;
let showHiddenIcons = false;
let currentIconList = [];
let selectedIconIds = [];
let lastSelectedIconIndex = null;

async function loadIconPrefs(){
    document.getElementById("icon-prefs-list").innerHTML = "<p>Chargement Icônes...</p>";
    try {
        const res = await fetch('/prefs?type=icon');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        const prefs = data.prefs || {};
        const iconPrefs = prefs.summoner_icon || {};

        iconInventory = iconPrefs.inventory || [];
        iconOverrides = iconPrefs.champion_overrides || {};
        iconDefaultId = iconPrefs.default || null;
        iconChampNames = data.champ_names || {};
        DD_VERSION = data.dd_version || DD_VERSION;

        ownedChampions = Object.keys(prefs.library || {}).map(champId => {
            return {
                id: champId,
                name: iconChampNames[champId] || `Champion ${champId}`
            };
        }).sort((a, b) => a.name.localeCompare(b.name, 'fr'));

        if (selectedChampionId && !ownedChampions.some(ch => ch.id === selectedChampionId)) {
            selectedChampionId = null;
        }

        const toggleButton = document.getElementById("toggle-hidden-btn");
        if (toggleButton) {
            toggleButton.textContent = showHiddenIcons ? "Masquer les cachées" : "Afficher les cachées";
        }

        renderSelectedChampion();
        renderIcons();
        updateSelectedCount();
        renderIconOverrides();
    } catch (e) {
        console.error("Erreur chargement Icônes :", e);
        document.getElementById("icon-prefs-list").innerHTML = `<p style="color:#ef4444;">Erreur chargement Icônes : ${e.message}</p>`;
    }
}

function renderSelectedChampion(){
    const card = document.getElementById("selected-champ-card");
    if (!selectedChampionId) {
        card.innerHTML = `
            <div style="font-weight:700;color:#60a5fa;">Aucun champion sélectionné</div>
            <div class="meta">Recherchez un champion ci-dessus pour l'associer à une icône dans la liste.</div>`;
        return;
    }

    const champ = ownedChampions.find(c => c.id === selectedChampionId) || {id:selectedChampionId, name:`Champion ${selectedChampionId}`};
    const overrideId = iconOverrides[selectedChampionId];
    const overrideIcon = overrideId ? iconInventory.find(i => i.id === overrideId) : null;
    const overrideLabel = overrideId ? `Icone dédiée : IC${overrideId}` : 'Pas d’icône dédiée définie';
    const defaultLabel = iconDefaultId ? `Valeur par défaut : IC${iconDefaultId}` : 'Aucune icône par défaut définie';
    const overrideImage = overrideIcon ? `<img src="${overrideIcon.image || `https://ddragon.leagueoflegends.com/cdn/${DD_VERSION}/img/profileicon/${overrideId}.png`}" alt="IC${overrideId}" style="width:64px;height:64px;border-radius:14px;border:1px solid #334155;margin-top:10px;" />` : '';

    card.innerHTML = `
        <div style="font-weight:700;color:#60a5fa;">${champ.name}</div>
        <div class="meta">ID ${champ.id}</div>
        <div class="meta">${overrideLabel}</div>
        ${overrideImage}
        <div class="meta">${defaultLabel}</div>
        <div class="meta" style="margin-top:10px;">Cliquez sur une icône pour l’affecter à ce champion. Le bouton « Définir par défaut » reste disponible pour l’ensemble du compte.</div>
        <button onclick="clearChampionSelection()" class="secondary" style="margin-top:12px;">Effacer la sélection</button>`;
}

function updateChampionSuggestions(){
    const query = document.getElementById("champ-search").value.toLowerCase().trim();
    const suggestions = ownedChampions.filter(champ => {
        return champ.name.toLowerCase().includes(query) || champ.id.includes(query);
    }).slice(0, 30);

    const html = suggestions.length ? suggestions.map(champ => {
        return `<div class="champ-suggestion" onclick="selectChampion('${champ.id}')">${champ.name} (ID ${champ.id})</div>`;
    }).join('') : `<div class="champ-suggestion">Aucun champion trouvé</div>`;

    document.getElementById("champ-suggestions").innerHTML = html;
}

function selectChampion(champId){
    selectedChampionId = champId;
    const champ = ownedChampions.find(c => c.id === champId);
    document.getElementById("champ-search").value = champ ? champ.name : champId;
    document.getElementById("champ-suggestions").innerHTML = "";
    renderSelectedChampion();
}

function clearChampionSelection(){
    selectedChampionId = null;
    document.getElementById("champ-search").value = "";
    document.getElementById("champ-suggestions").innerHTML = "";
    renderSelectedChampion();
}

function renderIcons(filtered = null){
    const list = (filtered || iconInventory).filter(icon => showHiddenIcons || icon.owned);
    let html = "";

    if (list.length === 0) {
        html = "<p>Aucune icône détectée.</p>";
    } else {
        currentIconList = list;
        html = `<div class="icon-grid">`;
        list.forEach((icon, index) => {
            const isDefault = String(icon.id) === String(iconDefaultId);
            const isSelectedOverride = selectedChampionId && String(iconOverrides[selectedChampionId]) === String(icon.id);
            const isSelected = selectedIconIds.includes(icon.id) || isSelectedOverride;
            const imageUrl = icon.image || `https://ddragon.leagueoflegends.com/cdn/${DD_VERSION}/img/profileicon/${icon.id}.png`;
            const hiddenLabel = icon.owned ? "" : `<div style="color:#f97316;font-weight:700;margin-top:8px;">Cachée</div>`;
            html += `
                <div class="icon-card${isSelected ? ' selected' : ''}" onclick="toggleIconSelection(event, ${icon.id}, ${index})">
                    <img src="${imageUrl}" alt="Icon ${icon.id}" />
                    <div class="item-name">IC${icon.id}</div>
                    ${hiddenLabel}
                    <div class="icon-actions">
                        <button onclick="event.stopPropagation(); setDefaultIcon(${icon.id})" class="${isDefault ? 'secondary' : ''}">${isDefault ? 'Défaut actif' : 'Définir par défaut'}</button>
                        <button onclick="event.stopPropagation(); assignIconToSelectedChampion(${icon.id})" class="${isSelectedOverride ? 'secondary' : ''}">${isSelectedOverride ? 'Affecté au champion' : 'Associer'}</button>
                        <button onclick="event.stopPropagation(); setIconOwned(${icon.id}, ${icon.owned ? 'false' : 'true'})" class="secondary">${icon.owned ? '🗑️ Masquer' : '↩️ Restaurer'}</button>
                    </div>
                </div>`;
        });
        html += `</div>`;
    }

    document.getElementById("icon-prefs-list").innerHTML = html;
}

function toggleIconSelection(event, iconId, index){
    const isButton = event.target.closest('button');
    if (isButton) return;

    if (event.shiftKey && lastSelectedIconIndex !== null) {
        applySelectionRange(lastSelectedIconIndex, index);
    } else if (event.ctrlKey || event.metaKey) {
        if (selectedIconIds.includes(iconId)) {
            selectedIconIds = selectedIconIds.filter(id => id !== iconId);
        } else {
            selectedIconIds.push(iconId);
            lastSelectedIconIndex = index;
        }
    } else {
        if (selectedIconIds.length === 1 && selectedIconIds[0] === iconId) {
            selectedIconIds = [];
            lastSelectedIconIndex = null;
        } else {
            selectedIconIds = [iconId];
            lastSelectedIconIndex = index;
        }
    }
    renderIcons(currentIconList);
    updateSelectedCount();
}

function applySelectionRange(fromIndex, toIndex){
    const start = Math.min(fromIndex, toIndex);
    const end = Math.max(fromIndex, toIndex);
    const rangeIds = currentIconList.slice(start, end + 1).map(icon => icon.id);
    const uniqueIds = new Set([...selectedIconIds, ...rangeIds]);
    selectedIconIds = Array.from(uniqueIds);
    lastSelectedIconIndex = toIndex;
}

function updateSelectedCount(){
    const count = selectedIconIds.length;
    const label = document.getElementById('selected-icon-count');
    if (label) {
        label.textContent = `${count} icône${count > 1 ? 's' : ''} sélectionnée${count > 1 ? 's' : ''}`;
    }
}

function clearIconSelection(){
    selectedIconIds = [];
    lastSelectedIconIndex = null;
    renderIcons(currentIconList);
    updateSelectedCount();
}

async function hideSelectedIcons(){
    if (!selectedIconIds.length) {
        return alert('Aucune icône sélectionnée.');
    }
    if (!confirm(`Masquer ${selectedIconIds.length} icône${selectedIconIds.length > 1 ? 's' : ''} ?`)) {
        return;
    }
    try {
        const res = await fetch('/set_icon_owned_bulk', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({iconIds: selectedIconIds, owned: false})
        });
        if (!res.ok) throw new Error('Échec mise à jour icônes');
        await res.json();
        clearIconSelection();
        await loadIconPrefs();
    } catch (e) {
        console.error('Erreur masquage icônes sélectionnées :', e);
        alert('Impossible de masquer les icônes sélectionnées');
    }
}

function filterIcons(){
    const term = document.getElementById("icon-search").value.toLowerCase().trim();
    if (!term) return renderIcons();
    const filtered = iconInventory.filter(icon => (icon.name.toLowerCase().includes(term) || String(icon.id).includes(term)) && (showHiddenIcons || icon.owned));
    renderIcons(filtered);
}

function toggleShowHiddenIcons(){
    showHiddenIcons = !showHiddenIcons;
    const toggleButton = document.getElementById("toggle-hidden-btn");
    if (toggleButton) {
        toggleButton.textContent = showHiddenIcons ? "Masquer les cachées" : "Afficher les cachées";
    }
    renderIcons();
}

function setIconOwned(iconId, owned){
    fetch('/set_icon_owned', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({iconId, owned})
    }).then(res => {
        if (!res.ok) throw new Error('Erreur mise à jour icône');
        return res.json();
    }).then(() => loadIconPrefs()).catch(e => {
        console.error('Erreur mise à jour ownership icône :', e);
        alert('Impossible de mettre à jour l’icône');
    });
}

function assignIconToSelectedChampion(iconId){
    if (!selectedChampionId) {
        return alert('Veuillez sélectionner d’abord un champion pour associer cette icône.');
    }
    saveIconOverride(selectedChampionId, iconId);
}

async function saveIconOverride(champId, iconId){
    try {
        const res = await fetch('/set_icon_override', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({champId, iconId})
        });
        if (!res.ok) throw new Error(await res.text());
        await loadIconPrefs();
    } catch (e) {
        console.error("Erreur sauvegarde override :", e);
        alert("Erreur sauvegarde override : " + e.message);
    }
}

async function setDefaultIcon(iconId){
    try {
        const res = await fetch('/set_icon_default', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({iconId})
        });
        if (!res.ok) throw new Error(await res.text());
        await loadIconPrefs();
    } catch (e) {
        console.error("Erreur définition icône par défaut :", e);
        alert("Erreur définition icône par défaut : " + e.message);
    }
}

async function removeIconOverride(champId){
    try {
        const res = await fetch('/remove_icon_override', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({champId})
        });
        if (!res.ok) throw new Error(await res.text());
        await loadIconPrefs();
    } catch (e) {
        console.error("Erreur suppression override :", e);
        alert("Erreur suppression override : " + e.message);
    }
}

function renderIconOverrides(){
    let html = `<div class="card-header">Affectations d'icônes par champion</div>`;
    const entries = Object.entries(iconOverrides || {});

    if (entries.length === 0) {
        html += '<div style="padding:18px;color:#94a3b8;">Aucune affectation de champion définie.</div>';
    } else {
        html += '<div class="grid-container">';
        entries.forEach(([champId, iconId]) => {
            const champName = iconChampNames[champId] || `Champion ${champId}`;
            const icon = iconInventory.find(i => i.id === iconId) || {};
            const imageUrl = icon.image || `https://ddragon.leagueoflegends.com/cdn/${DD_VERSION}/img/profileicon/${iconId}.png`;
            html += `
                <div class="item" style="align-items:center;gap:12px;">
                    <img src="${imageUrl}" alt="Icon ${iconId}" style="width:48px;height:48px;border-radius:12px;object-fit:cover;border:1px solid #334155;background:#0f172a;" />
                    <div class="item-name">${champName} → IC${iconId}</div>
                    <span class="heart secondary" onclick="removeIconOverride('${champId}')">❌</span>
                </div>`;
        });
        html += '</div>';
    }

    document.getElementById("icon-overrides-list").innerHTML = html;
}

async function toggleTFTFavorite(category, itemId, heart){
    const isFav = heart.classList.contains("red");
    try {
        const res = await fetch('/toggle_tft_favorite', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({category, itemId, add: !isFav})
        });
        if (!res.ok) {
            const err = await res.text();
            throw new Error(err);
        }
        heart.classList.toggle("red", !isFav);
        heart.classList.toggle("gray", isFav);
        heart.textContent = !isFav ? '❤️' : '♡';
    } catch (e) {
        console.error("Erreur toggle TFT :", e);
        alert("Erreur sauvegarde TFT : " + e.message);
    }
}
</script>
</body>
</html>
"""

# =========================================================
# ROUTES
# =========================================================
def get_game_data():
    try:
        r = requests.get("https://127.0.0.1:2999/liveclientdata/allgamedata", verify=False, timeout=3)
        data = r.json()

        active_name = data["activePlayer"]["summonerName"]
        active_gold = data["activePlayer"]["currentGold"]

        blue = []; red = []; bt = rt = 0

        for p in data["allPlayers"]:
            name = p["summonerName"]
            items_value = sum(it["price"] * it["count"] for it in p["items"])
            gold = items_value + active_gold if name == active_name else items_value

            spells = []
            ss = p.get("summonerSpells", {})
            for k in ["summonerSpellOne", "summonerSpellTwo"]:
                if k in ss:
                    spells.append(ss[k].get("displayName", "?"))

            player = {"name": name, "gold": int(gold), "spells": spells}

            if p["team"] == "ORDER":
                blue.append(player); bt += gold
            else:
                red.append(player); rt += gold

        return {
            "blue": blue, "red": red,
            "blue_total": int(bt), "red_total": int(rt),
            "diff": int(bt - rt)
        }
    except:
        return {"blue":[],"red":[],"blue_total":0,"red_total":0,"diff":0}

@app.route("/")
def index():
    return render_template_string(MAIN_HTML)

@app.route("/data")
def data():
    return jsonify(get_game_data())

@app.route("/mastery")
def mastery():
    lock_path = next((path for path in LCU_LOCKFILE_CANDIDATES if os.path.isfile(path)), None)
    if not lock_path:
        return jsonify({"error": "Client LoL introuvable. Ouvre le client et connecte-toi pour charger les maîtrises."}), 503

    try:
        with open(lock_path, "r", encoding="utf-8") as lockfile:
            parts = lockfile.read().strip().split(":")
    except OSError:
        return jsonify({"error": "Impossible de lire le fichier lockfile du client LoL."}), 503

    if len(parts) < 5 or parts[4] not in ("http", "https"):
        return jsonify({"error": "Le fichier lockfile du client LoL est invalide."}), 503

    try:
        port = int(parts[2])
    except ValueError:
        return jsonify({"error": "Le port du client LoL dans le lockfile est invalide."}), 503
    if not 1 <= port <= 65535:
        return jsonify({"error": "Le port du client LoL dans le lockfile est invalide."}), 503

    auth_raw = f"riot:{parts[3]}"
    auth_encoded = base64.b64encode(auth_raw.encode("utf-8")).decode("ascii")
    headers = {
        "Authorization": f"Basic {auth_encoded}",
        "User-Agent": "LeagueOfLegendsClient",
        "Accept": "application/json",
    }

    try:
        response = requests.get(
            f"{parts[4]}://127.0.0.1:{port}/lol-champion-mastery/v1/local-player/champion-mastery",
            headers=headers,
            verify=False,
            timeout=5,
        )
    except requests.RequestException:
        return jsonify({"error": "Impossible de joindre le client LoL. Vérifie qu'il est ouvert et connecté."}), 503

    if response.status_code != 200:
        return jsonify({"error": f"Le client LoL a refusé la lecture des maîtrises (HTTP {response.status_code})."}), 502

    try:
        mastery_data = response.json()
    except ValueError:
        return jsonify({"error": "Le client LoL a renvoyé des données de maîtrise invalides."}), 502

    if not isinstance(mastery_data, list):
        return jsonify({"error": "Le format des données de maîtrise renvoyées par le client est invalide."}), 502

    champions = []
    required_fields = (
        "championId",
        "championLevel",
        "championPoints",
        "championPointsUntilNextLevel",
        "markRequiredForNextLevel",
        "tokensEarned",
    )
    for mastery_data_item in mastery_data:
        if not isinstance(mastery_data_item, dict) or any(
            not isinstance(mastery_data_item.get(field), int) or isinstance(mastery_data_item.get(field), bool)
            for field in required_fields
        ):
            return jsonify({"error": "Une entrée de maîtrise renvoyée par le client est invalide."}), 502

        champion_id = mastery_data_item["championId"]
        xp_until_next_level = mastery_data_item["championPointsUntilNextLevel"]
        marks_required = max(0, mastery_data_item["markRequiredForNextLevel"])
        tokens_earned = max(0, mastery_data_item["tokensEarned"])
        has_next_level = xp_until_next_level > 0 or marks_required > 0

        champions.append({
            "championId": champion_id,
            "name": CHAMP_NAMES.get(champion_id, f"ID LCU non reconnu ({champion_id})"),
            "isRecognized": champion_id in CHAMP_NAMES,
            "image": f"https://ddragon.leagueoflegends.com/cdn/{DD_VERSION}/img/champion/{CHAMP_IMAGES[champion_id]}" if champion_id in CHAMP_IMAGES else None,
            "championLevel": mastery_data_item["championLevel"],
            "championPoints": mastery_data_item["championPoints"],
            "xpRemaining": max(0, xp_until_next_level) if has_next_level else None,
            "hasNextLevel": has_next_level,
            "markRequiredForNextLevel": marks_required,
            "tokensEarned": tokens_earned,
        })

    return jsonify({"champions": champions})

@app.route("/prefs")
def prefs():
    prefs_type = request.args.get('type', 'lol')

    try:
        if prefs_type == 'tft':
            prefs_data = load_prefs(TFT_PREFS_FILE)
            return jsonify({"prefs": prefs_data})
        elif prefs_type == 'icon':
            prefs_data = load_prefs(LOL_PREFS_FILE)
            return jsonify({
                "prefs": prefs_data,
                "champ_names": CHAMP_NAMES,
                "dd_version": DD_VERSION
            })
        else:
            prefs_data = load_prefs(LOL_PREFS_FILE)
            return jsonify({
                "prefs": prefs_data,
                "champ_names": CHAMP_NAMES
            })
    except Exception as e:
        print(f"Erreur route /prefs ({prefs_type}): {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/set_icon_default", methods=["POST"])
def set_icon_default():
    data = request.get_json()
    icon_id = int(data.get("iconId", 0))
    prefs = load_prefs(LOL_PREFS_FILE)
    icon_prefs = prefs.setdefault("summoner_icon", {})
    icon_prefs.setdefault("champion_overrides", {})
    icon_prefs.setdefault("inventory", [])
    icon_prefs["default"] = icon_id
    save_prefs(prefs, LOL_PREFS_FILE)
    return jsonify({"status": "ok"})

@app.route("/set_icon_override", methods=["POST"])
def set_icon_override():
    data = request.get_json()
    champ_id = str(data.get("champId", ""))
    icon_id = int(data.get("iconId", 0))
    prefs = load_prefs(LOL_PREFS_FILE)
    icon_prefs = prefs.setdefault("summoner_icon", {})
    overrides = icon_prefs.setdefault("champion_overrides", {})
    overrides[champ_id] = icon_id
    save_prefs(prefs, LOL_PREFS_FILE)
    return jsonify({"status": "ok"})

@app.route("/set_icon_owned", methods=["POST"])
def set_icon_owned():
    data = request.get_json()
    icon_id = int(data.get("iconId", 0))
    owned = bool(data.get("owned", True))
    prefs = load_prefs(LOL_PREFS_FILE)
    icon_prefs = prefs.setdefault("summoner_icon", {})
    inventory = icon_prefs.setdefault("inventory", [])
    found = False
    for icon in inventory:
        if icon.get("id") == icon_id:
            icon["owned"] = owned
            found = True
            break
    if not found:
        icon_prefs["inventory"].append({
            "id": icon_id,
            "name": f"Icône {icon_id}",
            "owned": owned,
            "image": f"https://ddragon.leagueoflegends.com/cdn/{DD_VERSION}/img/profileicon/{icon_id}.png"
        })
    save_prefs(prefs, LOL_PREFS_FILE)
    return jsonify({"status": "ok"})

@app.route("/set_icon_owned_bulk", methods=["POST"])
def set_icon_owned_bulk():
    data = request.get_json()
    icon_ids = data.get("iconIds", [])
    owned = bool(data.get("owned", True))

    if not isinstance(icon_ids, list):
        return jsonify({"error": "iconIds must be a list"}), 400

    prefs = load_prefs(LOL_PREFS_FILE)
    icon_prefs = prefs.setdefault("summoner_icon", {})
    inventory = icon_prefs.setdefault("inventory", [])

    for raw_id in icon_ids:
        try:
            icon_id = int(raw_id)
        except Exception:
            continue

        found = False
        for icon in inventory:
            if icon.get("id") == icon_id:
                icon["owned"] = owned
                found = True
                break
        if not found:
            inventory.append({
                "id": icon_id,
                "name": f"Icône {icon_id}",
                "owned": owned,
                "image": f"https://ddragon.leagueoflegends.com/cdn/{DD_VERSION}/img/profileicon/{icon_id}.png"
            })

    save_prefs(prefs, LOL_PREFS_FILE)
    return jsonify({"status": "ok"})

@app.route("/remove_icon_override", methods=["POST"])
def remove_icon_override():
    data = request.get_json()
    champ_id = str(data.get("champId", ""))
    prefs = load_prefs(LOL_PREFS_FILE)
    icon_prefs = prefs.setdefault("summoner_icon", {})
    overrides = icon_prefs.setdefault("champion_overrides", {})
    if champ_id in overrides:
        del overrides[champ_id]
        save_prefs(prefs, LOL_PREFS_FILE)
    return jsonify({"status": "ok"})

@app.route("/toggle_favorite", methods=["POST"])
def toggle_favorite():
    data = request.get_json()
    champ_id = str(data["champId"])
    skin_id = int(data["skinId"])
    add = data["add"]

    prefs = load_prefs(LOL_PREFS_FILE)
    favs = prefs.setdefault("favorites", {}).setdefault(champ_id, [])

    if add:
        if skin_id not in favs:
            favs.append(skin_id)
    else:
        if skin_id in favs:
            favs.remove(skin_id)

    save_prefs(prefs, LOL_PREFS_FILE)
    return jsonify({"status": "ok"})

@app.route("/toggle_tft_favorite", methods=["POST"])
def toggle_tft_favorite():
    data = request.get_json()
    category = data["category"]
    item_id = data["itemId"]
    add = data["add"]
    
    try:
        item_id_int = int(item_id)
    except (ValueError, TypeError):
        return jsonify({"error": "itemId doit être un nombre entier"}), 400

    prefs = load_prefs(TFT_PREFS_FILE)
    favs = prefs.setdefault("favorites", {}).setdefault(category, [])

    if add:
        if item_id_int not in favs:
            favs.append(item_id_int)
    else:
        if item_id_int in favs:
            favs.remove(item_id_int)

    save_prefs(prefs, TFT_PREFS_FILE)
    return jsonify({"status": "ok"})

def run_hud():
    print("→ HUD démarré → http://127.0.0.1:5000")
    app.run(port=5000, debug=False, use_reloader=False)

if __name__ == "__main__":
    run_hud()