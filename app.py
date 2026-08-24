import json
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from data_utils import normalize_players_df, team_players_path

st.set_page_config(page_title="Speler Prestatie Dashboard", layout="wide")
# ---------------------------------------------------------------------------
# Coach-login: elke coach heeft een eigen account dat gekoppeld is aan één
# team. Accounts staan in Streamlit secrets (zie SETUP_TEAMS.md) — dat is
# de enige plek waar coach-toegang wordt beheerd, coaches kunnen zichzelf
# niet registreren.
# ---------------------------------------------------------------------------
if "coach_authed" not in st.session_state:
    st.session_state.coach_authed = False

if not st.session_state.coach_authed:
    st.markdown("## Inloggen")
    username = st.text_input("Gebruikersnaam")
    password = st.text_input("Wachtwoord", type="password")
    if st.button("Inloggen"):
        coaches = st.secrets.get("coaches", {})
        coach = coaches.get(username)
        if coach and password == coach.get("password"):
            st.session_state.coach_authed = True
            st.session_state.coach_team_slug = coach["team_slug"]
            st.session_state.coach_team_name = coach.get("team_name", coach["team_slug"])
            st.rerun()
        else:
            st.error("Onjuiste gebruikersnaam of wachtwoord.")
    st.stop()

TEAM_SLUG = st.session_state.coach_team_slug
TEAM_NAME = st.session_state.coach_team_name


