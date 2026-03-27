# hud_monitor.py
# =========================================================
# 🎮 LoL/TFT HUD - Monitoring + LoL Skins + TFT Random
# =========================================================

from flask import Flask, jsonify, render_template_string, request
import requests
import urllib3
import json
import os

urllib3.disable_warnings()

app = Flask(__name__)

LOL_PREFS_FILE = "skin_prefs.json"
TFT_PREFS_FILE = "tft_prefs.json"

CHAMP_NAMES = {}

def load_champ_names():
    global CHAMP_NAMES
    try:
        v = requests.get("https://ddragon.leagueoflegends.com/api/versions.json").json()[0]
        data = requests.get(f"https://ddragon.leagueoflegends.com/cdn/{v}/data/fr_FR/champion.json").json()
        CHAMP_NAMES = {int(ch["key"]): ch["name"] for ch in data["data"].values()}
        print(f"✅ {len(CHAMP_NAMES)} noms de champions chargés")
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
                return data
        except Exception as e:
            print(f"Erreur lecture {file_path} : {e}")
            return {"favorites": {}, "library": {}}
    print(f"Fichier {file_path} introuvable, template vide retourné")
    return {"favorites": {}, "library": {}}

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
#monitoring {display:flex !important;}
#lol-settings, #tft-settings {display:none;padding:30px;background:#0f172a;border-radius:14px;margin:25px;}
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
</style>
</head>
<body>
<div class="header">
    <h1>LoL/TFT HUD</h1>
    <div class="nav-buttons">
        <button class="nav-btn active" onclick="showSection('monitoring')">Monitoring Game</button>
        <button class="nav-btn" onclick="showSection('lol-settings')">LoL Skins</button>
        <button class="nav-btn" onclick="showSection('tft-settings')">TFT Random</button>
    </div>
    <div class="diff" id="diff"></div>
</div>

<div id="monitoring" class="container">
    <div id="blue" class="team"></div>
    <div id="red" class="team"></div>
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

<script>
// Navigation
function showSection(sectionId) {
    document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');

    document.getElementById('monitoring').style.display = sectionId === 'monitoring' ? 'flex' : 'none';
    document.getElementById('lol-settings').style.display = sectionId === 'lol-settings' ? 'block' : 'none';
    document.getElementById('tft-settings').style.display = sectionId === 'tft-settings' ? 'block' : 'none';

    if (sectionId === 'lol-settings') loadLoLPrefs();
    if (sectionId === 'tft-settings') loadTFTPrefs();
}

// HUD monitoring
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
            const diff = document.getElementById("diff").innerText.match(/(-?\d+)/)?.[0] || "0";
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

@app.route("/prefs")
def prefs():
    prefs_type = request.args.get('type', 'lol')

    try:
        if prefs_type == 'tft':
            prefs_data = load_prefs(TFT_PREFS_FILE)
            return jsonify({"prefs": prefs_data})
        else:
            prefs_data = load_prefs(LOL_PREFS_FILE)
            return jsonify({
                "prefs": prefs_data,
                "champ_names": CHAMP_NAMES
            })
    except Exception as e:
        print(f"Erreur route /prefs ({prefs_type}): {e}")
        return jsonify({"error": str(e)}), 500

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