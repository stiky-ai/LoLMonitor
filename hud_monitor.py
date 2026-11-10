# hud_monitor.py
# =========================================================
# 🎮 LoL/TFT HUD - Monitoring + LoL Skins + TFT Random
# =========================================================

from flask import Flask, jsonify, render_template_string, request
import requests
import urllib3
import json
import os
import webbrowser
from threading import Timer

from lol_mastery import (
    CHAMP_IMAGES as MASTERY_CHAMP_IMAGES,
    CHAMP_NAMES as MASTERY_CHAMP_NAMES,
    DD_VERSION as MASTERY_DD_VERSION,
    MASTERY_HTML,
    get_gameflow_phase,
    get_mastery_data,
)

urllib3.disable_warnings()

app = Flask(__name__)

LOL_PREFS_FILE = "skin_prefs.json"
TFT_PREFS_FILE = "tft_prefs.json"

CHAMP_NAMES = {}
DD_VERSION = "latest"

def load_champ_names():
    global CHAMP_NAMES, DD_VERSION
    try:
        versions = requests.get("https://ddragon.leagueoflegends.com/api/versions.json").json()
        DD_VERSION = versions[0]
        data = requests.get(f"https://ddragon.leagueoflegends.com/cdn/{DD_VERSION}/data/fr_FR/champion.json").json()
        CHAMP_NAMES = {int(ch["key"]): ch["name"] for ch in data["data"].values()}
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
                data.setdefault("automation_enabled", True)
                icon_prefs = data.setdefault("summoner_icon", {})
                icon_prefs.setdefault("default", None)
                icon_prefs.setdefault("champion_overrides", {})
                icon_prefs.setdefault("inventory", [])
                return data
        except Exception as e:
            print(f"Erreur lecture {file_path} : {e}")
            return {"favorites": {}, "library": {}, "automation_enabled": True, "summoner_icon": {"default": None, "champion_overrides": {}, "inventory": []}}
    print(f"Fichier {file_path} introuvable, template vide retourné")
    return {"favorites": {}, "library": {}, "automation_enabled": True, "summoner_icon": {"default": None, "champion_overrides": {}, "inventory": []}}

def save_prefs(data, file_path):
    try:
        data.setdefault("automation_enabled", True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"{file_path} sauvegardé")
        return True
    except Exception as e:
        print(f"Erreur sauvegarde {file_path} : {e}")
        return False

