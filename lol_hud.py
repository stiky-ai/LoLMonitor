# =========================================================
# 🎮 LoL HUD - Gold + Spell Timer Tracker (Manual)
# =========================================================
# ✔ Gold estimé par joueur
# ✔ Gold team + diff
# ✔ Boutons pour lancer timers (Flash etc.)
# ✔ UI propre type HUD
# ✔ 100% légal (API Riot locale)
# =========================================================

from flask import Flask, jsonify, render_template_string
import requests
import urllib3

# 🔒 Désactive warning SSL (API locale Riot)
urllib3.disable_warnings()

app = Flask(__name__)

# =========================================================
# 🎨 HTML + UI (frontend)
# =========================================================
HTML = """
<!DOCTYPE html>
<html>
<head>
<title>LoL HUD</title>

<style>
body {
    background:#020617;
    color:white;
    font-family:Arial;
}

h1 {
    text-align:center;
}

.container {
    display:flex;
    justify-content:space-between;
}

.team {
    width:48%;
    background:#0f172a;
    padding:10px;
    border-radius:12px;
}

.player {
    background:#1e293b;
    margin:6px;
    padding:10px;
    border-radius:10px;
}

.gold {
    color:#facc15;
    font-weight:bold;
}

/* 🔥 Timer visuel */
.timer {
    color:#22c55e;
    font-weight:bold;
}

/* 🎯 Boutons */
button {
    margin-top:5px;
    margin-right:5px;
    padding:4px 8px;
    border:none;
    border-radius:6px;
    cursor:pointer;
    background:#334155;
    color:white;
}

button:hover {
    background:#475569;
}

.diff {
    text-align:center;
    font-size:26px;
    margin:10px;
}
</style>
</head>

<body>

<h1>LoL HUD</h1>
<div class="diff" id="diff"></div>

<div class="container">
    <div id="blue" class="team"></div>
    <div id="red" class="team"></div>
</div>

<script>

// =========================================================
// ⏱️ STOCKAGE DES TIMERS (frontend uniquement)
// =========================================================
let timers = {};

// CD de base des spells (en secondes)
const SPELL_COOLDOWNS = {
    "Flash": 300,
    "Saut éclair": 300,
    "Ignite": 180,
    "Embrasement": 180,
    "Teleport": 360,
    "Téléportation": 360,
    "Heal": 240,
    "Soins": 240,
    "Ghost": 210,
    "Fantôme": 210,
    "Smite": 90,
    "Châtiment": 90
};

// =========================================================
// 🎯 LANCER UN TIMER MANUEL
// =========================================================
function startTimer(player, spell){
    const key = player + "_" + spell;
    const cd = SPELL_COOLDOWNS[spell] || 180;

    timers[key] = Date.now() + cd * 1000;
}

// =========================================================
// ⏱️ CALCUL TEMPS RESTANT
// =========================================================
function getRemaining(player, spell){
    const key = player + "_" + spell;
    if (!timers[key]) return null;

    let remaining = Math.floor((timers[key] - Date.now()) / 1000);

    if (remaining <= 0){
        delete timers[key];
        return "READY";
    }

    return remaining + "s";
}

// =========================================================
// 🔄 UPDATE UI
// =========================================================
async function update(){
    let res = await fetch('/data');
    let data = await res.json();

    document.getElementById("diff").innerText =
        "Gold Diff: " + data.diff;

    function render(id, team, total){
        let html = `<h2>${id.toUpperCase()} (${total})</h2>`;

        team.forEach(p=>{
            let spellsHTML = "";

            p.spells.forEach(spell=>{
                let remaining = getRemaining(p.name, spell);

                spellsHTML += `
                <div>
                    ${spell}
                    <span class="timer">${remaining ? remaining : ""}</span>
                    <button onclick="startTimer('${p.name}','${spell}')">
                        Start
                    </button>
                </div>`;
            });

            html += `
            <div class="player">
                <div>${p.name}</div>
                <div class="gold">${p.gold} gold</div>
                ${spellsHTML}
            </div>`;
        });

        document.getElementById(id).innerHTML = html;
    }

    render("blue", data.blue, data.blue_total);
    render("red", data.red, data.red_total);
}

// refresh toutes les 1.5s
setInterval(update, 1500);

</script>

</body>
</html>
"""

# =========================================================
# 📊 BACKEND : récupération données LoL
# =========================================================
def get_data():
    try:
        url = "https://127.0.0.1:2999/liveclientdata/allgamedata"
        data = requests.get(url, verify=False).json()

        # 💰 gold réel du joueur
        active_gold = data.get("activePlayer", {}).get("currentGold", 0)
        active_name = data.get("activePlayer", {}).get("summonerName", "")

        blue, red = [], []
        bt, rt = 0, 0

        print("\n=== DEBUG ===")

        for p in data.get("allPlayers", []):

            name = p.get("summonerName", "Unknown")

            # 💰 estimation gold via items
            items_value = sum(
                i.get("price", 0) * i.get("count", 1)
                for i in p.get("items", [])
            )

            # ➕ ajoute gold réel si c'est toi
            if name == active_name:
                gold = items_value + active_gold
            else:
                gold = items_value

            print(f"{name} -> {gold}")

            # 🔥 récupération spells (nouveau format Riot)
            spells_raw = p.get("summonerSpells", {})
            spells = []

            for key in ["summonerSpellOne", "summonerSpellTwo"]:
                if key in spells_raw:
                    spells.append(spells_raw[key].get("displayName", "?"))

            player = {
                "name": name,
                "gold": int(gold),
                "spells": spells
            }

            # 🔵 🔴 répartition teams
            if p.get("team") == "ORDER":
                blue.append(player)
                bt += gold
            else:
                red.append(player)
                rt += gold

        print("Blue:", bt, "Red:", rt)

        return {
            "blue": blue,
            "red": red,
            "blue_total": int(bt),
            "red_total": int(rt),
            "diff": int(bt - rt)
        }

    except Exception as e:
        print("ERROR:", e)
        return {
            "blue": [],
            "red": [],
            "blue_total": 0,
            "red_total": 0,
            "diff": 0
        }

# =========================================================
# 🌐 ROUTES WEB
# =========================================================
@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/data")
def data():
    return jsonify(get_data())

# =========================================================
# ▶️ LANCEMENT
# =========================================================
if __name__ == "__main__":
    print("HUD lancé sur http://localhost:5000")
    app.run(port=5000)