_navbar_html = """
<style>
/* Verberg Streamlit's eigen header/menu voor een clean look */
#MainMenu {visibility: hidden;}
header {visibility: hidden;}

.top-navbar {
    display: flex;
    align-items: center;
    background-color: #12172c;
    padding: 1rem 2rem;
    margin: -1rem -1rem 1.5rem -1rem;
}
.navbar-logo {
    font-family: Arial, sans-serif;
    font-weight: 800;
    font-size: 1.1rem;
    color: white;
    line-height: 1.1;
    letter-spacing: 0.02em;
}
.navbar-logo .sub {
    display: block;
    font-size: 0.55rem;
    font-weight: 600;
    letter-spacing: 0.15em;
    color: #ffffff;
    margin-top: 0.1rem;
}
.navbar-logo .ball-icon {
    display: inline-block;
    vertical-align: top;
    margin-left: 0.2rem;
    margin-top: -0.15rem;
}
.page-title {
    font-size: 1.75rem;
    font-weight: 700;
    color: white;
    margin-bottom: 0.25rem;
    line-height: 1.3;
}
.page-subtitle {
    font-size: 0.95rem;
    color: #94a3b8;
    margin-bottom: 1.5rem;
}
@media (max-width: 640px) {
    .top-navbar { padding: 0.85rem 1.25rem; }
    .page-title { font-size: 1.35rem; }
    .page-subtitle { font-size: 0.85rem; }
}
</style>

<div class="top-navbar">
    <div class="navbar-logo">KICK<svg class="ball-icon" viewBox="0 0 24 24" width="18" height="18" xmlns="http://www.w3.org/2000/svg"><circle cx="12" cy="12" r="10" stroke="#ffffff" stroke-width="1.4" fill="none"/><path d="M12 6.2l3.2 2.3-1.2 3.8h-4l-1.2-3.8L12 6.2z" fill="#ffffff"/><path d="M12 2.5V6.2M5.3 7.9L2.2 6M18.7 7.9l3.1-1.9M8.8 12.3L4.4 15.7M15.2 12.3l4.4 3.4M9.1 16.3l6-.1.9 3.6M9.1 16.3l-1 3.6" stroke="#ffffff" stroke-width="1.1" stroke-linecap="round" stroke-linejoin="round"/></svg><span class="sub">COMPETITION</span></div>
</div>

<div class="page-title">__TEAM_NAME__ — 1e Testmoment</div>
<div class="page-subtitle">Overzicht van alle prestatiegegevens van het team</div>
"""
st.markdown(_navbar_html.replace("__TEAM_NAME__", TEAM_NAME), unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Styling — dark navy background met witte kaarten, zoals in de mockups
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    .stApp { background-color: #12172c; }
    .block-container { padding-top: 2rem; padding-bottom: 2rem; max-width: 1300px; }

    .dash-title { color: #ffffff; font-size: 1.6rem; font-weight: 700; margin-bottom: 0.1rem; }
    .dash-subtitle { color: #9aa3c4; font-size: 0.95rem; margin-bottom: 1rem; }

    .white-card { background-color: #ffffff; border-radius: 14px; padding: 1.5rem 1.75rem; margin-bottom: 1.5rem; }
    .metric-card { background-color: #ffffff; border-radius: 14px; padding: 1.1rem 1.3rem; margin-bottom: 1.5rem; height: 100%; }

    .metric-label { color: #6b7280; font-size: 0.82rem; font-weight: 500; }
    .metric-value { color: #111827; font-size: 1.6rem; font-weight: 700; margin-top: 0.15rem; }
    .metric-value.green { color: #16a34a; }
    .metric-value.red { color: #dc2626; }
    .metric-sub { color: #9ca3af; font-size: 0.78rem; margin-top: 0.1rem; }
    .metric-sub.green { color: #16a34a; }
    .metric-sub.red { color: #dc2626; }

    .badge-pill { display: inline-block; background-color: #1f2547; color: #cdd3f0; border-radius: 999px;
                  padding: 0.35rem 0.9rem; font-size: 0.85rem; margin-bottom: 0.5rem; }

    .card-title { color: #111827; font-size: 1.05rem; font-weight: 700; }
    .card-subtitle { color: #9ca3af; font-size: 0.8rem; margin-bottom: 1rem; }

    .stat-row { margin-bottom: 0.85rem; }
    .stat-label-row { display: flex; justify-content: space-between; font-size: 0.85rem; color: #374151; margin-bottom: 0.25rem; }
    .stat-bar-bg { background-color: #e5e7eb; border-radius: 999px; height: 7px; width: 100%; }
    .stat-bar-fill { border-radius: 999px; height: 7px; }

    .note-box { background-color: #eff6ff; border-radius: 10px; padding: 0.9rem 1rem; font-size: 0.82rem; color: #374151; margin-top: 1rem; }
    .quad-box { border-radius: 10px; padding: 0.7rem 0.9rem; font-size: 0.78rem; margin-bottom: 0.5rem; }
    .quad-title { font-weight: 700; font-size: 0.8rem; margin-bottom: 0.1rem; }

    div[data-testid="stCheckbox"] label p { color: #ffffff !important; }
    .white-card div[data-testid="stCheckbox"] label p { color: #374151 !important; }

    /* --- Mobiel: alle st.columns() onder elkaar i.p.v. naast elkaar --- */
    @media (max-width: 640px) {
        div[data-testid="stHorizontalBlock"] {
            flex-direction: column !important;
        }
        div[data-testid="stHorizontalBlock"] > div {
            width: 100% !important;
            min-width: 100% !important;
        }
        .block-container { padding-left: 1rem; padding-right: 1rem; }
        .white-card, .metric-card { padding: 1.1rem 1.2rem; }
        .dash-title { font-size: 1.3rem; }
        .card-title { font-size: 0.95rem; }
        .metric-value { font-size: 1.35rem; }
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
@st.cache_data
def load_data(team_slug):
    raw = pd.read_csv(team_players_path(team_slug))
    clean, missing_required, _unused = normalize_players_df(raw)

    if missing_required:
        st.error(
            "Deze verwachte kolommen zijn niet gevonden in de data van dit team: "
            f"{missing_required}. Gevonden kolommen in het bestand: {raw.columns.tolist()}"
        )
        st.stop()

    return clean

df = load_data(TEAM_SLUG)

POSITION_COLORS = {
    "Attacker": "#ef4444",
    "Midfielder": "#3b82f6",
    "Defender": "#22c55e",
    "Goalkeeper": "#f97316",
}
POSITION_LABELS_NL = {
    "Attacker": "Aanvaller",
    "Midfielder": "Middenvelder",
    "Defender": "Verdediger",
    "Goalkeeper": "Doelman",
}

# (min, max, invert) -> invert=True betekent: lager is beter
# De index-score wordt bepaald ten opzichte van de eigen spelersgroep, niet
# tegenover een vaste externe norm: min/max hieronder komen uit df zelf, dus
# de beste speler van dit team scoort 100 en de zwakste 0 op elk onderdeel.
def _team_relative_bounds(column, invert):
    lo = float(df[column].min())
    hi = float(df[column].max())
    if hi == lo:
        # Iedereen heeft hier exact dezelfde waarde: geen spreiding, dus
        # iedereen krijgt een neutrale middenscore i.p.v. delen door nul.
        hi = lo + 1.0
    return (lo, hi, invert)

RANGES = {
    "agility": _team_relative_bounds("agility_zonder_bal_s", True),          # seconden, lager = beter
    "acceleratie": _team_relative_bounds("acceleratie_kmh", False),          # km/h
    "max_snelheid": _team_relative_bounds("max_snelheid_kmh", False),        # km/h
    "sprong": _team_relative_bounds("sprong_cm", False),                     # cm
    "uithoudingsvermogen": _team_relative_bounds("afstand_m", False),        # meters
}

def normalize(value, lo, hi, invert=False):
    pct = (value - lo) / (hi - lo) * 100
    if invert:
        pct = 100 - pct
    return float(np.clip(pct, 0, 100))

def player_scores(row):
    return {
        "Agility": normalize(row["agility_zonder_bal_s"], *RANGES["agility"][:2], invert=RANGES["agility"][2]),
        "Acceleratie": normalize(row["acceleratie_kmh"], *RANGES["acceleratie"][:2]),
        "Max Snelheid": normalize(row["max_snelheid_kmh"], *RANGES["max_snelheid"][:2]),
        "Sprong": normalize(row["sprong_cm"], *RANGES["sprong"][:2]),
        "Uithoud-vermogen": normalize(row["afstand_m"], *RANGES["uithoudingsvermogen"][:2]),
    }

all_scores = [player_scores(r) for _, r in df.iterrows()]
categories = list(all_scores[0].keys())
team_scores = {cat: float(np.mean([s[cat] for s in all_scores])) for cat in categories}

# =============================================================================
# SECTIE 1 — PRESTATIE-INDEX (CLIENT-SIDE, MET ECHTE SMOOTH TRANSITIE)
# =============================================================================
st.markdown('<div class="dash-title">Prestatie-Index</div>', unsafe_allow_html=True)
st.markdown('<div class="dash-subtitle">Index-score per vaardigheid (0-100) — vergelijk met het teamgemiddelde en/of een andere speler</div>', unsafe_allow_html=True)

STAT_COLORS = {
    "Agility": "#22c55e",
    "Acceleratie": "#3b82f6",
    "Max Snelheid": "#a855f7",
    "Sprong": "#f97316",
    "Uithoud-vermogen": "#ef4444",
}
STAT_LABELS = {
    "Agility": "Agility",
    "Acceleratie": "Acceleratie",
    "Max Snelheid": "Max. Snelheid",
    "Sprong": "Sprong",
    "Uithoud-vermogen": "Uithoudingsvermogen",
}

players_data = {}
for _, row in df.iterrows():
    name = row["naam"]
    s = player_scores(row)
    players_data[name] = {
        "positie": row["positie"],
        "scores": s,
        "raw": {
            "Agility": f'{row["agility_zonder_bal_s"]:.1f}s',
            "Acceleratie": f'{row["acceleratie_kmh"]:.1f} km/h',
            "Max Snelheid": f'{row["max_snelheid_kmh"]:.1f} km/h',
            "Sprong": f'{row["sprong_cm"]:.0f} cm',
            "Uithoud-vermogen": f'{row["afstand_m"]:.0f} m',
        },
    }

default_name = df["naam"].iloc[0]

PLAYERS_JSON = json.dumps(players_data, ensure_ascii=False)
TEAM_JSON = json.dumps(team_scores, ensure_ascii=False)
CATEGORIES_JSON = json.dumps(categories, ensure_ascii=False)
STAT_COLORS_JSON = json.dumps(STAT_COLORS, ensure_ascii=False)
STAT_LABELS_JSON = json.dumps(STAT_LABELS, ensure_ascii=False)
DEFAULT_NAME_JSON = json.dumps(default_name, ensure_ascii=False)
PLAYER_NAMES_JSON = json.dumps(sorted(players_data.keys()), ensure_ascii=False)
LABEL_OPTIONS_JSON = json.dumps(
    [f'{n} - {players_data[n]["positie"]}' for n in sorted(players_data.keys())],
    ensure_ascii=False,
)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
    * { box-sizing: border-box; }
    body {
        margin: 0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
        background: transparent;
    }
    .card {
        background: #ffffff;
        border-radius: 14px;
        padding: 1.5rem 1.75rem;
    }
    .top-row {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 1rem;
        flex-wrap: wrap;
        gap: 1rem;
    }
    .sel-label {
        font-weight: 600;
        font-size: 0.9rem;
        color: #111827;
        margin-bottom: 0.4rem;
        display: block;
    }
    select {
        width: 100%;
        max-width: 420px;
        padding: 0.55rem 0.75rem;
        border-radius: 8px;
        border: 1px solid #d1d5db;
        font-size: 0.9rem;
        color: #111827;
        background: #ffffff;
    }
    .toggle-wrap {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        white-space: nowrap;
        padding-top: 1.6rem;
    }
    .toggle-wrap label {
        font-size: 0.9rem;
        color: #111827;
    }
    .content-row {
        display: flex;
        gap: 2rem;
        flex-wrap: wrap;
    }
    .chart-col {
        flex: 2;
        min-width: 320px;
    }
    .info-col {
        flex: 1;
        min-width: 260px;
    }
    .legend {
        display: flex;
        gap: 1.5rem;
        justify-content: center;
        font-size: 0.85rem;
        color: #374151;
        margin-top: 0.25rem;
    }
    .legend span.dot {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 2px;
        margin-right: 6px;
    }
    .card-title {
        color: #111827;
        font-size: 1.05rem;
        font-weight: 700;
    }
    .card-subtitle {
        color: #9ca3af;
        font-size: 0.8rem;
        margin-bottom: 1rem;
    }
    .stat-row { margin-bottom: 0.85rem; }
    .stat-label-row {
        display: flex;
        justify-content: space-between;
        font-size: 0.85rem;
        color: #374151;
        margin-bottom: 0.25rem;
    }
    .stat-bar-bg {
        background-color: #e5e7eb;
        border-radius: 999px;
        height: 7px;
        width: 100%;
        position: relative;
    }
    .stat-bar-fill {
        border-radius: 999px;
        height: 7px;
        transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .stat-bar-avg-marker {
        position: absolute;
        top: -1px;
        bottom: -1px;
        width: 2px;
        margin-left: -1px;
        background-color: rgba(75, 85, 99, 0.55);
        border-radius: 1px;
        box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.5);
        cursor: pointer;
    }
    .stat-bar-avg-marker::after {
        content: attr(data-tooltip);
        position: absolute;
        bottom: 100%;
        left: 50%;
        transform: translateX(-50%) translateY(4px);
        margin-bottom: 6px;
        background-color: #111827;
        color: #ffffff;
        font-size: 0.7rem;
        font-weight: 600;
        padding: 0.3rem 0.55rem;
        border-radius: 6px;
        white-space: nowrap;
        opacity: 0;
        pointer-events: none;
        transition: opacity 0.15s ease, transform 0.15s ease;
        z-index: 10;
    }
    .stat-bar-avg-marker:hover::after {
        opacity: 1;
        transform: translateX(-50%) translateY(0);
    }
    .note-box {
        background-color: #eff6ff;
        border-radius: 10px;
        padding: 0.9rem 1rem;
        font-size: 0.82rem;
        color: #374151;
        margin-top: 1rem;
    }

    /* --- Mobiel: alles onder elkaar, kleinere marges --- */
    @media (max-width: 640px) {
        .card { padding: 1.1rem 1.1rem; }
        .top-row { flex-direction: column; align-items: stretch; gap: 0.75rem; }
        .toggle-wrap { padding-top: 0; }
        select { max-width: 100%; }
        .content-row { flex-direction: column; gap: 1.25rem; }
        .chart-col, .info-col { min-width: 100%; flex: 1 1 100%; }
        #spiderChart { height: 340px !important; }
    }
</style>
</head>
<body>
    <div class="card">
        <div class="top-row">
            <div style="flex:1; min-width:220px;">
                <span class="sel-label">Selecteer Speler</span>
                <select id="playerSelect"></select>
            </div>
            <div style="flex:1; min-width:220px;">
                <span class="sel-label">Vergelijk met (optioneel)</span>
                <select id="compareSelect"></select>
            </div>
            <div class="toggle-wrap">
                <input type="checkbox" id="teamToggle" checked />
                <label for="teamToggle">Toon Team Gemiddelde</label>
            </div>
        </div>

        <div class="content-row">
            <div class="chart-col">
                <div id="spiderChart" style="width:100%; height:420px;"></div>
                <div class="legend" id="legendBox"></div>
            </div>
            <div class="info-col">
                <div class="card-title" id="playerName"></div>
                <div class="card-subtitle" id="playerPos"></div>
                <div id="statBars"></div>
                <div style="font-size:0.75rem; color:#6b7280; margin-top:-0.4rem; margin-bottom:0.75rem;">
                    <span style="display:inline-block; width:2px; height:10px; background-color:rgba(75,85,99,0.55); vertical-align:middle; margin-right:5px;"></span>
                    = team gemiddelde
                </div>
                <div class="note-box">
                    <b>Indexscore</b><br>
                    Een score die laat zien hoe een speler presteert ten opzichte van de gekozen
                    referentiegroep. Referentiegroep = de spelers van dit team: 100 is de beste van de
                    groep op dat onderdeel, 0 de zwakste.
                </div>
            </div>
        </div>
    </div>

<script>
    var PLAYERS = __PLAYERS_JSON__;
    var TEAM = __TEAM_JSON__;
    var CATEGORIES = __CATEGORIES_JSON__;
    var STAT_COLORS = __STAT_COLORS_JSON__;
    var STAT_LABELS = __STAT_LABELS_JSON__;
    var DEFAULT_NAME = __DEFAULT_NAME_JSON__;
    var PLAYER_NAMES = __PLAYER_NAMES_JSON__;
    var LABEL_OPTIONS = __LABEL_OPTIONS_JSON__;

    var selectEl = document.getElementById("playerSelect");
    var compareSelectEl = document.getElementById("compareSelect");
    var toggleEl = document.getElementById("teamToggle");

    PLAYER_NAMES.forEach(function (name, i) {
        var opt = document.createElement("option");
        opt.value = name;
        opt.textContent = LABEL_OPTIONS[i];
        if (name === DEFAULT_NAME) opt.selected = true;
        selectEl.appendChild(opt);
    });

    var noCompareOpt = document.createElement("option");
    noCompareOpt.value = "";
    noCompareOpt.textContent = "Geen vergelijking";
    compareSelectEl.appendChild(noCompareOpt);

    PLAYER_NAMES.forEach(function (name, i) {
        var opt = document.createElement("option");
        opt.value = name;
        opt.textContent = LABEL_OPTIONS[i];
        compareSelectEl.appendChild(opt);
    });

    function isMobile() {
        return window.innerWidth <= 640;
    }

    function getBaseLayout() {
        var mobile = isMobile();
        return {
            polar: {
                radialaxis: { visible: true, range: [0, 100], gridcolor: "#e5e7eb" },
            },
            showlegend: false,
            margin: mobile
                ? { l: 30, r: 30, t: 10, b: 10 }
                : { l: 40, r: 40, t: 20, b: 20 },
            height: mobile ? 340 : 420,
            paper_bgcolor: "white",
            plot_bgcolor: "white",
        };
    }
    var baseLayout = getBaseLayout();

    var chartInitialized = false;
    var animRunning = false;

    // Plotly's ingebouwde `transition` werkt niet betrouwbaar voor scatterpolar
    // (radar) traces. Daarom animeren we hier zelf: we interpoleren de r-waarden
    // stap voor stap en pushen die via Plotly.restyle() naar de grafiek.
    function easeInOutCubic(t) {
        return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
    }

    function animateToTraces(newTraces) {
        var gd = document.getElementById("spiderChart");
        var currentData = gd.data || [];

        // Als het aantal traces verschilt (bv. team-gemiddelde aan/uit gezet),
        // kunnen we niet zinvol interpoleren: direct hertekenen.
        if (currentData.length !== newTraces.length) {
            Plotly.react("spiderChart", newTraces, baseLayout, { displayModeBar: false, responsive: true });
            return;
        }

        var startR = currentData.map(function (tr) { return tr.r.slice(); });
        var endR = newTraces.map(function (tr) { return tr.r.slice(); });

        var duration = 600;
        var startTime = null;
        animRunning = true;

        function step(timestamp) {
            if (!startTime) startTime = timestamp;
            var elapsed = timestamp - startTime;
            var t = Math.min(elapsed / duration, 1);
            var eased = easeInOutCubic(t);

            var interpR = startR.map(function (arr, i) {
                return arr.map(function (v, j) {
                    return v + (endR[i][j] - v) * eased;
                });
            });

            Plotly.restyle("spiderChart", { r: interpR });

            if (t < 1) {
                requestAnimationFrame(step);
            } else {
                animRunning = false;
                // Zet na de animatie de volledige trace-config (namen, kleuren, hover)
                // definitief vast, voor het geval die ook gewijzigd zijn.
                Plotly.react("spiderChart", newTraces, baseLayout, { displayModeBar: false, responsive: true });
            }
        }
        requestAnimationFrame(step);
    }

    function buildTraces(name, compareName, showTeam) {
        var p = PLAYERS[name];
        var scoreArr = CATEGORIES.map(function (c) { return p.scores[c]; });
        scoreArr.push(scoreArr[0]);
        var thetaArr = CATEGORIES.concat([CATEGORIES[0]]);

        var traces = [];
        if (showTeam) {
            var teamArr = CATEGORIES.map(function (c) { return TEAM[c]; });
            teamArr.push(teamArr[0]);
            traces.push({
                type: "scatterpolar",
                r: teamArr,
                theta: thetaArr,
                fill: "toself",
                name: "Team Gemiddelde",
                line: { color: "#3b82f6" },
                fillcolor: "rgba(59,130,246,0.15)",
            });
        }
        if (compareName && compareName !== name && PLAYERS[compareName]) {
            var cp = PLAYERS[compareName];
            var compareArr = CATEGORIES.map(function (c) { return cp.scores[c]; });
            compareArr.push(compareArr[0]);
            traces.push({
                type: "scatterpolar",
                r: compareArr,
                theta: thetaArr,
                fill: "toself",
                name: compareName,
                line: { color: "#8b5cf6" },
                fillcolor: "rgba(139,92,246,0.15)",
            });
        }
        traces.push({
            type: "scatterpolar",
            r: scoreArr,
            theta: thetaArr,
            fill: "toself",
            name: name,
            line: { color: "#14b8a6" },
            fillcolor: "rgba(20,184,166,0.35)",
        });
        return traces;
    }

    function updateLegend(name, compareName, showTeam) {
        var html = "";
        if (showTeam) {
            html += '<div><span class="dot" style="background:#3b82f6;"></span>Team Gemiddelde</div>';
        }
        if (compareName && compareName !== name && PLAYERS[compareName]) {
            html += '<div><span class="dot" style="background:#8b5cf6;"></span>' + compareName + "</div>";
        }
        html += '<div><span class="dot" style="background:#14b8a6;"></span>' + name + "</div>";
        document.getElementById("legendBox").innerHTML = html;
    }

    function safeId(cat) {
        return cat.replace(/[^a-zA-Z0-9]/g, "");
    }

    // Bouwt de statbalken-structuur precies één keer op. Daarna wordt bij elke
    // spelerwissel alleen de breedte/waarde van de bestáánde elementen aangepast
    // (i.p.v. de HTML te vervangen), zodat de CSS-transitie op .stat-bar-fill
    // daadwerkelijk kan animeren.
    function initStatBars() {
        var barsHtml = "";
        CATEGORIES.forEach(function (cat) {
            var label = STAT_LABELS[cat];
            var color = STAT_COLORS[cat];
            var id = safeId(cat);
            var avgPct = TEAM[cat];
            barsHtml += (
                '<div class="stat-row">' +
                '<div class="stat-label-row"><span>' + label + '</span><span id="statval-' + id + '"></span></div>' +
                '<div class="stat-bar-bg">' +
                '<div class="stat-bar-fill" id="statfill-' + id + '" style="width:0%; background-color:' + color + ';"></div>' +
                '<div class="stat-bar-avg-marker" style="left:' + avgPct + '%;" data-tooltip="Team gemiddelde: ' + Math.round(avgPct) + '"></div>' +
                '</div>' +
                "</div>"
            );
        });
        document.getElementById("statBars").innerHTML = barsHtml;
    }

    function updateInfoPanel(name) {
        var p = PLAYERS[name];
        document.getElementById("playerName").textContent = name;
        document.getElementById("playerPos").textContent = p.positie;

        CATEGORIES.forEach(function (cat) {
            var id = safeId(cat);
            var valEl = document.getElementById("statval-" + id);
            var fillEl = document.getElementById("statfill-" + id);
            if (valEl) valEl.textContent = p.raw[cat];
            if (fillEl) fillEl.style.width = p.scores[cat] + "%";
        });
    }

    function renderChart(name, compareName) {
        var showTeam = toggleEl.checked;
        var traces = buildTraces(name, compareName, showTeam);

        if (!chartInitialized) {
            Plotly.newPlot("spiderChart", traces, baseLayout, { displayModeBar: false, responsive: true });
            chartInitialized = true;
        } else {
            animateToTraces(traces);
        }
        updateLegend(name, compareName, showTeam);
        updateInfoPanel(name);

        if (typeof resizeFrame === "function") {
            setTimeout(resizeFrame, 50);
        }
    }

    selectEl.addEventListener("change", function () {
        renderChart(selectEl.value, compareSelectEl.value);
    });
    compareSelectEl.addEventListener("change", function () {
        renderChart(selectEl.value, compareSelectEl.value);
    });
    toggleEl.addEventListener("change", function () {
        renderChart(selectEl.value, compareSelectEl.value);
    });

    initStatBars();
    renderChart(DEFAULT_NAME, "");

    // --- Iframe-hoogte automatisch laten meebewegen met de inhoud ---
    // Gebruikt Streamlit's officiële resize-protocol (postMessage), zodat niet
    // alleen de iframe zelf, maar ook de door Streamlit gereserveerde ruimte
    // eromheen wordt aangepast — anders blijft er witruimte over.
    function resizeFrame() {
        var height = document.body.scrollHeight;
        window.parent.postMessage({ type: "streamlit:setFrameHeight", height: height }, "*");
    }
    setTimeout(resizeFrame, 150);
    window.addEventListener("load", resizeFrame);

    // --- Bij resize/rotatie: layout herberekenen en iframe-hoogte updaten ---
    var resizeTimer = null;
    window.addEventListener("resize", function () {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(function () {
            baseLayout = getBaseLayout();
            Plotly.relayout("spiderChart", baseLayout);
            Plotly.Plots.resize("spiderChart");
            resizeFrame();
        }, 150);
    });
</script>
</body>
</html>
"""

html_out = (
    HTML_TEMPLATE
    .replace("__PLAYERS_JSON__", PLAYERS_JSON)
    .replace("__TEAM_JSON__", TEAM_JSON)
    .replace("__CATEGORIES_JSON__", CATEGORIES_JSON)
    .replace("__STAT_COLORS_JSON__", STAT_COLORS_JSON)
    .replace("__STAT_LABELS_JSON__", STAT_LABELS_JSON)
    .replace("__DEFAULT_NAME_JSON__", DEFAULT_NAME_JSON)
    .replace("__PLAYER_NAMES_JSON__", PLAYER_NAMES_JSON)
    .replace("__LABEL_OPTIONS_JSON__", LABEL_OPTIONS_JSON)
)

# height is enkel een startwaarde; de JS in de component corrigeert dit
# direct automatisch naar de werkelijke inhoud (zowel op desktop als mobiel)
components.html(html_out, height=600, scrolling=False)

# =============================================================================
# SECTIE 2 — AGILITY ANALYSE
# =============================================================================
st.markdown('<div class="dash-title">Agility Analyse</div>', unsafe_allow_html=True)
st.markdown('<div class="dash-subtitle">Wendbaarheid en balcontrole van spelers</div>', unsafe_allow_html=True)
st.markdown('<div class="badge-pill">Test: Illinois Agility Test (met en zonder bal)</div>', unsafe_allow_html=True)

avg_zonder = df["agility_zonder_bal_s"].mean()
avg_met = df["agility_met_bal_s"].mean()
best_row = df.loc[df["agility_zonder_bal_s"].idxmin()]
worst_row = df.loc[df["agility_zonder_bal_s"].idxmax()]

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Gem. Agility Zonder Bal</div>
        <div class="metric-value">{avg_zonder:.2f}s</div>
        <div class="metric-sub">Team gemiddelde</div>
    </div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Gem. Agility Met Bal</div>
        <div class="metric-value">{avg_met:.2f}s</div>
        <div class="metric-sub">Team gemiddelde</div>
    </div>""", unsafe_allow_html=True)
with c3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">&#8599; Beste Speler</div>
        <div class="metric-value green">{best_row['naam']}</div>
        <div class="metric-sub green">{best_row['agility_zonder_bal_s']:.2f}s</div>
    </div>""", unsafe_allow_html=True)
with c4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">&#8600; Zwakste Speler</div>
        <div class="metric-value red">{worst_row['naam']}</div>
        <div class="metric-sub red">{worst_row['agility_zonder_bal_s']:.2f}s</div>
    </div>""", unsafe_allow_html=True)


# --- Agility per speler (bar chart) ---
sorted_df = df.sort_values("agility_zonder_bal_s")
colors = [POSITION_COLORS.get(p, "#6b7280") for p in sorted_df["positie"]]

present_positions = [p for p in POSITION_COLORS if p in df["positie"].unique()]
position_legend = [
    {"label": POSITION_LABELS_NL.get(p, p), "color": POSITION_COLORS[p]}
    for p in present_positions
]

BAR_NAMES_JSON = json.dumps(sorted_df["naam"].tolist(), ensure_ascii=False)
BAR_VALUES_JSON = json.dumps([float(v) for v in sorted_df["agility_zonder_bal_s"]], ensure_ascii=False)
BAR_COLORS_JSON = json.dumps(colors, ensure_ascii=False)
AVG_ZONDER_JSON = json.dumps(float(avg_zonder), ensure_ascii=False)
POSITION_LEGEND_JSON = json.dumps(position_legend, ensure_ascii=False)

BAR_HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
* { box-sizing: border-box; }
body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif; background: transparent; }
.card { background: #ffffff; border-radius: 14px; padding: 1.5rem 1.75rem; }
.top-row { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem; flex-wrap: wrap; gap: 0.75rem; }
.card-title { color: #111827; font-size: 1.05rem; font-weight: 700; }
.card-subtitle { color: #9ca3af; font-size: 0.8rem; }
.toggle-wrap { display: flex; align-items: center; gap: 0.5rem; white-space: nowrap; }
.toggle-wrap label { font-size: 0.9rem; color: #111827; }
.legend { display: flex; gap: 1.5rem; justify-content: center; font-size: 0.85rem; color: #374151; margin-top: 0.75rem; flex-wrap: wrap; }
.legend span.dot { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 6px; }
@media (max-width: 640px) {
    .card { padding: 1.1rem 1.1rem; }
    .top-row { flex-direction: column; align-items: stretch; }
}
</style>
</head>
<body>
<div class="card">
    <div class="top-row">
        <div>
            <div class="card-title">Agility per Speler</div>
            <div class="card-subtitle">Gesorteerd op prestatie (lager is beter)</div>
        </div>
        <div class="toggle-wrap">
            <input type="checkbox" id="refToggle" checked />
            <label for="refToggle">Team gemiddelde</label>
        </div>
    </div>
    <div id="barChart" style="width:100%; height:430px;"></div>
    <div class="legend" id="legendBox"></div>
</div>

<script>
var NAMES = __BAR_NAMES_JSON__;
var VALUES = __BAR_VALUES_JSON__;
var COLORS = __BAR_COLORS_JSON__;
var AVG = __AVG_ZONDER_JSON__;
var POSITION_LEGEND = __POSITION_LEGEND_JSON__;

var refToggle = document.getElementById("refToggle");

var legendHtml = "";
POSITION_LEGEND.forEach(function (item) {
    legendHtml += '<div><span class="dot" style="background:' + item.color + ';"></span>' + item.label + "</div>";
});
document.getElementById("legendBox").innerHTML = legendHtml;

function easeInOutCubic(t) {
    return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
}

var layout = {
    xaxis: { title: "Agility (seconden)", automargin: true },
    yaxis: { title: null, autorange: "reversed", automargin: true },
    height: 430,
    margin: { l: 10, r: 20, t: 10, b: 30 },
    paper_bgcolor: "white",
    plot_bgcolor: "white",
    shapes: [{
        type: "line",
        x0: AVG, x1: AVG,
        y0: 0, y1: 1,
        yref: "paper",
        line: { color: "#9ca3af", width: 1.5, dash: "dash" },
        opacity: 1,
    }],
    annotations: [{
        x: AVG, y: 1, yref: "paper", yanchor: "bottom",
        text: "Team gem.: " + AVG.toFixed(2) + "s",
        showarrow: false,
        font: { size: 11, color: "#6b7280" },
        opacity: 1,
    }],
};

Plotly.newPlot("barChart", [{
    type: "bar",
    orientation: "h",
    x: VALUES,
    y: NAMES,
    marker: { color: COLORS },
}], layout, { displayModeBar: false, responsive: true });

var currentOpacity = 1;

function animateLineOpacity(target) {
    var start = currentOpacity;
    var duration = 400;
    var startTime = null;

    function step(ts) {
        if (!startTime) startTime = ts;
        var t = Math.min((ts - startTime) / duration, 1);
        var eased = easeInOutCubic(t);
        var val = start + (target - start) * eased;
        Plotly.relayout("barChart", { "shapes[0].opacity": val, "annotations[0].opacity": val });
        if (t < 1) {
            requestAnimationFrame(step);
        } else {
            currentOpacity = target;
        }
    }
    requestAnimationFrame(step);
}

refToggle.addEventListener("change", function () {
    animateLineOpacity(refToggle.checked ? 1 : 0);
});

function resizeFrame() {
    var height = document.body.scrollHeight;
    window.parent.postMessage({ type: "streamlit:setFrameHeight", height: height }, "*");
}
setTimeout(resizeFrame, 150);
window.addEventListener("load", resizeFrame);

var resizeTimer = null;
window.addEventListener("resize", function () {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function () {
        Plotly.Plots.resize("barChart");
        resizeFrame();
    }, 150);
});
</script>
</body>
</html>
"""

bar_html_out = (
    BAR_HTML_TEMPLATE
    .replace("__BAR_NAMES_JSON__", BAR_NAMES_JSON)
    .replace("__BAR_VALUES_JSON__", BAR_VALUES_JSON)
    .replace("__BAR_COLORS_JSON__", BAR_COLORS_JSON)
    .replace("__AVG_ZONDER_JSON__", AVG_ZONDER_JSON)
    .replace("__POSITION_LEGEND_JSON__", POSITION_LEGEND_JSON)
)
components.html(bar_html_out, height=610, scrolling=False)

# =============================================================================
# SECTIE 3 — SPRINT ANALYSE
# =============================================================================
st.markdown('<div class="dash-title">Sprint Analyse</div>', unsafe_allow_html=True)
st.markdown('<div class="dash-subtitle">Acceleratie en topsnelheid metingen</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="badge-pill">Test: 30m Sprint (acceleratie + topsnelheid)</div>',
    unsafe_allow_html=True,
)

# NB: er is geen aparte "Totaal"-kolom in de brondata. "Totaal" hieronder is
# het gemiddelde van acceleratie_kmh en max_snelheid_kmh. Pas dit aan zodra
# er een specifieke totaalscore-kolom beschikbaar is.
avg_accel = float(df["acceleratie_kmh"].mean())
avg_top = float(df["max_snelheid_kmh"].mean())
df["totaal_snelheid"] = (df["acceleratie_kmh"] + df["max_snelheid_kmh"]) / 2
avg_totaal = float(df["totaal_snelheid"].mean())

best_accel_row = df.loc[df["acceleratie_kmh"].idxmax()]
best_top_row = df.loc[df["max_snelheid_kmh"].idxmax()]

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Gem. Acceleration Speed</div>
        <div class="metric-value">{avg_accel:.1f} km/h</div>
        <div class="metric-sub">Team gemiddelde</div>
    </div>""", unsafe_allow_html=True)
with m2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Gem. Topsnelheid</div>
        <div class="metric-value">{avg_top:.1f} km/h</div>
        <div class="metric-sub">Team gemiddelde</div>
    </div>""", unsafe_allow_html=True)
with m3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">&#9889; Explosiefste Speler</div>
        <div class="metric-value">{best_accel_row['naam']}</div>
        <div class="metric-sub" style="color:#3b82f6;">{best_accel_row['acceleratie_kmh']:.1f} km/h</div>
    </div>""", unsafe_allow_html=True)
with m4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">&#127942; Snelste Speler</div>
        <div class="metric-value">{best_top_row['naam']}</div>
        <div class="metric-sub green">{best_top_row['max_snelheid_kmh']:.1f} km/h</div>
    </div>""", unsafe_allow_html=True)

col_sprint_scatter, col_sprint_bar = st.columns(2)

# --- Acceleratie vs Topsnelheid (scatter) ---
with col_sprint_scatter:
    SPRINT_SCATTER_TRACES = []
    for pos, color in POSITION_COLORS.items():
        sub = df[df["positie"] == pos]
        if sub.empty:
            continue
        SPRINT_SCATTER_TRACES.append({
            "type": "scatter",
            "mode": "markers",
            "name": pos,
            "x": sub["acceleratie_kmh"].tolist(),
            "y": sub["max_snelheid_kmh"].tolist(),
            "text": sub["naam"].tolist(),
            "marker": {"color": color, "size": 10},
            "hovertemplate": "%{text}<extra></extra>",
        })

    SPRINT_SCATTER_JSON = json.dumps(SPRINT_SCATTER_TRACES, ensure_ascii=False)

    SPRINT_SCATTER_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
    * { box-sizing: border-box; }
    body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif; background: transparent; }
    .card { background: #ffffff; border-radius: 14px; padding: 1.5rem 1.75rem; }
    .card-title { color: #111827; font-size: 1.05rem; font-weight: 700; }
    .card-subtitle { color: #9ca3af; font-size: 0.8rem; margin-bottom: 1rem; }
    @media (max-width: 640px) {
        .card { padding: 1.1rem 1.1rem; }
    }
</style>
</head>
<body>
    <div class="card">
        <div class="card-title">Acceleratie vs Topsnelheid</div>
        <div class="card-subtitle">Sprinttijden analyse</div>
        <div id="sprintScatter" style="width:100%; height:380px;"></div>
    </div>

<script>
    var TRACES = __SPRINT_SCATTER_JSON__;

    var layout = {
        xaxis: { title: "Acceleratie (km/h)", automargin: true },
        yaxis: { title: "Topsnelheid (km/h)", automargin: true },
        height: 380,
        margin: { l: 10, r: 10, t: 10, b: 10 },
        legend: { orientation: "h", yanchor: "bottom", y: -0.35 },
        paper_bgcolor: "white",
        plot_bgcolor: "white",
    };

    Plotly.newPlot("sprintScatter", TRACES, layout, { displayModeBar: false, responsive: true });

    function resizeFrame() {
        var height = document.body.scrollHeight;
        window.parent.postMessage({ type: "streamlit:setFrameHeight", height: height }, "*");
    }
    setTimeout(resizeFrame, 150);
    window.addEventListener("load", resizeFrame);

    var resizeTimer = null;
    window.addEventListener("resize", function () {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(function () {
            Plotly.Plots.resize("sprintScatter");
            resizeFrame();
        }, 150);
    });
</script>
</body>
</html>
"""

    sprint_scatter_out = SPRINT_SCATTER_TEMPLATE.replace("__SPRINT_SCATTER_JSON__", SPRINT_SCATTER_JSON)
    components.html(sprint_scatter_out, height=470, scrolling=False)

# --- Acceleratie / Topsnelheid / Totaal (tabbed bar chart) ---
with col_sprint_bar:
    def build_tab(metric_col, avg_val):
        sorted_df = df.sort_values(metric_col, ascending=False)
        return {
            "names": sorted_df["naam"].tolist(),
            "values": [float(v) for v in sorted_df[metric_col]],
            "colors": [POSITION_COLORS.get(p, "#6b7280") for p in sorted_df["positie"]],
            "avg": avg_val,
        }

    TAB_DATA = {
        "Acceleratie": build_tab("acceleratie_kmh", avg_accel),
        "Topsnelheid": build_tab("max_snelheid_kmh", avg_top),
        "Totaal": build_tab("totaal_snelheid", avg_totaal),
    }
    TAB_DATA_JSON = json.dumps(TAB_DATA, ensure_ascii=False)

    SPRINT_BAR_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
    * { box-sizing: border-box; }
    body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif; background: transparent; }
    .card { background: #ffffff; border-radius: 14px; padding: 1.5rem 1.75rem; }
    .top-row { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem; flex-wrap: wrap; gap: 0.75rem; }
    .card-title { color: #111827; font-size: 1.05rem; font-weight: 700; }
    .card-subtitle { color: #9ca3af; font-size: 0.8rem; }
    .toggle-wrap { display: flex; align-items: center; gap: 0.5rem; white-space: nowrap; }
    .toggle-wrap label { font-size: 0.9rem; color: #111827; }
    .tab-row { display: flex; gap: 0.5rem; margin: 0.75rem 0 1rem 0; flex-wrap: wrap; }
    .tab-btn {
        border: none; border-radius: 8px; padding: 0.4rem 0.9rem;
        font-size: 0.85rem; font-weight: 600; cursor: pointer;
        background: #f1f5f9; color: #475569;
    }
    .tab-btn.active { background: #4f46e5; color: #ffffff; }
    @media (max-width: 640px) {
        .card { padding: 1.1rem 1.1rem; }
        .top-row { flex-direction: column; align-items: stretch; }
    }
</style>
</head>
<body>
    <div class="card">
        <div class="top-row">
            <div>
                <div class="card-title" id="chartTitle">Acceleratie (0-10m)</div>
                <div class="card-subtitle">Per speler</div>
            </div>
            <div class="toggle-wrap">
                <input type="checkbox" id="refToggle" checked />
                <label for="refToggle">Referentielijn</label>
            </div>
        </div>
        <div class="tab-row" id="tabRow"></div>
        <div id="sprintBarChart" style="width:100%; height:430px;"></div>
    </div>

<script>
    var TAB_DATA = __TAB_DATA_JSON__;
    var TAB_TITLES = {
        "Acceleratie": "Acceleratie (0-10m)",
        "Topsnelheid": "Topsnelheid",
        "Totaal": "Totaal (gemiddelde)",
    };
    var TAB_KEYS = ["Acceleratie", "Topsnelheid", "Totaal"];
    var currentTab = "Acceleratie";
    var currentOpacity = 1;

    var refToggle = document.getElementById("refToggle");
    var tabRow = document.getElementById("tabRow");
    var chartTitle = document.getElementById("chartTitle");

    TAB_KEYS.forEach(function (key) {
        var btn = document.createElement("button");
        btn.className = "tab-btn" + (key === currentTab ? " active" : "");
        btn.textContent = key;
        btn.dataset.key = key;
        btn.addEventListener("click", function () {
            if (currentTab === key) return;
            currentTab = key;
            Array.prototype.forEach.call(tabRow.children, function (el) {
                el.classList.toggle("active", el.dataset.key === key);
            });
            chartTitle.textContent = TAB_TITLES[key];
            renderBar();
        });
        tabRow.appendChild(btn);
    });

    function easeInOutCubic(t) {
        return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
    }

    var baseLayout = {
        xaxis: { title: null, automargin: true },
        yaxis: { title: null, autorange: "reversed", automargin: true },
        height: 430,
        margin: { l: 10, r: 20, t: 10, b: 30 },
        paper_bgcolor: "white",
        plot_bgcolor: "white",
        transition: { duration: 500, easing: "cubic-in-out" },
    };

    function renderBar() {
        var d = TAB_DATA[currentTab];
        var shape = {
            type: "line",
            x0: d.avg, x1: d.avg,
            y0: 0, y1: 1, yref: "paper",
            line: { color: "#ef4444", width: 1.5, dash: "dash" },
            opacity: currentOpacity,
        };
        var layout = Object.assign({}, baseLayout, { shapes: [shape] });
        Plotly.react("sprintBarChart", [{
            type: "bar",
            orientation: "h",
            x: d.values,
            y: d.names,
            marker: { color: d.colors },
        }], layout, { displayModeBar: false, responsive: true });
        resizeFrame();
    }

    function animateLineOpacity(target) {
        var start = currentOpacity;
        var duration = 400;
        var startTime = null;
        function step(ts) {
            if (!startTime) startTime = ts;
            var t = Math.min((ts - startTime) / duration, 1);
            var eased = easeInOutCubic(t);
            var val = start + (target - start) * eased;
            Plotly.relayout("sprintBarChart", { "shapes[0].opacity": val });
            if (t < 1) {
                requestAnimationFrame(step);
            } else {
                currentOpacity = target;
            }
        }
        requestAnimationFrame(step);
    }

    refToggle.addEventListener("change", function () {
        animateLineOpacity(refToggle.checked ? 1 : 0);
    });

    function resizeFrame() {
        var height = document.body.scrollHeight;
        window.parent.postMessage({ type: "streamlit:setFrameHeight", height: height }, "*");
    }

    renderBar();
    setTimeout(resizeFrame, 150);
    window.addEventListener("load", resizeFrame);

    var resizeTimer = null;
    window.addEventListener("resize", function () {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(function () {
            Plotly.Plots.resize("sprintBarChart");
            resizeFrame();
        }, 150);
    });
</script>
</body>
</html>
"""

    sprint_bar_out = SPRINT_BAR_TEMPLATE.replace("__TAB_DATA_JSON__", TAB_DATA_JSON)
    components.html(sprint_bar_out, height=650, scrolling=False)

# =============================================================================
# SECTIE 4 — SPRONG ANALYSE
# =============================================================================
st.markdown('<div class="dash-title">Sprong Analyse</div>', unsafe_allow_html=True)
st.markdown('<div class="dash-subtitle">Verticale sprong en explosieve kracht</div>', unsafe_allow_html=True)
st.markdown('<div class="badge-pill">Test: Vertical Jump Test</div>', unsafe_allow_html=True)

# NB: "Norm" hieronder is een aanname (25 cm), afgestemd op de schaal van de
# huidige pilot-data. Pas dit aan zodra er een officiële norm-waarde bekend is.
NORM_CM = 25
avg_sprong = float(df["sprong_cm"].mean())
best_sprong_row = df.loc[df["sprong_cm"].idxmax()]
aantal_onder_norm = int((df["sprong_cm"] < NORM_CM).sum())
pct_onder_norm = float((df["sprong_cm"] < NORM_CM).mean() * 100)

j1, j2, j3 = st.columns(3)
with j1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Gem. Vertical Jump</div>
        <div class="metric-value">{avg_sprong:.0f} cm</div>
        <div class="metric-sub">Team gemiddelde</div>
    </div>""", unsafe_allow_html=True)
with j2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">&#127942; Beste Sprong</div>
        <div class="metric-value">{best_sprong_row['naam']}</div>
        <div class="metric-sub green">{best_sprong_row['sprong_cm']:.0f} cm</div>
    </div>""", unsafe_allow_html=True)
with j3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">&#128200; % Spelers Onder Norm</div>
        <div class="metric-value">{pct_onder_norm:.0f}%</div>
        <div class="metric-sub">{aantal_onder_norm} van {len(df)} spelers (norm: {NORM_CM}cm)</div>
    </div>""", unsafe_allow_html=True)

# --- Verticale Sprong per Speler (bar chart, kleur o.b.v. Explosive Power) ---
if "power_watt" in df.columns:
    power_tier = pd.qcut(df["power_watt"], q=3, labels=["Lage Power", "Gemiddelde Power", "Hoge Power"])
else:
    power_tier = pd.Series(["Gemiddelde Power"] * len(df), index=df.index)

TIER_COLORS = {
    "Lage Power": "#ef4444",
    "Gemiddelde Power": "#f59e0b",
    "Hoge Power": "#22c55e",
}

jump_df = df.copy()
jump_df["power_tier"] = power_tier
jump_df = jump_df.sort_values("sprong_cm", ascending=False)

JUMP_NAMES_JSON = json.dumps(jump_df["naam"].tolist(), ensure_ascii=False)
JUMP_VALUES_JSON = json.dumps([float(v) for v in jump_df["sprong_cm"]], ensure_ascii=False)
JUMP_COLORS_JSON = json.dumps(
    [TIER_COLORS.get(t, "#6b7280") for t in jump_df["power_tier"]], ensure_ascii=False
)
AVG_SPRONG_JSON = json.dumps(avg_sprong, ensure_ascii=False)

JUMP_HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
    * { box-sizing: border-box; }
    body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif; background: transparent; }
    .card { background: #ffffff; border-radius: 14px; padding: 1.5rem 1.75rem; }
    .top-row { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem; flex-wrap: wrap; gap: 0.75rem; }
    .card-title { color: #111827; font-size: 1.05rem; font-weight: 700; }
    .card-subtitle { color: #9ca3af; font-size: 0.8rem; }
    .toggle-wrap { display: flex; align-items: center; gap: 0.5rem; white-space: nowrap; }
    .toggle-wrap label { font-size: 0.9rem; color: #111827; }
    .legend { display: flex; gap: 1.5rem; justify-content: center; font-size: 0.85rem; color: #374151; margin-top: 0.75rem; flex-wrap: wrap; }
    .legend span.dot { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 6px; }
    @media (max-width: 640px) {
        .card { padding: 1.1rem 1.1rem; }
        .top-row { flex-direction: column; align-items: stretch; }
    }
</style>
</head>
<body>
    <div class="card">
        <div class="top-row">
            <div>
                <div class="card-title">Verticale Sprong per Speler</div>
                <div class="card-subtitle">Kleur gebaseerd op explosieve kracht</div>
            </div>
            <div class="toggle-wrap">
                <input type="checkbox" id="avgToggle" checked />
                <label for="avgToggle">Team Gemiddelde</label>
            </div>
        </div>
        <div id="jumpChart" style="width:100%; height:480px;"></div>
        <div class="legend">
            <div><span class="dot" style="background:#ef4444;"></span>Lage Power</div>
            <div><span class="dot" style="background:#f59e0b;"></span>Gemiddelde Power</div>
            <div><span class="dot" style="background:#22c55e;"></span>Hoge Power</div>
        </div>
    </div>

<script>
    var NAMES = __JUMP_NAMES_JSON__;
    var VALUES = __JUMP_VALUES_JSON__;
    var COLORS = __JUMP_COLORS_JSON__;
    var AVG = __AVG_SPRONG_JSON__;

    var avgToggle = document.getElementById("avgToggle");
    var currentOpacity = 1;

    function easeInOutCubic(t) {
        return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
    }

    var layout = {
        xaxis: { title: null, automargin: true, ticksuffix: " cm" },
        yaxis: { title: null, autorange: "reversed", automargin: true },
        height: 480,
        margin: { l: 10, r: 20, t: 10, b: 30 },
        paper_bgcolor: "white",
        plot_bgcolor: "white",
        shapes: [{
            type: "line",
            x0: AVG, x1: AVG,
            y0: 0, y1: 1, yref: "paper",
            line: { color: "#6366f1", width: 1.5, dash: "dash" },
            opacity: 1,
        }],
        annotations: [{
            x: AVG, y: 1, yref: "paper", yanchor: "bottom",
            text: "Gem.", showarrow: false,
            font: { size: 11, color: "#6366f1" },
        }],
    };

    Plotly.newPlot("jumpChart", [{
        type: "bar",
        orientation: "h",
        x: VALUES,
        y: NAMES,
        marker: { color: COLORS },
    }], layout, { displayModeBar: false, responsive: true });

    function animateLineOpacity(target) {
        var start = currentOpacity;
        var duration = 400;
        var startTime = null;
        function step(ts) {
            if (!startTime) startTime = ts;
            var t = Math.min((ts - startTime) / duration, 1);
            var eased = easeInOutCubic(t);
            var val = start + (target - start) * eased;
            Plotly.relayout("jumpChart", { "shapes[0].opacity": val });
            if (t < 1) {
                requestAnimationFrame(step);
            } else {
                currentOpacity = target;
            }
        }
        requestAnimationFrame(step);
    }

    avgToggle.addEventListener("change", function () {
        animateLineOpacity(avgToggle.checked ? 1 : 0);
    });

    function resizeFrame() {
        var height = document.body.scrollHeight;
        window.parent.postMessage({ type: "streamlit:setFrameHeight", height: height }, "*");
    }
    setTimeout(resizeFrame, 150);
    window.addEventListener("load", resizeFrame);

    var resizeTimer = null;
    window.addEventListener("resize", function () {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(function () {
            Plotly.Plots.resize("jumpChart");
            resizeFrame();
        }, 150);
    });
</script>
</body>
</html>
"""

jump_html_out = (
    JUMP_HTML_TEMPLATE
    .replace("__JUMP_NAMES_JSON__", JUMP_NAMES_JSON)
    .replace("__JUMP_VALUES_JSON__", JUMP_VALUES_JSON)
    .replace("__JUMP_COLORS_JSON__", JUMP_COLORS_JSON)
    .replace("__AVG_SPRONG_JSON__", AVG_SPRONG_JSON)
)
components.html(jump_html_out, height=620, scrolling=False)

# =============================================================================
# SECTIE 5 — UITHOUDINGSVERMOGEN
# =============================================================================
st.markdown('<div class="dash-title">Uithoudingsvermogen</div>', unsafe_allow_html=True)
st.markdown('<div class="dash-subtitle">Afgelegde afstand tijdens wedstrijd/training</div>', unsafe_allow_html=True)
st.markdown('<div class="badge-pill">Test: Yo-Yo Intermittent Recovery Test Level 1</div>', unsafe_allow_html=True)

# NB: de brondata (afstand_m) ligt op een schaal van ~250-2300 meter.
# REFERENTIE_M hieronder is een PLACEHOLDER-waarde (geen echte professionele
# norm) — pas dit aan zodra je de juiste referentiewaarde hebt.
REFERENTIE_M = 2000.0
avg_afstand_m = float(df["afstand_m"].mean())
best_afstand_row = df.loc[df["afstand_m"].idxmax()]

u1, u2, u3 = st.columns(3)
with u1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">&#128202; Gem. Afgelegde Afstand</div>
        <div class="metric-value">{avg_afstand_m / 1000:.2f} km</div>
        <div class="metric-sub">Team gemiddelde</div>
    </div>""", unsafe_allow_html=True)
with u2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Beste Prestatie</div>
        <div class="metric-value">{best_afstand_row['afstand_m'] / 1000:.2f} km</div>
        <div class="metric-sub green">{best_afstand_row['naam']}</div>
    </div>""", unsafe_allow_html=True)
with u3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Referentiewaarde</div>
        <div class="metric-value">{REFERENTIE_M / 1000:.2f} km</div>
        <div class="metric-sub">Professioneel niveau</div>
    </div>""", unsafe_allow_html=True)

# --- Stamina per Speler (bar chart, kleur t.o.v. teamgemiddelde) ---
def stamina_kleur(value, avg):
    diff_pct = (value - avg) / avg * 100
    if diff_pct <= -5:
        return "#ef4444"
    elif diff_pct >= 5:
        return "#22c55e"
    return "#f59e0b"

stamina_df = df.copy()
stamina_df["stamina_kleur"] = stamina_df["afstand_m"].apply(lambda v: stamina_kleur(v, avg_afstand_m))
stamina_df = stamina_df.sort_values("afstand_m", ascending=False)

STAMINA_NAMES_JSON = json.dumps(stamina_df["naam"].tolist(), ensure_ascii=False)
STAMINA_VALUES_JSON = json.dumps([float(v) / 1000 for v in stamina_df["afstand_m"]], ensure_ascii=False)
STAMINA_COLORS_JSON = json.dumps(stamina_df["stamina_kleur"].tolist(), ensure_ascii=False)
AVG_AFSTAND_KM_JSON = json.dumps(avg_afstand_m / 1000, ensure_ascii=False)
REFERENTIE_KM_JSON = json.dumps(REFERENTIE_M / 1000, ensure_ascii=False)

STAMINA_HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
    * { box-sizing: border-box; }
    body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif; background: transparent; }
    .card { background: #ffffff; border-radius: 14px; padding: 1.5rem 1.75rem; }
    .top-row { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem; flex-wrap: wrap; gap: 0.75rem; }
    .card-title { color: #111827; font-size: 1.05rem; font-weight: 700; }
    .card-subtitle { color: #9ca3af; font-size: 0.8rem; }
    .tab-row { display: flex; gap: 0.5rem; flex-wrap: wrap; }
    .tab-btn {
        border: none; border-radius: 8px; padding: 0.4rem 0.9rem;
        font-size: 0.85rem; font-weight: 600; cursor: pointer;
        background: #f1f5f9; color: #475569;
    }
    .tab-btn.active { background: #4f46e5; color: #ffffff; }
    .legend { display: flex; gap: 1.5rem; justify-content: center; font-size: 0.85rem; color: #374151; margin-top: 0.75rem; flex-wrap: wrap; }
    .legend span.dot { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 6px; }
    @media (max-width: 640px) {
        .card { padding: 1.1rem 1.1rem; }
        .top-row { flex-direction: column; align-items: stretch; }
    }
</style>
</head>
<body>
    <div class="card">
        <div class="top-row">
            <div>
                <div class="card-title">Stamina per Speler</div>
                <div class="card-subtitle">Kleuren tonen prestatie t.o.v. teamgemiddelde</div>
            </div>
            <div class="tab-row" id="refTabRow">
                <button class="tab-btn active" data-mode="team">Teamgemiddelde</button>
                <button class="tab-btn" data-mode="ref">Referentiewaarde</button>
            </div>
        </div>
        <div id="staminaChart" style="width:100%; height:480px;"></div>
        <div class="legend">
            <div><span class="dot" style="background:#ef4444;"></span>Onder gemiddelde (&le;-5%)</div>
            <div><span class="dot" style="background:#f59e0b;"></span>Rond gemiddelde (&plusmn;5%)</div>
            <div><span class="dot" style="background:#22c55e;"></span>Boven gemiddelde (&ge;+5%)</div>
        </div>
    </div>

<script>
    var NAMES = __STAMINA_NAMES_JSON__;
    var VALUES = __STAMINA_VALUES_JSON__;
    var COLORS = __STAMINA_COLORS_JSON__;
    var AVG_KM = __AVG_AFSTAND_KM_JSON__;
    var REF_KM = __REFERENTIE_KM_JSON__;

    var refTabRow = document.getElementById("refTabRow");
    var currentX = AVG_KM;
    var currentMode = "team";

    function easeInOutCubic(t) {
        return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
    }

    var baseLayout = {
        xaxis: { title: null, automargin: true, ticksuffix: " km" },
        yaxis: { title: null, autorange: "reversed", automargin: true },
        height: 480,
        margin: { l: 10, r: 20, t: 10, b: 30 },
        paper_bgcolor: "white",
        plot_bgcolor: "white",
    };

    function makeShape(xVal, label) {
        return {
            shapes: [{
                type: "line",
                x0: xVal, x1: xVal,
                y0: 0, y1: 1, yref: "paper",
                line: { color: "#4f46e5", width: 1.5, dash: "dash" },
            }],
            annotations: [{
                x: xVal, y: 1, yref: "paper", yanchor: "bottom",
                text: label, showarrow: false,
                font: { size: 11, color: "#4f46e5" },
            }],
        };
    }

    Plotly.newPlot("staminaChart", [{
        type: "bar",
        orientation: "h",
        x: VALUES,
        y: NAMES,
        marker: { color: COLORS },
    }], Object.assign({}, baseLayout, makeShape(AVG_KM, "Team")), { displayModeBar: false, responsive: true });

    function animateLineTo(targetX, label) {
        var startX = currentX;
        var duration = 450;
        var startTime = null;

        function step(ts) {
            if (!startTime) startTime = ts;
            var t = Math.min((ts - startTime) / duration, 1);
            var eased = easeInOutCubic(t);
            var val = startX + (targetX - startX) * eased;
            Plotly.relayout("staminaChart", {
                "shapes[0].x0": val,
                "shapes[0].x1": val,
                "annotations[0].x": val,
                "annotations[0].text": label,
            });
            if (t < 1) {
                requestAnimationFrame(step);
            } else {
                currentX = targetX;
            }
        }
        requestAnimationFrame(step);
    }

    Array.prototype.forEach.call(refTabRow.children, function (btn) {
        btn.addEventListener("click", function () {
            var mode = btn.dataset.mode;
            if (mode === currentMode) return;
            currentMode = mode;
            Array.prototype.forEach.call(refTabRow.children, function (el) {
                el.classList.toggle("active", el.dataset.mode === mode);
            });
            if (mode === "team") {
                animateLineTo(AVG_KM, "Team");
            } else {
                animateLineTo(REF_KM, "Ref.");
            }
        });
    });

    function resizeFrame() {
        var height = document.body.scrollHeight;
        window.parent.postMessage({ type: "streamlit:setFrameHeight", height: height }, "*");
    }
    setTimeout(resizeFrame, 150);
    window.addEventListener("load", resizeFrame);

    var resizeTimer = null;
    window.addEventListener("resize", function () {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(function () {
            Plotly.Plots.resize("staminaChart");
            resizeFrame();
        }, 150);
    });
</script>
</body>
</html>
"""

stamina_html_out = (
    STAMINA_HTML_TEMPLATE
    .replace("__STAMINA_NAMES_JSON__", STAMINA_NAMES_JSON)
    .replace("__STAMINA_VALUES_JSON__", STAMINA_VALUES_JSON)
    .replace("__STAMINA_COLORS_JSON__", STAMINA_COLORS_JSON)
    .replace("__AVG_AFSTAND_KM_JSON__", AVG_AFSTAND_KM_JSON)
    .replace("__REFERENTIE_KM_JSON__", REFERENTIE_KM_JSON)
)
components.html(stamina_html_out, height=620, scrolling=False)