MAIN_HTML = """
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#020617">
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
.automation-controls {display:flex;justify-content:center;flex-wrap:wrap;gap:12px;margin:12px 0;}
.automation-control {display:flex;align-items:center;gap:10px;padding:8px 14px;border:1px solid #334155;border-radius:10px;background:#0f172a;color:#cbd5e1;}
.automation-control input {width:18px;height:18px;margin:0;accent-color:#22c55e;}
.automation-control .automation-state {min-width:34px;color:#22c55e;font-weight:700;}
.automation-control .automation-state.off {color:#f87171;}
#automation-error {min-height:1.2em;color:#fca5a5;}
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
#mastery-settings {display:none;width:100%;max-width:none;margin:0;padding:0;border:0;border-radius:0;background:transparent;box-shadow:none;}
.search {width:100%;padding:16px;margin-bottom:25px;background:#1e293b;border:none;border-radius:12px;color:white;font-size:1.15rem;box-sizing:border-box;}
#lol-prefs-list, #tft-prefs-list {display:grid;grid-template-columns:repeat(auto-fill, minmax(380px, 1fr));gap:20px;}
.champ-card, .tft-card {background:#1e293b;border-radius:12px;overflow:hidden;box-shadow:0 4px 15px rgba(0,0,0,0.5);}
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
* {box-sizing:border-box;}
body {min-width:320px;background:radial-gradient(ellipse at top,#172b46 0,#020617 55%);font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;}
.header {position:relative;padding:24px clamp(14px,4vw,48px) 18px;background:linear-gradient(180deg,rgba(15,23,42,.96),rgba(2,6,23,.82));border-bottom:1px solid #1e293b;}
h1 {margin:0 0 16px;font-size:clamp(1.7rem,4vw,2.4rem);letter-spacing:-.04em;}
.automation-controls {gap:10px;margin:0 auto 12px;max-width:740px;}
.automation-control {flex:1 1 260px;min-width:0;justify-content:center;gap:12px;padding:10px 14px;background:rgba(15,23,42,.9);transition:border-color .18s,background .18s;}
.automation-control:has(input:checked) {border-color:#166534;background:rgba(6,78,59,.28);}
.automation-control input {appearance:none;position:relative;flex:none;width:38px;height:22px;border:1px solid #475569;border-radius:999px;background:#334155;cursor:pointer;transition:background .18s,border-color .18s;}
.automation-control input::after {position:absolute;top:2px;left:2px;width:16px;height:16px;border-radius:50%;background:#cbd5e1;content:"";transition:transform .18s,background .18s;}
.automation-control input:checked {border-color:#10b981;background:#047857;}
.automation-control input:checked::after {transform:translateX(16px);background:#fff;}
.automation-control input:disabled {cursor:wait;opacity:.65;}
.automation-control input:focus-visible {outline:2px solid #38bdf8;outline-offset:3px;}
.automation-control .automation-state {min-width:34px;text-align:center;}
#automation-error {max-width:740px;margin:0 auto;color:#fca5a5;font-size:.84rem;}
.nav-buttons {display:flex;justify-content:center;flex-wrap:wrap;gap:8px;margin:14px auto 0;}
.nav-btn {margin:0;padding:10px 16px;border:1px solid #334155;font-size:.96rem;font-weight:700;transition:background .18s,border-color .18s,transform .18s;}
.nav-btn:hover {transform:translateY(-1px);border-color:#475569;}
.nav-btn.active {border-color:#3b82f6;background:#1d4ed8;}
button:focus-visible,input:focus-visible,select:focus-visible {outline:2px solid #38bdf8;outline-offset:3px;}
#monitoring {justify-content:center;align-items:flex-start;max-width:1480px;margin:0 auto;padding:24px clamp(12px,3vw,32px);gap:18px;}
.team {width:auto;min-width:0;flex:1 1 0;border:1px solid #1e293b;box-shadow:0 16px 40px rgba(0,0,0,.24);}
#lol-settings,#tft-settings,#icon-settings {width:calc(100% - 32px);max-width:1480px;margin:20px auto;padding:clamp(16px,3vw,30px);border:1px solid #1e293b;box-shadow:0 16px 40px rgba(0,0,0,.2);}
#lol-prefs-list,#tft-prefs-list {grid-template-columns:repeat(auto-fill,minmax(min(100%,300px),1fr));gap:16px;}
.champ-card,.tft-card,.icon-card {min-width:0;border:1px solid #334155;box-shadow:0 10px 28px rgba(0,0,0,.18);}
.card-header {padding:14px 16px;font-size:1.08rem;overflow-wrap:anywhere;}
.grid-container {grid-template-columns:repeat(auto-fit,minmax(min(100%,180px),1fr));}
.item,.skin-item {min-width:0;gap:8px;padding:10px 12px;font-size:.96rem;}
.item-name,.skin-name {min-width:0;overflow-wrap:anywhere;}
.heart {flex:none;padding:4px 8px;}
.selection-toolbar {gap:8px;}
.icon-override-form > div {min-width:min(100%,260px)!important;}
.search {margin-bottom:18px;font-size:1rem;}
@media (max-width: 760px) {
    .header {padding:20px 14px 16px;}
    .automation-controls {gap:8px;margin-bottom:10px;}
    .automation-control {flex-basis:100%;justify-content:flex-start;padding:10px 12px;}
    .nav-buttons {display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;}
    .nav-btn {width:100%;padding:11px 8px;font-size:.9rem;}
    #monitoring {flex-direction:column;padding:14px 10px;gap:12px;}
    .team {width:100%;flex:none;padding:14px;}
    #lol-settings,#tft-settings,#icon-settings {width:calc(100% - 20px);margin:10px;padding:16px;}
    #lol-prefs-list,#tft-prefs-list {grid-template-columns:repeat(auto-fill,minmax(min(100%,260px),1fr));gap:12px;}
    .selection-toolbar {align-items:stretch;}
    .selection-toolbar .nav-btn {width:auto;flex:1 1 150px;}
    .icon-override-form {flex-direction:column;}
    .icon-override-form > div {width:100%;min-width:0!important;}
}
@media (max-width: 420px) {
    .nav-btn {padding:10px 6px;font-size:.84rem;}
    #monitoring {padding:10px 8px;}
    .team {padding:11px;}
    .team-header {font-size:1.35rem;}
    .player {margin:9px 0;padding:11px;}
    #lol-settings,#tft-settings,#icon-settings {width:calc(100% - 16px);padding:12px;}
    .grid-container {grid-template-columns:1fr;padding:9px;gap:8px;}
    .card-header {padding:12px;}
    .icon-card {padding:12px;}
    .icon-card .icon-actions button {max-width:100%;font-size:.85rem;}
}
</style>
</head>
<body>
<div class="header">
    <h1>LoL/TFT HUD</h1>
    <div class="automation-controls" aria-label="Automatismes">
        <label class="automation-control" for="lol-automation">
            <input id="lol-automation" type="checkbox" checked disabled onchange="setAutomation('lol', this.checked)">
            <span>Automatisme LoL</span>
            <span id="lol-automation-state" class="automation-state">ON</span>
        </label>
        <label class="automation-control" for="tft-automation">
            <input id="tft-automation" type="checkbox" checked disabled onchange="setAutomation('tft', this.checked)">
            <span>Automatisme TFT</span>
            <span id="tft-automation-state" class="automation-state">ON</span>
        </label>
    </div>
    <div id="automation-error" role="status" aria-live="polite"></div>
    <div class="nav-buttons">
        <button class="nav-btn active" onclick="showSection('monitoring', this)">Monitoring Game</button>
        <button class="nav-btn" onclick="showSection('lol-settings', this)">LoL Skins</button>
        <button class="nav-btn" onclick="showSection('mastery-settings', this)">Maîtrise</button>
        <button class="nav-btn" onclick="showSection('tft-settings', this)">TFT Random</button>
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

<div id="tft-settings">
    <h2>⚙️ TFT Random Preferences</h2>
    <input type="text" id="tft-search" class="search" placeholder="🔎 Filtrer par catégorie..." onkeyup="filterTFT()">
    <div id="tft-prefs-list"></div>
</div>

<div id="mastery-settings">
    <div id="mastery-content" role="region" aria-label="Maîtrises LoL">Chargement des maîtrises…</div>
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
let masteryViewLoaded = false;
let masteryViewLoading = false;

async function loadMasteryView() {
    if (masteryViewLoaded || masteryViewLoading) return;
    masteryViewLoading = true;
    const container = document.getElementById("mastery-content");
    container.textContent = "Chargement des maîtrises…";
    try {
        const response = await fetch("/mastery-panel", {cache: "no-store"});
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const page = new DOMParser().parseFromString(await response.text(), "text/html");
        const style = page.querySelector("style");
        const root = page.getElementById("mastery-root");
        const script = page.querySelector("script");
        if (!style || !root || !script) throw new Error("La vue Maîtrise est incomplète.");

        root.querySelector("header")?.remove();
        const scopedStyles = document.createElement("style");
        scopedStyles.textContent = style.textContent;
        document.head.append(scopedStyles);
        container.replaceChildren(root);
        const activeScript = document.createElement("script");
        activeScript.textContent = script.textContent;
        document.body.append(activeScript);
        masteryViewLoaded = true;
    } catch (error) {
        container.textContent = `Impossible de charger les maîtrises : ${error.message}`;
        console.error("Erreur chargement de la vue Maîtrise :", error);
    } finally {
        masteryViewLoading = false;
    }
}

function showSection(sectionId, button) {
    document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));
    button.classList.add('active');

    document.getElementById('monitoring-view').style.display = sectionId === 'monitoring' ? 'block' : 'none';
    document.getElementById('lol-settings').style.display = sectionId === 'lol-settings' ? 'block' : 'none';
    document.getElementById('tft-settings').style.display = sectionId === 'tft-settings' ? 'block' : 'none';
    document.getElementById('mastery-settings').style.display = sectionId === 'mastery-settings' ? 'block' : 'none';
    document.getElementById('icon-settings').style.display = sectionId === 'icon-settings' ? 'block' : 'none';

    if (sectionId === 'lol-settings') loadLoLPrefs();
    if (sectionId === 'tft-settings') loadTFTPrefs();
    if (sectionId === 'mastery-settings') loadMasteryView();
    if (sectionId === 'icon-settings') loadIconPrefs();
}

function updateAutomationControl(game, enabled) {
    const input = document.getElementById(`${game}-automation`);
    const state = document.getElementById(`${game}-automation-state`);
    input.checked = enabled;
    state.textContent = enabled ? "ON" : "OFF";
    state.classList.toggle("off", !enabled);
}

async function loadAutomationStates() {
    const error = document.getElementById("automation-error");
    try {
        const response = await fetch("/automation-settings");
        const states = await response.json();
        if (!response.ok) throw new Error(states.error || `HTTP ${response.status}`);
        updateAutomationControl("lol", states.lol);
        updateAutomationControl("tft", states.tft);
        document.getElementById("lol-automation").disabled = false;
        document.getElementById("tft-automation").disabled = false;
        error.textContent = "";
    } catch (e) {
        error.textContent = `Impossible de lire les automatismes : ${e.message}`;
        console.error("Erreur lecture automatismes :", e);
    }
}

async function setAutomation(game, enabled) {
    const input = document.getElementById(`${game}-automation`);
    const error = document.getElementById("automation-error");
    input.disabled = true;
    try {
        const response = await fetch("/set_automation", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({game, enabled})
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);
        updateAutomationControl(game, result.enabled);
        error.textContent = "";
    } catch (e) {
        updateAutomationControl(game, !enabled);
        error.textContent = `Impossible de sauvegarder l'automatisme : ${e.message}`;
        console.error("Erreur sauvegarde automatisme :", e);
    } finally {
        input.disabled = false;
    }
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
loadAutomationStates();

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

@app.route("/mastery-panel")
def mastery_panel():
    return MASTERY_HTML

@app.route("/mastery")
def mastery_data():
    payload, status = get_mastery_data(
        MASTERY_CHAMP_NAMES, MASTERY_CHAMP_IMAGES, MASTERY_DD_VERSION
    )
    response = jsonify(payload)
    response.headers["Cache-Control"] = "no-store"
    return response, status

@app.route("/gameflow-phase")
def mastery_gameflow_phase():
    payload, status = get_gameflow_phase()
    response = jsonify(payload)
    response.headers["Cache-Control"] = "no-store"
    return response, status

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

@app.route("/set_automation", methods=["POST"])
def set_automation():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Corps JSON invalide"}), 400

    game = data.get("game")
    enabled = data.get("enabled")
    if game not in ("lol", "tft") or not isinstance(enabled, bool):
        return jsonify({"error": "game doit être lol ou tft et enabled doit être booléen"}), 400

    file_path = LOL_PREFS_FILE if game == "lol" else TFT_PREFS_FILE
    try:
        prefs_data = load_automation_prefs(file_path)
        prefs_data["automation_enabled"] = enabled
        if not save_prefs(prefs_data, file_path):
            return jsonify({"error": f"Impossible de sauvegarder {file_path}"}), 500
    except (OSError, ValueError) as e:
        print(f"Erreur mise à jour des automatismes ({game}) : {e}")
        return jsonify({"error": f"Impossible de lire ou mettre à jour {file_path}"}), 500
    return jsonify({"game": game, "enabled": enabled})

@app.route("/automation-settings")
def automation_settings():
    try:
        lol_prefs = load_automation_prefs(LOL_PREFS_FILE)
        tft_prefs = load_automation_prefs(TFT_PREFS_FILE)
        return jsonify({
            "lol": lol_prefs.get("automation_enabled", True),
            "tft": tft_prefs.get("automation_enabled", True),
        })
    except (OSError, ValueError) as e:
        print(f"Erreur lecture des automatismes : {e}")
        return jsonify({"error": "Impossible de lire les préférences d’automatisation."}), 500

def load_automation_prefs(file_path):
    if not os.path.exists(file_path):
        return {
            "favorites": {},
            "library": {},
            "automation_enabled": True,
            "summoner_icon": {"default": None, "champion_overrides": {}, "inventory": []},
        }

    with open(file_path, "r", encoding="utf-8") as prefs_file:
        prefs_data = json.load(prefs_file)
    if not isinstance(prefs_data, dict):
        raise ValueError(f"Format de préférences invalide : {file_path}")
    if not isinstance(prefs_data.get("automation_enabled", True), bool):
        raise ValueError(f"État d’automatisation invalide : {file_path}")
    return prefs_data

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
    browser_timer = Timer(1.0, _open_app_page, args=("http://127.0.0.1:5000",))
    browser_timer.daemon = True
    browser_timer.start()
    app.run(port=5000, debug=False, use_reloader=False)

def _open_app_page(url):
    try:
        opened = webbrowser.open(url, new=2)
    except (OSError, webbrowser.Error) as error:
        print(f"Impossible d'ouvrir le navigateur par défaut : {error}")
        return
    if not opened:
        print(f"Impossible d'ouvrir le navigateur par défaut. Ouvre {url} manuellement.")

if __name__ == "__main__":
    run_hud()