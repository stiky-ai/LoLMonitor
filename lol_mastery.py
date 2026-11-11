from threading import Timer
import webbrowser

from flask import Flask, jsonify, render_template_string

from mastery_service import (
    get_champion_select_pool,
    get_gameflow_phase,
    get_mastery_data,
    get_post_game_mastery_update,
    load_champion_catalog,
)


app = Flask(__name__)
CHAMP_NAMES, CHAMP_IMAGES, DD_VERSION = load_champion_catalog()

MASTERY_HTML = """
<!doctype html>
<html lang="fr">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="theme-color" content="#07111f">
    <title>LoLMastery</title>
    <style>
        :root { color-scheme: dark; }
        * { box-sizing:border-box; }
        body { margin:0; }
        #mastery-root { width:100%; margin:0; padding:16px clamp(8px,2vw,24px); background:radial-gradient(ellipse at top,#172b46 0,#07111f 55%); color:#e2e8f0; font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif; }
        #mastery-root .shell { width:100%; margin:0; padding:0; }
        #mastery-root header { display:flex; align-items:end; justify-content:space-between; gap:20px; margin-bottom:28px; }
        #mastery-root .eyebrow { color:#7dd3fc; font-size:.75rem; font-weight:800; letter-spacing:.16em; text-transform:uppercase; }
        #mastery-root h1 { margin:8px 0; color:#f8fafc; font-size:clamp(2rem,7vw,3.8rem); letter-spacing:-.06em; line-height:1; }
        #mastery-root .intro { max-width:620px; margin:0; color:#94a3b8; line-height:1.6; }
        #mastery-root .toolbar { display:flex; align-items:center; flex-wrap:wrap; gap:8px; margin:0 0 14px; }
        #mastery-root .toolbar-primary,#mastery-root .toolbar-secondary { display:contents; }
        #mastery-root input,#mastery-root select,#mastery-root button { min-height:38px; border:1px solid #334155; border-radius:9px; font:inherit; }
        #mastery-root input:not([type="checkbox"]):not([type="range"]),#mastery-root select { min-width:0; padding:0 11px; background:#0f1b2d; color:#f8fafc; font-size:.88rem; }
        #mastery-root input[type="search"] { flex:0 1 175px; width:175px; }
        #mastery-root input[type="number"] { width:76px; min-height:32px; padding:0 8px; }
        #mastery-root select { width:auto; }
        #mastery-root #sort-order { flex:0 1 195px; }
        #mastery-root #level-filter { flex:0 1 138px; }
        #mastery-root label { display:flex; align-items:center; gap:7px; color:#cbd5e1; font-size:.82rem; }
        #mastery-root label input[type="checkbox"] { width:15px; height:15px; min-height:0; margin:0; accent-color:#38bdf8; }
        #mastery-root .toolbar-option { min-height:38px; padding:0 9px; border:1px solid #26384e; border-radius:9px; background:rgba(15,27,45,.72); white-space:nowrap; }
        #mastery-root #show-unknown-option { gap:6px; }
        #mastery-root #threshold-option { gap:5px; }
        #mastery-root .card-size-control { gap:6px; }
        #mastery-root .card-size-control input[type="range"] { width:clamp(78px,8vw,108px); height:20px; min-height:0; padding:0; accent-color:#38bdf8; }
        #mastery-root #card-size-value { min-width:40px; color:#e2e8f0; font-size:.78rem; font-variant-numeric:tabular-nums; }
        #mastery-root .toolbar-actions { display:flex; flex:0 0 auto; gap:6px; margin-left:0; }
        #mastery-root .icon-button { display:grid; width:38px; min-height:38px; place-items:center; padding:0; background:#16263b; color:#cbd5e1; cursor:pointer; transition:background .16s ease,border-color .16s ease,color .16s ease; }
        #mastery-root .icon-button:hover { border-color:#4b6584; background:#243a55; color:#fff; }
        #mastery-root .icon-button svg { width:17px; height:17px; }
        #mastery-root .icon-button:disabled { opacity:.55; cursor:wait; }
        #mastery-root .details-switch { display:flex; align-items:center; justify-content:center; gap:8px; min-width:106px; padding:0 10px; font-size:.8rem; font-weight:750; cursor:pointer; transition:background .16s ease,border-color .16s ease; }
        #mastery-root .details-switch .details-state { font-size:.72rem; font-weight:850; letter-spacing:.06em; }
        #mastery-root .details-switch.is-on { border-color:#166534; background:#14532d; color:#bbf7d0; }
        #mastery-root .details-switch.is-on:hover { border-color:#22c55e; background:#166534; }
        #mastery-root .details-switch.is-off { border-color:#7f1d1d; background:#450a0a; color:#fecaca; }
        #mastery-root .details-switch.is-off:hover { border-color:#ef4444; background:#7f1d1d; }
        #mastery-root .toolbar button:focus-visible { outline-offset:2px; }
        #mastery-root button:focus-visible,#mastery-root input:focus-visible,#mastery-root select:focus-visible { outline:2px solid #38bdf8; outline-offset:3px; }
        #mastery-root #status { min-height:24px; margin:0 0 8px; color:#a5f3fc; }
        #mastery-root #status.error { color:#fca5a5; }
        #mastery-root #gameflow-status { min-height:20px; margin:0 0 10px; color:#94a3b8; font-size:.86rem; }
        #mastery-root #champion-select-status { min-height:20px; margin:0 0 10px; color:#94a3b8; font-size:.86rem; }
        #mastery-root #champion-select-status.error { color:#fca5a5; }
        #mastery-root .mastery-legend { display:flex; align-items:center; flex-wrap:wrap; gap:8px; margin:0 0 10px; color:#cbd5e1; font-size:.8rem; }
        #mastery-root .mastery-legend-mark { width:11px; height:11px; flex:none; border:2px solid currentColor; border-radius:3px; }
        #mastery-root .mastery-legend-mark.is-close { color:#facc15; box-shadow:0 0 8px rgba(250,204,21,.2); }
        #mastery-root .mastery-legend-mark.is-selected { color:#22d3ee; }
        #mastery-root .mastery-legend-mark.is-bench { color:#c084fc; }
        #mastery-root #list { display:grid; grid-template-columns:repeat(auto-fill,minmax(min(100%,var(--card-size,250px)),1fr)); gap:12px; }
        #mastery-root .card { min-width:0; padding:12px; border:1px solid #334155; border-radius:12px; background:linear-gradient(145deg,rgba(23,39,61,.96),rgba(12,24,40,.96)); box-shadow:0 10px 28px rgba(0,0,0,.18); }
        #mastery-root .card.close { border:2px solid #facc15; box-shadow:0 0 0 2px rgba(250,204,21,.18); }
        #mastery-root .card.ally-selected { outline:2px solid #22d3ee; outline-offset:1px; }
        #mastery-root .card.ally-bench { outline:2px solid #c084fc; outline-offset:1px; }
        #mastery-root .card.max-level { border-color:#64748b; }
        #mastery-root .card-head { display:flex; align-items:center; gap:8px; }
        #mastery-root .card-title { display:flex; align-items:center; gap:8px; flex:1; min-width:0; }
        #mastery-root .card img,#mastery-root .fallback { width:64px; height:64px; flex:none; border:1px solid #475569; border-radius:10px; object-fit:cover; background:#0f172a; }
        #mastery-root .fallback { display:grid; place-items:center; color:#94a3b8; font-size:1.6rem; }
        #mastery-root .card-info { display:flex; flex:1; flex-direction:column; align-items:center; gap:6px; min-width:0; }
        #mastery-root h2 { width:100%; overflow:hidden; margin:0; color:#93c5fd; font-size:.84rem; text-align:center; text-overflow:ellipsis; white-space:nowrap; }
        #mastery-root .level { display:grid; place-items:center; width:52px; height:52px; flex:none; border:1px solid currentColor; border-radius:50%; font-size:1.4rem; font-weight:800; }
        #mastery-root .estimate-badge { padding:2px 6px; border:1px solid #a16207; border-radius:999px; background:#422006; color:#fde68a; font-size:.68rem; font-weight:750; }
        #mastery-root .availability-badge { padding:2px 6px; border:1px solid currentColor; border-radius:999px; font-size:.68rem; font-weight:750; }
        #mastery-root .availability-badge.is-selected { background:rgba(8,145,178,.18); color:#67e8f9; }
        #mastery-root .availability-badge.is-bench { background:rgba(126,34,206,.18); color:#d8b4fe; }
        #mastery-root .mastery-level-basic { background:#334155; color:#cbd5e1; }
        #mastery-root .mastery-level-black { background:#020617; color:#f8fafc; }
        #mastery-root .mastery-level-green { background:#14532d; color:#4ade80; }
        #mastery-root .mastery-level-blue { background:#1e3a8a; color:#60a5fa; }
        #mastery-root .mastery-level-violet { background:#581c87; color:#c084fc; }
        #mastery-root .mastery-level-gold { background:#713f12; color:#facc15; }
        #mastery-root .mastery-level-red { background:#7f1d1d; color:#f87171; }
        #mastery-root .mastery-toggle { display:flex; align-items:center; justify-content:center; width:28px; height:28px; min-height:28px; flex-shrink:0; padding:0; border:1px solid #475569; border-radius:7px; background:#0f172a; color:#cbd5e1; cursor:pointer; }
        #mastery-root .mastery-toggle:hover { background:#334155; color:white; }
        #mastery-root .mastery-toggle:focus-visible { outline:2px solid #38bdf8; outline-offset:2px; }
        #mastery-root .mastery-chevron { width:11px; height:11px; transition:transform .18s ease; }
        #mastery-root .mastery-toggle[aria-expanded="true"] .mastery-chevron { transform:rotate(180deg); }
        #mastery-root .mastery-details { margin-top:14px; padding-top:10px; border-top:1px solid #334155; }
        #mastery-root .mastery-details p { margin:8px 0; color:#e2e8f0; line-height:1.6; }
        #mastery-root .mastery-details strong { color:#f8fafc; }
        @media (max-width:560px) {
            #mastery-root header { align-items:flex-start; flex-direction:column; }
            #mastery-root input[type="search"] { flex:1 1 100%; width:100%; }
            #mastery-root #sort-order { flex:1 1 180px; }
            #mastery-root #level-filter { flex:1 1 120px; }
            #mastery-root .card-size-control input[type="range"] { width:clamp(78px,30vw,130px); }
        }
    </style>
</head>
<body>
    <main id="mastery-root" class="shell">
        <header>
            <div>
                <div class="eyebrow">League of Legends</div>
                <h1>LoLMastery</h1>
                <p class="intro">Suivez la progression des maîtrises du compte actuellement connecté au client Riot.</p>
            </div>
        </header>
        <div class="toolbar" aria-label="Filtres et réglages des maîtrises">
            <div class="toolbar-primary">
                <input id="search" type="search" placeholder="Rechercher…" aria-label="Rechercher un champion">
                <select id="sort-order" aria-label="Trier les maîtrises">
                    <option value="progress">Progression · XP restantes</option>
                    <option value="level">Niveau · décroissant</option>
                </select>
                <select id="level-filter" aria-label="Filtrer par niveau">
                    <option value="">Tous les niveaux</option>
                </select>
                <div class="toolbar-actions">
                    <button class="icon-button" id="refresh" type="button" aria-label="Actualiser les maîtrises" title="Actualiser les maîtrises">
                        <svg viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="M16.5 9.2A6.6 6.6 0 0 0 5.2 5.3L3.8 6.7M3.5 3.8v2.9h2.9m-2.9 4.1a6.6 6.6 0 0 0 11.3 3.9l1.4-1.4m.3 2.9v-2.9h-2.9" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>
                    </button>
                </div>
            </div>
            <div class="toolbar-secondary">
                <label class="toolbar-option" id="show-unknown-option" for="show-unknown"><input id="show-unknown" type="checkbox"> IDs inconnus</label>
                <label class="toolbar-option" id="threshold-option" for="xp-threshold">Proche ≤ <input id="xp-threshold" type="number" min="0" step="100" value="1000" aria-label="Seuil de proximité en XP"> XP</label>
                <label class="toolbar-option card-size-control" for="card-size">
                    Vignettes
                    <input id="card-size" type="range" min="190" max="380" step="10" value="250" aria-label="Taille des vignettes">
                    <output id="card-size-value" for="card-size">250 px</output>
                </label>
                <div class="toolbar-actions" aria-label="Détails des vignettes">
                    <button class="details-switch is-off" id="details-switch" type="button" aria-pressed="false" aria-label="Détails désactivés">
                        <span>Détails</span><span class="details-state">OFF</span>
                    </button>
                </div>
            </div>
        </div>
        <p id="status" role="status" aria-live="polite">Prêt à charger les maîtrises.</p>
        <p id="gameflow-status" role="status" aria-live="polite">Actualisation automatique à la fin d’une partie LoL.</p>
        <p id="champion-select-status" role="status" aria-live="polite">Vérification de la sélection de champions…</p>
        <div class="mastery-legend" aria-label="Légende des indicateurs">
            <span class="mastery-legend-mark is-close" aria-hidden="true"></span><span>Bordure dorée : proche du niveau suivant</span>
            <span class="mastery-legend-mark is-selected" aria-hidden="true"></span><span>Contour cyan : sélectionné par un allié</span>
            <span class="mastery-legend-mark is-bench" aria-hidden="true"></span><span>Contour violet : disponible sur le banc ARAM</span>
        </div>
        <section id="list" aria-label="Maîtrises des champions"></section>
    </main>
    <script>
        let champions = [];
        let visibleChampions = [];
        let selectedChampionIds = new Set();
        let benchChampionIds = new Set();
        const expandedChampions = new Set();
        let matchInProgress = false;
        let gameflowPollInProgress = false;
        let championSelectPollInProgress = false;
        let masteryRefreshPending = false;
        let matchMasterySnapshot = null;
        let postGameSyncTimer = null;
        let postGameSyncActive = false;
        let postGameSyncFinished = false;
        let postGameSyncGeneration = 0;
        const postGameSyncInterval = 2000;
        const postGameSyncMaxAttempts = 31;
        const gameflowPollInterval = 2000;
        const championSelectPollInterval = 2000;
        const statusNode = document.getElementById("status");
        const gameflowStatusNode = document.getElementById("gameflow-status");
        const championSelectStatusNode = document.getElementById("champion-select-status");
        const list = document.getElementById("list");
        const cardSizeControl = document.getElementById("card-size");
        const cardSizeValue = document.getElementById("card-size-value");

        function updateCardSize() {
            const size = Number(cardSizeControl.value);
            document.getElementById("mastery-root").style.setProperty("--card-size", `${size}px`);
            cardSizeValue.value = `${size} px`;
            cardSizeValue.textContent = `${size} px`;
            localStorage.setItem("mastery-card-size", String(size));
        }

        const savedCardSize = Number(localStorage.getItem("mastery-card-size"));
        if (savedCardSize >= 190 && savedCardSize <= 380) cardSizeControl.value = String(savedCardSize);
        updateCardSize();

        function masteryLevelClass(level) {
            if (level >= 10) return "mastery-level-red";
            return ({
                5: "mastery-level-black",
                6: "mastery-level-green",
                7: "mastery-level-blue",
                8: "mastery-level-violet",
                9: "mastery-level-gold"
            })[level] || "mastery-level-basic";
        }

        function render() {
            const query = document.getElementById("search").value.trim().toLocaleLowerCase("fr");
            const sortOrder = document.getElementById("sort-order").value;
            const level = document.getElementById("level-filter").value;
            const showUnknown = document.getElementById("show-unknown").checked;
            const threshold = Math.max(0, Number(document.getElementById("xp-threshold").value) || 0);
            const filtered = champions
                .filter(champion => showUnknown || champion.isRecognized)
                .filter(champion => !level || (level === "10+"
                    ? champion.championLevel >= 10
                    : String(champion.championLevel) === level))
                .filter(champion => champion.name.toLocaleLowerCase("fr").includes(query))
                .sort((a, b) => {
                    if (sortOrder === "level") {
                        return b.championLevel - a.championLevel
                            || b.championPoints - a.championPoints
                            || a.name.localeCompare(b.name, "fr");
                    }
                    if (a.hasNextLevel !== b.hasNextLevel) return a.hasNextLevel ? -1 : 1;
                    if (!a.hasNextLevel) return a.name.localeCompare(b.name, "fr");
                    return a.xpRemaining - b.xpRemaining || a.name.localeCompare(b.name, "fr");
                });
            visibleChampions = filtered;
            updateDetailsSwitch();
            list.replaceChildren();
            filtered.forEach(champion => {
                const card = document.createElement("article");
                card.className = "card";
                const isClose = champion.hasNextLevel && champion.xpRemaining <= threshold;
                const isExpanded = expandedChampions.has(String(champion.championId));
                const isSelectedByAlly = selectedChampionIds.has(champion.championId);
                const isOnBench = benchChampionIds.has(champion.championId);
                if (isClose) card.classList.add("close");
                if (isSelectedByAlly) card.classList.add("ally-selected");
                else if (isOnBench) card.classList.add("ally-bench");
                if (!champion.hasNextLevel) card.classList.add("max-level");
                const heading = document.createElement("div");
                heading.className = "card-head";
                const titleBlock = document.createElement("div");
                titleBlock.className = "card-title";
                if (champion.image) {
                    const image = document.createElement("img");
                    image.src = champion.image;
                    image.alt = "";
                    image.loading = "lazy";
                    titleBlock.append(image);
                } else {
                    const fallback = document.createElement("span");
                    fallback.className = "fallback";
                    fallback.textContent = "?";
                    titleBlock.append(fallback);
                }
                const info = document.createElement("div");
                info.className = "card-info";
                const title = document.createElement("h2");
                title.textContent = champion.name;
                const level = document.createElement("span");
                level.className = `level ${masteryLevelClass(champion.championLevel)}`;
                level.textContent = champion.championLevel;
                level.setAttribute("aria-label", `Niveau ${champion.championLevel}`);
                level.title = `Niveau ${champion.championLevel}`;
                if (champion.isEstimated) {
                    const estimateBadge = document.createElement("span");
                    estimateBadge.className = "estimate-badge";
                    estimateBadge.textContent = "estimé";
                    info.append(title, level, estimateBadge);
                } else {
                    info.append(title, level);
                }
                if (isSelectedByAlly || isOnBench) {
                    const availability = document.createElement("span");
                    availability.className = `availability-badge ${isSelectedByAlly ? "is-selected" : "is-bench"}`;
                    availability.textContent = isSelectedByAlly ? "Équipe" : "Banc ARAM";
                    info.append(availability);
                }

                const detailsId = `mastery-details-${champion.championId}`;
                const toggle = document.createElement("button");
                toggle.className = "mastery-toggle";
                toggle.type = "button";
                toggle.setAttribute("aria-expanded", String(isExpanded));
                toggle.setAttribute("aria-controls", detailsId);
                toggle.setAttribute("aria-label", `${isExpanded ? "Réduire" : "Afficher"} les détails de ${champion.name}`);
                toggle.title = `${isExpanded ? "Réduire" : "Afficher"} les détails de ${champion.name}`;
                toggle.innerHTML = '<svg class="mastery-chevron" viewBox="0 0 16 16" aria-hidden="true"><path d="m3.5 6 4.5 4 4.5-4" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8"/></svg>';
                toggle.addEventListener("click", () => toggleMasteryDetails(champion.championId));
                titleBlock.append(info);
                heading.append(titleBlock, toggle);

                const details = document.createElement("div");
                details.className = "mastery-details";
                details.id = detailsId;
                details.hidden = !isExpanded;
                if (champion.hasNextLevel) {
                    if (Number.isInteger(champion.pointsIntoLevel) && Number.isInteger(champion.xpRemaining)) {
                        const levelProgress = document.createElement("p");
                        const pointsIntoLevel = champion.pointsIntoLevel;
                        const levelThreshold = pointsIntoLevel + champion.xpRemaining;
                        levelProgress.textContent = `Progression du niveau : ${pointsIntoLevel.toLocaleString("fr-FR")} / ${levelThreshold.toLocaleString("fr-FR")} pts`;
                        details.append(levelProgress);
                    }
                    const progress = document.createElement("p");
                    progress.append("XP restantes : ");
                    const xp = document.createElement("strong");
                    xp.textContent = `${champion.xpRemaining.toLocaleString("fr-FR")} XP`;
                    progress.append(xp);
                    details.append(progress);
                } else {
                    const maxLevel = document.createElement("p");
                    maxLevel.textContent = "Niveau maximal atteint · aucun niveau suivant";
                    details.append(maxLevel);
                }
                if (champion.markRequiredForNextLevel > 0 || champion.tokensEarned > 0) {
                    const marks = document.createElement("p");
                    marks.textContent = `Jetons : ${champion.tokensEarned} / ${champion.markRequiredForNextLevel} requis(s)`;
                    details.append(marks);
                }
                const points = document.createElement("p");
                points.textContent = `Points de maîtrise : ${champion.championPoints.toLocaleString("fr-FR")}`;
                details.append(points);
                if (champion.isEstimated) {
                    const estimate = document.createElement("p");
                    estimate.textContent = `Gain estimé : +${champion.championPointsGained.toLocaleString("fr-FR")} pts, calculé sur ${champion.estimateSampleCount} gains réels précédents. Niveau et jetons non estimés.`;
                    details.append(estimate);
                }

                card.append(heading, details);
                list.append(card);
            });
            const hiddenUnknown = showUnknown ? 0 : champions.filter(champion => !champion.isRecognized).length;
            statusNode.textContent = filtered.length
                ? `${filtered.length} maîtrise(s) affichée(s).${hiddenUnknown ? ` ${hiddenUnknown} ID(s) non reconnu(s) masqué(s).` : ""}`
                : "Aucune maîtrise ne correspond à ces filtres.";
        }

        function toggleMasteryDetails(championId) {
            const key = String(championId);
            if (expandedChampions.has(key)) expandedChampions.delete(key);
            else expandedChampions.add(key);
            render();
        }

        function updateDetailsSwitch() {
            const button = document.getElementById("details-switch");
            const enabled = visibleChampions.length > 0
                && visibleChampions.every(champion => expandedChampions.has(String(champion.championId)));
            button.classList.toggle("is-on", enabled);
            button.classList.toggle("is-off", !enabled);
            button.setAttribute("aria-pressed", String(enabled));
            button.setAttribute("aria-label", `Détails ${enabled ? "activés" : "désactivés"}`);
            button.innerHTML = `<span>Détails</span><span class="details-state">${enabled ? "ON" : "OFF"}</span>`;
        }

        function setMasteryDetailsExpanded(expanded) {
            visibleChampions.forEach(champion => {
                const key = String(champion.championId);
                if (expanded) expandedChampions.add(key);
                else expandedChampions.delete(key);
            });
            render();
        }

        function masterySnapshot() {
            return JSON.stringify(champions
                .map(champion => [
                    champion.championId,
                    champion.championLevel,
                    champion.championPoints,
                    champion.xpRemaining,
                    champion.markRequiredForNextLevel,
                    champion.tokensEarned
                ])
                .sort((a, b) => a[0] - b[0]));
        }

        async function loadMasteries(forceRefresh = false) {
            statusNode.classList.remove("error");
            const refreshButton = document.getElementById("refresh");
            if (refreshButton.disabled) {
                if (forceRefresh) masteryRefreshPending = true;
                return false;
            }
            statusNode.textContent = "Chargement des maîtrises…";
            refreshButton.disabled = true;
            try {
                const response = await fetch("/mastery", {cache: "no-store"});
                const data = await response.json();
                if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
                if (!Array.isArray(data.champions)) throw new Error("Format des maîtrises invalide.");
                champions = data.champions;
                const levels = [...new Set(champions.map(champion => champion.championLevel))].sort((a, b) => a - b);
                const levelFilter = document.getElementById("level-filter");
                levelFilter.replaceChildren(new Option("Tous les niveaux", ""));
                levels.filter(level => level < 10)
                    .forEach(level => levelFilter.add(new Option(`Niveau ${level}`, String(level))));
                if (levels.some(level => level >= 10)) levelFilter.add(new Option("10+", "10+"));
                statusNode.textContent = `${champions.length} champion(s) chargé(s).`;
                render();
                if (postGameSyncFinished && !matchInProgress) {
                    const provisionalChampion = champions.find(champion => champion.isProvisional);
                    gameflowStatusNode.textContent = provisionalChampion
                        ? `${provisionalChampion.name} niveau ${provisionalChampion.championLevel} reste affiché provisoirement, en attente de confirmation du client.`
                        : "Maîtrises rechargées manuellement.";
                }
                return true;
            } catch (error) {
                statusNode.classList.add("error");
                statusNode.textContent = error.message;
                list.replaceChildren();
                return false;
            } finally {
                refreshButton.disabled = false;
                if (masteryRefreshPending) {
                    masteryRefreshPending = false;
                    loadMasteries(true);
                }
            }
        }

        async function synchronizeMasteriesAfterMatch(previousSnapshot, generation, attempt = 1) {
            let postGameUpdateAvailable = false;
            let postGameUpdateError = null;
            let estimatePending = null;
            try {
                const updateResponse = await fetch("/post-game-mastery-update", {cache: "no-store"});
                const updateData = await updateResponse.json();
                if (!updateResponse.ok) throw new Error(updateData.error || `HTTP ${updateResponse.status}`);
                postGameUpdateAvailable = updateData.available === true;
                if (updateData.estimatePending) estimatePending = updateData;
                if (updateData.warning) postGameUpdateError = updateData.warning;
            } catch (error) {
                postGameUpdateError = error.message;
            }

            const refreshed = await loadMasteries(true);
            if (generation !== postGameSyncGeneration) return;
            const hasProvisionalMastery = champions.some(champion => champion.isProvisional);
            if (refreshed && !hasProvisionalMastery && (postGameUpdateAvailable || masterySnapshot() !== previousSnapshot)) {
                postGameSyncTimer = null;
                postGameSyncActive = false;
                postGameSyncFinished = true;
                gameflowStatusNode.textContent = "Maîtrises synchronisées après la partie.";
                return;
            }
            if (attempt >= postGameSyncMaxAttempts) {
                postGameSyncTimer = null;
                postGameSyncActive = false;
                postGameSyncFinished = true;
                const estimatedChampion = champions.find(champion => champion.isEstimated);
                if (estimatedChampion) {
                    gameflowStatusNode.textContent = `${estimatedChampion.name} : gain estimé de +${estimatedChampion.championPointsGained.toLocaleString("fr-FR")} points (${estimatedChampion.estimateSampleCount} gains réels de référence). Niveau et jetons restent ceux du client.`;
                } else if (hasProvisionalMastery) {
                    gameflowStatusNode.textContent = "Le résultat de maîtrise reste affiché provisoirement, en attente de confirmation du client.";
                } else if (estimatePending) {
                    gameflowStatusNode.textContent = estimatePending.pendingReason === "missing-match-snapshot"
                        ? `Gain réel indisponible : total de maîtrise avant-match manquant, estimation impossible pour cette partie.${postGameUpdateError ? ` ${postGameUpdateError}` : ""}`
                        : `Gain réel indisponible : estimation en attente de ${estimatePending.requiredGainSamples} gains réels de référence (actuellement ${estimatePending.observedGainSamples}).${postGameUpdateError ? ` ${postGameUpdateError}` : ""}`;
                } else {
                    gameflowStatusNode.textContent = `Aucune mise à jour des maîtrises confirmée après 60 s.${postGameUpdateError ? ` ${postGameUpdateError}` : ""}`;
                }
                return;
            }

            const provisionalChampion = champions.find(champion => champion.isProvisional);
            gameflowStatusNode.textContent = provisionalChampion?.isEstimated
                ? `${provisionalChampion.name} : gain estimé provisoirement ; attente d’une valeur réelle du client… nouvelle lecture ${attempt}/${postGameSyncMaxAttempts} dans 2 s.`
                : provisionalChampion
                ? `${provisionalChampion.name} niveau ${provisionalChampion.championLevel} affiché provisoirement ; attente de synchronisation… nouvelle lecture ${attempt}/${postGameSyncMaxAttempts} dans 2 s.`
                : `Synchronisation des maîtrises… nouvelle lecture ${attempt}/${postGameSyncMaxAttempts} dans 2 s.`;
            postGameSyncTimer = window.setTimeout(
                () => synchronizeMasteriesAfterMatch(previousSnapshot, generation, attempt + 1),
                postGameSyncInterval
            );
        }

        async function checkGameflow() {
            if (gameflowPollInProgress) return;
            gameflowPollInProgress = true;
            try {
                const response = await fetch("/gameflow-phase", {cache: "no-store"});
                const data = await response.json();
                if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
                if (typeof data.phase !== "string") throw new Error("Format d’état de partie invalide.");

                if (data.phase === "InProgress") {
                    if (!matchInProgress) {
                        matchMasterySnapshot = masterySnapshot();
                        postGameSyncActive = false;
                        postGameSyncFinished = false;
                        postGameSyncGeneration++;
                        if (postGameSyncTimer !== null) {
                            window.clearTimeout(postGameSyncTimer);
                            postGameSyncTimer = null;
                        }
                    }
                    matchInProgress = true;
                } else if (matchInProgress && data.phase === "WaitingForStats") {
                    if (!postGameSyncActive && !postGameSyncFinished) {
                        postGameSyncActive = true;
                        const generation = ++postGameSyncGeneration;
                        gameflowStatusNode.textContent = "Partie terminée : lecture des gains de maîtrise et synchronisation…";
                        synchronizeMasteriesAfterMatch(matchMasterySnapshot, generation);
                    }
                } else if (matchInProgress) {
                    matchInProgress = false;
                    const previousSnapshot = matchMasterySnapshot;
                    matchMasterySnapshot = null;
                    if (!postGameSyncActive && !postGameSyncFinished) {
                        postGameSyncActive = true;
                        const generation = ++postGameSyncGeneration;
                        gameflowStatusNode.textContent = "Fin de partie détectée : synchronisation des maîtrises…";
                        synchronizeMasteriesAfterMatch(previousSnapshot, generation);
                    }
                } else if (!postGameSyncActive && !postGameSyncFinished) {
                    gameflowStatusNode.textContent = "Actualisation automatique à la fin d’une partie LoL.";
                }
            } catch (error) {
                gameflowStatusNode.textContent = `Détection de fin de partie indisponible : ${error.message}`;
            } finally {
                gameflowPollInProgress = false;
            }
        }

        function sameChampionIds(left, right) {
            return left.size === right.size && [...left].every(championId => right.has(championId));
        }

        async function checkChampionSelectPool() {
            if (championSelectPollInProgress) return;
            championSelectPollInProgress = true;
            try {
                const response = await fetch("/champion-select-pool", {cache: "no-store"});
                const data = await response.json();
                if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
                if (typeof data.available !== "boolean"
                    || !Array.isArray(data.selectedChampionIds)
                    || !Array.isArray(data.benchChampionIds)) {
                    throw new Error("Format de la sélection de champions invalide.");
                }

                const nextSelectedIds = new Set(data.available ? data.selectedChampionIds : []);
                const nextBenchIds = new Set(data.available ? data.benchChampionIds : []);
                const changed = !sameChampionIds(selectedChampionIds, nextSelectedIds)
                    || !sameChampionIds(benchChampionIds, nextBenchIds);
                selectedChampionIds = nextSelectedIds;
                benchChampionIds = nextBenchIds;

                championSelectStatusNode.classList.remove("error");
                championSelectStatusNode.textContent = data.available
                    ? `Sélection en cours · ${selectedChampionIds.size} champion(s) allié(s) sélectionné(s), ${benchChampionIds.size} disponible(s) sur le banc.`
                    : "Aucune sélection de champion en cours.";
                if (changed && champions.length) render();
            } catch (error) {
                championSelectStatusNode.classList.add("error");
                championSelectStatusNode.textContent = `Lecture de la sélection indisponible : ${error.message}`;
            } finally {
                championSelectPollInProgress = false;
            }
        }

        document.getElementById("search").addEventListener("input", render);
        document.getElementById("sort-order").addEventListener("change", render);
        document.getElementById("level-filter").addEventListener("change", render);
        document.getElementById("show-unknown").addEventListener("change", render);
        document.getElementById("xp-threshold").addEventListener("input", render);
        cardSizeControl.addEventListener("input", updateCardSize);
        document.getElementById("refresh").addEventListener("click", loadMasteries);
        document.getElementById("details-switch").addEventListener("click", () => {
            const enabled = visibleChampions.length > 0
                && visibleChampions.every(champion => expandedChampions.has(String(champion.championId)));
            setMasteryDetailsExpanded(!enabled);
        });
        loadMasteries();
        checkGameflow();
        checkChampionSelectPool();
        window.setInterval(checkGameflow, gameflowPollInterval);
        window.setInterval(checkChampionSelectPool, championSelectPollInterval);
    </script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(MASTERY_HTML)


@app.route("/mastery")
def mastery():
    payload, status = get_mastery_data(CHAMP_NAMES, CHAMP_IMAGES, DD_VERSION)
    response = jsonify(payload)
    response.headers["Cache-Control"] = "no-store"
    return response, status


@app.route("/post-game-mastery-update")
def post_game_mastery_update():
    payload, status = get_post_game_mastery_update()
    response = jsonify(payload)
    response.headers["Cache-Control"] = "no-store"
    return response, status


@app.route("/gameflow-phase")
def gameflow_phase():
    payload, status = get_gameflow_phase()
    response = jsonify(payload)
    response.headers["Cache-Control"] = "no-store"
    return response, status


@app.route("/champion-select-pool")
def champion_select_pool():
    payload, status = get_champion_select_pool()
    response = jsonify(payload)
    response.headers["Cache-Control"] = "no-store"
    return response, status


def run_mastery_app(open_browser=True):
    print("LoLMastery demarre : http://127.0.0.1:5001")
    if open_browser:
        browser_timer = Timer(1.0, _open_app_page, args=("http://127.0.0.1:5001",))
        browser_timer.daemon = True
        browser_timer.start()
    app.run(host="127.0.0.1", port=5001, debug=False, use_reloader=False)


def _open_app_page(url):
    try:
        opened = webbrowser.open(url, new=2)
    except (OSError, webbrowser.Error) as error:
        print(f"Impossible d'ouvrir le navigateur par défaut : {error}")
        return
    if not opened:
        print(f"Impossible d'ouvrir le navigateur par défaut. Ouvre {url} manuellement.")


if __name__ == "__main__":
    run_mastery_app()
