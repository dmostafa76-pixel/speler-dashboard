import json
import time
import uuid
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from data_utils import (
    normalize_players_df,
    team_players_path,
    classify_topend_benchmark,
    TOPEND_BENCHMARK_ORDER,
    TOPEND_BENCHMARK_COLORS,
)

st.set_page_config(page_title="Speler Prestatie Dashboard", layout="wide")

# ---------------------------------------------------------------------------
# Coach-login: elke coach heeft een eigen account dat gekoppeld is aan één
# team. Accounts staan in Streamlit secrets (zie SETUP_TEAMS.md) — dat is
# de enige plek waar coach-toegang wordt beheerd, coaches kunnen zichzelf
# niet registreren.
#
# Eén account = maximaal één actieve sessie tegelijk. Dit wordt bijgehouden
# in een gedeeld geheugen (st.cache_resource, gedeeld door alle sessies
# binnen deze draaiende app) i.p.v. st.session_state, dat juist per apparaat
# apart is. Een sessie die 15 minuten niets doet, wordt automatisch als
# "verlaten" beschouwd en geeft het account weer vrij.
# ---------------------------------------------------------------------------
SESSION_TIMEOUT_SECONDS = 15 * 60


@st.cache_resource
def get_active_coach_sessions():
    return {}  # gebruikersnaam -> {"token": str, "last_seen": float}


active_sessions = get_active_coach_sessions()

# Het sessie-ID wordt ook in de URL bewaard (?s=...), zodat een refresh van
# dezelfde tab herkend wordt als dezelfde sessie i.p.v. als een "nieuw
# apparaat" — anders zou een simpele pagina-herlaad jezelf per ongeluk
# buitensluiten.
if "session_token" not in st.session_state:
    bestaand_token = st.query_params.get("s")
    if bestaand_token:
        st.session_state.session_token = bestaand_token
    else:
        st.session_state.session_token = str(uuid.uuid4())
        st.query_params["s"] = st.session_state.session_token

if "coach_authed" not in st.session_state:
    st.session_state.coach_authed = False

if not st.session_state.coach_authed:
    st.markdown("## Inloggen")
    username = st.text_input("Gebruikersnaam")
    password = st.text_input("Wachtwoord", type="password")
    if st.button("Inloggen"):
        coaches = st.secrets.get("coaches", {})
        coach = coaches.get(username)
        if not coach or password != coach.get("password"):
            st.error("Onjuiste gebruikersnaam of wachtwoord.")
        else:
            now = time.time()
            existing = active_sessions.get(username)
            elders_actief = (
                existing is not None
                and existing["token"] != st.session_state.session_token
                and (now - existing["last_seen"]) < SESSION_TIMEOUT_SECONDS
            )
            if elders_actief:
                st.error(
                    "Dit account is al actief ingelogd op een ander apparaat. "
                    "Log daar eerst uit, of probeer het over een paar minuten opnieuw."
                )
            else:
                active_sessions[username] = {"token": st.session_state.session_token, "last_seen": now}
                st.session_state.coach_authed = True
                st.session_state.coach_username = username
                st.session_state.coach_team_slug = coach["team_slug"]
                st.session_state.coach_team_name = coach.get("team_name", coach["team_slug"])
                st.rerun()
    st.stop()

# Iemand anders kan intussen (na een timeout) met hetzelfde account zijn
# ingelogd — in dat geval verliest deze sessie de vergrendeling en moet
# opnieuw worden ingelogd i.p.v. door te blijven werken.
_username = st.session_state.coach_username
_current = active_sessions.get(_username)
if _current is None or _current["token"] != st.session_state.session_token:
    st.session_state.coach_authed = False
    st.warning("Je bent uitgelogd omdat dit account op een ander apparaat actief is geworden.")
    st.stop()
active_sessions[_username]["last_seen"] = time.time()

TEAM_SLUG = st.session_state.coach_team_slug
TEAM_NAME = st.session_state.coach_team_name

if st.button("Uitloggen", key="logout_button"):
    active_sessions.pop(_username, None)
    st.session_state.coach_authed = False
    st.rerun()


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
    display: flex;
    align-items: center;
}
.navbar-logo-img {
    height: 32px;
    width: auto;
    display: block;
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
    .navbar-logo-img { height: 26px; }
    .page-title { font-size: 1.35rem; }
    .page-subtitle { font-size: 0.85rem; }
}
</style>

<div class="top-navbar">
    <div class="navbar-logo"><img src="data:image/png;base64,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" alt="KICK Competition" class="navbar-logo-img" /></div>
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
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap');

    html, body, .stApp, [class*="css"] { font-family: 'Poppins', sans-serif !important; }

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

# invert=True betekent: lager is beter (bv. agility-tijd), dus het teken van
# de z-score wordt omgedraaid zodat "verder naar buiten" altijd "beter"
# betekent, ongeacht het onderdeel.
def _team_mean_std(column, invert):
    mean = float(df[column].mean())
    std = float(df[column].std(ddof=0))
    return (mean, std, invert)

TEAM_STATS = {
    "agility": _team_mean_std("agility_zonder_bal_s", True),          # seconden, lager = beter
    "acceleratie": _team_mean_std("acceleratie_kmh", False),          # km/h
    "max_snelheid": _team_mean_std("max_snelheid_kmh", False),        # km/h
    "sprong": _team_mean_std("sprong_cm", False),                     # cm
    "uithoudingsvermogen": _team_mean_std("afstand_m", False),        # meters
}

def zscore(value, mean, std, invert=False):
    z = 0.0 if std == 0 else (value - mean) / std
    if invert:
        z = -z
    return float(z)

def player_scores(row):
    return {
        "Agility": zscore(row["agility_zonder_bal_s"], *TEAM_STATS["agility"][:2], invert=TEAM_STATS["agility"][2]),
        "Acceleratie": zscore(row["acceleratie_kmh"], *TEAM_STATS["acceleratie"][:2]),
        "Max Snelheid": zscore(row["max_snelheid_kmh"], *TEAM_STATS["max_snelheid"][:2]),
        "Sprong": zscore(row["sprong_cm"], *TEAM_STATS["sprong"][:2]),
        "Uithoud-vermogen": zscore(row["afstand_m"], *TEAM_STATS["uithoudingsvermogen"][:2]),
    }

# De statbalken rechts van de spider chart gebruiken bewust géén z-score:
# die zou voor een team met weinig spreiding alle balken even (kort) maken.
# In plaats daarvan een 0-100 index t.o.v. de eigen spelersgroep (beste van
# het team = 100, zwakste = 0), zodat de balken de volle breedte benutten.
#
# Zonder marge staat de zwakste speler van het team altijd op exact 0% —
# zijn balk is dan onzichtbaar, ongeacht hoe zwak hij precies is. Door de
# boven- en ondergrens wat op te rekken (8% van de spreiding) krijgt ook de
# zwakste (en sterkste) speler een klein, maar zichtbaar stukje balk.
def _index_bounds(column, invert):
    lo = float(df[column].min())
    hi = float(df[column].max())
    if hi == lo:
        hi = lo + 1.0
    padding = (hi - lo) * 0.08
    return (lo - padding, hi + padding, invert)

INDEX_RANGES = {
    "agility": _index_bounds("agility_zonder_bal_s", True),
    "acceleratie": _index_bounds("acceleratie_kmh", False),
    "max_snelheid": _index_bounds("max_snelheid_kmh", False),
    "sprong": _index_bounds("sprong_cm", False),
    "uithoudingsvermogen": _index_bounds("afstand_m", False),
}

def index_normalize(value, lo, hi, invert=False):
    pct = (value - lo) / (hi - lo) * 100
    if invert:
        pct = 100 - pct
    return float(np.clip(pct, 0, 100))

def player_index_scores(row):
    return {
        "Agility": index_normalize(row["agility_zonder_bal_s"], *INDEX_RANGES["agility"][:2], invert=INDEX_RANGES["agility"][2]),
        "Acceleratie": index_normalize(row["acceleratie_kmh"], *INDEX_RANGES["acceleratie"][:2]),
        "Max Snelheid": index_normalize(row["max_snelheid_kmh"], *INDEX_RANGES["max_snelheid"][:2]),
        "Sprong": index_normalize(row["sprong_cm"], *INDEX_RANGES["sprong"][:2]),
        "Uithoud-vermogen": index_normalize(row["afstand_m"], *INDEX_RANGES["uithoudingsvermogen"][:2]),
    }

all_scores = [player_scores(r) for _, r in df.iterrows()]
categories = list(all_scores[0].keys())
team_scores = {cat: float(np.mean([s[cat] for s in all_scores])) for cat in categories}

all_index_scores = [player_index_scores(r) for _, r in df.iterrows()]
team_index_scores = {cat: float(np.mean([s[cat] for s in all_index_scores])) for cat in categories}

# Tekst voor de "Team gemiddelde"-tooltip op de statbalken: de echte,
# ongeschaalde gemiddelde meetwaarde in de eigen eenheid — geen index- of
# z-score-getal.
team_avg_text = {
    "Agility": f'{TEAM_STATS["agility"][0]:.1f}s',
    "Acceleratie": f'{TEAM_STATS["acceleratie"][0]:.1f} km/h',
    "Max Snelheid": f'{TEAM_STATS["max_snelheid"][0]:.1f} km/h',
    "Sprong": f'{TEAM_STATS["sprong"][0]:.0f} cm',
    "Uithoud-vermogen": f'{TEAM_STATS["uithoudingsvermogen"][0]:.0f} m',
}

# =============================================================================
# SECTIE 1 — PRESTATIE-INDEX (CLIENT-SIDE, MET ECHTE SMOOTH TRANSITIE)
# =============================================================================
st.markdown('<div class="dash-title">Prestatie Z-Score</div>', unsafe_allow_html=True)
st.markdown('<div class="dash-subtitle">Afwijking t.o.v. het teamgemiddelde, in standaarddeviaties — vergelijk met het teamgemiddelde en/of een andere speler</div>', unsafe_allow_html=True)

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
    idx = player_index_scores(row)
    players_data[name] = {
        "positie": row["positie"],
        "scores": s,
        "index_scores": idx,
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
TEAM_INDEX_JSON = json.dumps(team_index_scores, ensure_ascii=False)
TEAM_AVG_TEXT_JSON = json.dumps(team_avg_text, ensure_ascii=False)
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
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap');
    * { box-sizing: border-box; }
    body {
        margin: 0;
        font-family: 'Poppins', sans-serif;
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
                    <b>Z-score</b><br>
                    Hoeveel standaarddeviaties een speler van het teamgemiddelde afwijkt.
                    0 = gemiddeld, +2 = sterk boven, &minus;2 = sterk onder het gemiddelde van dit team.
                </div>
            </div>
        </div>
    </div>

<script>
    var PLAYERS = __PLAYERS_JSON__;
    var TEAM = __TEAM_JSON__;
    var TEAM_INDEX = __TEAM_INDEX_JSON__;
    var TEAM_AVG_TEXT = __TEAM_AVG_TEXT_JSON__;
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
                radialaxis: {
                    visible: true,
                    range: [-2.5, 2.5],
                    tickvals: [-2, -1, 0, 1, 2],
                    gridcolor: "#e5e7eb",
                },
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

    // Plotly's radiale as loopt van -2.5 tot +2.5; extreme uitschieters
    // (bv. bij een heel kleine spreiding) worden hierop afgeklemd zodat de
    // chart bruikbaar blijft. De echte, ongeklemde z-score blijft gewoon
    // zichtbaar in het infopaneel rechts.
    function clampZ(z) {
        return Math.max(-2.5, Math.min(2.5, z));
    }

    function buildTraces(name, compareName, showTeam) {
        var p = PLAYERS[name];
        var scoreArr = CATEGORIES.map(function (c) { return clampZ(p.scores[c]); });
        scoreArr.push(scoreArr[0]);
        var thetaArr = CATEGORIES.concat([CATEGORIES[0]]);

        var traces = [];
        if (showTeam) {
            var teamArr = CATEGORIES.map(function (c) { return clampZ(TEAM[c]); });
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
            var compareArr = CATEGORIES.map(function (c) { return clampZ(cp.scores[c]); });
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
            var avgPct = TEAM_INDEX[cat];
            barsHtml += (
                '<div class="stat-row">' +
                '<div class="stat-label-row"><span>' + label + '</span><span id="statval-' + id + '"></span></div>' +
                '<div class="stat-bar-bg">' +
                '<div class="stat-bar-fill" id="statfill-' + id + '" style="width:0%; background-color:' + color + ';"></div>' +
                '<div class="stat-bar-avg-marker" style="left:' + avgPct + '%;" data-tooltip="Team gemiddelde: ' + TEAM_AVG_TEXT[cat] + '"></div>' +
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
            if (fillEl) fillEl.style.width = p.index_scores[cat] + "%";
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
    .replace("__TEAM_INDEX_JSON__", TEAM_INDEX_JSON)
    .replace("__TEAM_AVG_TEXT_JSON__", TEAM_AVG_TEXT_JSON)
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
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap');
* { box-sizing: border-box; }
body { margin: 0; font-family: 'Poppins', sans-serif; background: transparent; }
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
    margin: { l: 10, r: 20, t: 30, b: 30 },
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

avg_accel = float(df["acceleratie_kmh"].mean())
avg_top = float(df["max_snelheid_kmh"].mean())

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
        <div class="metric-label">&#9889; Meest Explosieve Speler</div>
        <div class="metric-value">{best_accel_row['naam']}</div>
        <div class="metric-sub" style="color:#3b82f6; font-size:1.05rem; font-weight:700;">{best_accel_row['acceleratie_kmh']:.1f} km/h</div>
    </div>""", unsafe_allow_html=True)
with m4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">&#127942; Snelste Speler</div>
        <div class="metric-value">{best_top_row['naam']}</div>
        <div class="metric-sub green" style="font-size:1.05rem; font-weight:700;">{best_top_row['max_snelheid_kmh']:.1f} km/h</div>
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
            "name": POSITION_LABELS_NL.get(pos, pos),
            "x": sub["acceleratie_kmh"].tolist(),
            "y": sub["max_snelheid_kmh"].tolist(),
            "text": sub["naam"].tolist(),
            "marker": {"color": color, "size": 10},
            "hovertemplate": "%{text} (%{x:.1f} km/h, %{y:.1f} km/h)<extra></extra>",
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
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap');
    * { box-sizing: border-box; }
    body { margin: 0; font-family: 'Poppins', sans-serif; background: transparent; }
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
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap');
    * { box-sizing: border-box; }
    body { margin: 0; font-family: 'Poppins', sans-serif; background: transparent; }
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
                <div class="card-title" id="chartTitle">Acceleratie (0-10m)</div>
                <div class="card-subtitle">Per speler</div>
            </div>
            <div class="toggle-wrap">
                <input type="checkbox" id="refToggle" checked />
                <label for="refToggle">Team gemiddelde</label>
            </div>
        </div>
        <div class="tab-row" id="tabRow"></div>
        <div id="sprintBarChart" style="width:100%; height:430px;"></div>
        <div class="legend" id="legendBox"></div>
    </div>

<script>
    var TAB_DATA = __TAB_DATA_JSON__;
    var POSITION_LEGEND = __POSITION_LEGEND_JSON__;
    var TAB_TITLES = {
        "Acceleratie": "Acceleratie (0-10m)",
        "Topsnelheid": "Topsnelheid",
    };
    var AXIS_LABELS = {
        "Acceleratie": "Acceleratie (km/h)",
        "Topsnelheid": "Topsnelheid (km/h)",
    };
    var TAB_KEYS = ["Acceleratie", "Topsnelheid"];
    var currentTab = "Acceleratie";
    var currentOpacity = 1;

    var refToggle = document.getElementById("refToggle");
    var tabRow = document.getElementById("tabRow");
    var chartTitle = document.getElementById("chartTitle");

    var legendHtml = "";
    POSITION_LEGEND.forEach(function (item) {
        legendHtml += '<div><span class="dot" style="background:' + item.color + ';"></span>' + item.label + "</div>";
    });
    document.getElementById("legendBox").innerHTML = legendHtml;

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
        yaxis: { title: null, autorange: "reversed", automargin: true },
        height: 430,
        margin: { l: 10, r: 20, t: 30, b: 30 },
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
        var annotation = {
            x: d.avg, y: 1, yref: "paper", yanchor: "bottom",
            text: "Team gem.: " + d.avg.toFixed(1) + " km/h",
            showarrow: false,
            font: { size: 11, color: "#ef4444" },
            opacity: currentOpacity,
        };
        var layout = Object.assign({}, baseLayout, {
            shapes: [shape],
            annotations: [annotation],
            xaxis: { title: AXIS_LABELS[currentTab], automargin: true },
        });
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
            Plotly.relayout("sprintBarChart", { "shapes[0].opacity": val, "annotations[0].opacity": val });
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

    sprint_bar_out = (
        SPRINT_BAR_TEMPLATE
        .replace("__TAB_DATA_JSON__", TAB_DATA_JSON)
        .replace("__POSITION_LEGEND_JSON__", POSITION_LEGEND_JSON)
    )
    components.html(sprint_bar_out, height=690, scrolling=False)

# =============================================================================
# SECTIE 4 — SPRONG ANALYSE
# =============================================================================
st.markdown('<div class="dash-title">Sprong Analyse</div>', unsafe_allow_html=True)
st.markdown('<div class="dash-subtitle">Verticale sprong en explosieve kracht</div>', unsafe_allow_html=True)
st.markdown('<div class="badge-pill">Test: Vertical Jump Test</div>', unsafe_allow_html=True)

avg_sprong = float(df["sprong_cm"].mean())
best_sprong_row = df.loc[df["sprong_cm"].idxmax()]

j1, j2 = st.columns(2)
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

# --- Verticale Sprong per Speler (bar chart, kleur o.b.v. Explosive Power) ---
if "power_watt" in df.columns:
    power_tier = pd.qcut(df["power_watt"], q=3, labels=["Lage Explosieve Power", "Gemiddelde Explosieve Power", "Hoge Explosieve Power"])
else:
    power_tier = pd.Series(["Gemiddelde Explosieve Power"] * len(df), index=df.index)

TIER_COLORS = {
    "Lage Explosieve Power": "#ef4444",
    "Gemiddelde Explosieve Power": "#f59e0b",
    "Hoge Explosieve Power": "#22c55e",
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
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap');
    * { box-sizing: border-box; }
    body { margin: 0; font-family: 'Poppins', sans-serif; background: transparent; }
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
            <div><span class="dot" style="background:#ef4444;"></span>Lage Explosieve Power</div>
            <div><span class="dot" style="background:#f59e0b;"></span>Gemiddelde Explosieve Power</div>
            <div><span class="dot" style="background:#22c55e;"></span>Hoge Explosieve Power</div>
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

avg_afstand_m = float(df["afstand_m"].mean())
best_afstand_row = df.loc[df["afstand_m"].idxmax()]

u1, u2 = st.columns(2)
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

# Benchmark TopEnd Sport (Adults only) — Yo-Yo IR1 classificatie t.o.v. een
# vaste, geslachtsafhankelijke normtabel (dus geen teamgemiddelde). Vereist
# een "geslacht"-kolom in de brondata; ontbreekt die, dan blijft dit leeg
# en verschijnen er simpelweg geen labels/legenda (geen crash).
if "geslacht" in stamina_df.columns:
    stamina_df["benchmark"] = stamina_df.apply(
        lambda r: classify_topend_benchmark(r["afstand_m"], r["geslacht"]), axis=1
    )
else:
    stamina_df["benchmark"] = None

STAMINA_NAMES_JSON = json.dumps(stamina_df["naam"].tolist(), ensure_ascii=False)
STAMINA_VALUES_JSON = json.dumps([float(v) / 1000 for v in stamina_df["afstand_m"]], ensure_ascii=False)
STAMINA_COLORS_JSON = json.dumps(stamina_df["stamina_kleur"].tolist(), ensure_ascii=False)
AVG_AFSTAND_KM_JSON = json.dumps(avg_afstand_m / 1000, ensure_ascii=False)

STAMINA_HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap');
    * { box-sizing: border-box; }
    body { margin: 0; font-family: 'Poppins', sans-serif; background: transparent; }
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
                <div class="card-title">Stamina per Speler</div>
                <div class="card-subtitle">Kleuren tonen prestatie t.o.v. teamgemiddelde</div>
            </div>
            <div class="toggle-wrap">
                <input type="checkbox" id="avgToggle" checked />
                <label for="avgToggle">Team gemiddelde</label>
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

    var avgToggle = document.getElementById("avgToggle");
    var currentOpacity = 1;

    function easeInOutCubic(t) {
        return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
    }

    var layout = {
        xaxis: { title: null, automargin: true, ticksuffix: " km" },
        yaxis: { title: null, autorange: "reversed", automargin: true },
        height: 480,
        margin: { l: 10, r: 20, t: 30, b: 30 },
        paper_bgcolor: "white",
        plot_bgcolor: "white",
        shapes: [{
            type: "line",
            x0: AVG_KM, x1: AVG_KM,
            y0: 0, y1: 1, yref: "paper",
            line: { color: "#4f46e5", width: 1.5, dash: "dash" },
            opacity: 1,
        }],
        annotations: [{
            x: AVG_KM, y: 1, yref: "paper", yanchor: "bottom",
            text: "Team gem.: " + AVG_KM.toFixed(2) + " km",
            showarrow: false,
            font: { size: 11, color: "#4f46e5" },
            opacity: 1,
        }],
    };

    Plotly.newPlot("staminaChart", [{
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
            Plotly.relayout("staminaChart", { "shapes[0].opacity": val, "annotations[0].opacity": val });
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
)
components.html(stamina_html_out, height=620, scrolling=False)

# =============================================================================
# Benchmark TopEnd Sport (Adults only) — losse visualisatie
# =============================================================================
# Aparte kaart i.p.v. verwerkt in de Stamina-chart hierboven: dit is een
# classificatie t.o.v. een vaste, geslachtsafhankelijke normtabel (Yo-Yo
# IR1), een ander soort vergelijking dan "t.o.v. teamgemiddelde" hierboven.
# Door ze apart te houden blijft elke chart maar één signaal per keer tonen.
benchmark_df = stamina_df[stamina_df["benchmark"].notna()].copy()

if not benchmark_df.empty:
    BENCHMARK_RANK = {lbl: i + 1 for i, lbl in enumerate(TOPEND_BENCHMARK_ORDER)}
    benchmark_df["benchmark_rank"] = benchmark_df["benchmark"].map(BENCHMARK_RANK)
    benchmark_df = benchmark_df.sort_values("benchmark_rank", ascending=False)

    st.markdown('<div class="dash-title">Benchmark TopEnd Sport (Adults only)</div>', unsafe_allow_html=True)
    st.markdown('<div class="dash-subtitle">Yo-Yo IR1-classificatie t.o.v. een vaste normtabel (per geslacht) — losstaand van het teamgemiddelde hierboven</div>', unsafe_allow_html=True)

    badge_rows_html = ""
    for _, r in benchmark_df.iterrows():
        color = TOPEND_BENCHMARK_COLORS[r["benchmark"]]
        km_text = f'{r["afstand_m"] / 1000:.2f} km'
        badge_rows_html += f"""
        <div class="benchmark-row">
            <div class="benchmark-name">{r['naam']}</div>
            <div class="benchmark-right">
                <span class="benchmark-km">{km_text}</span>
                <span class="benchmark-badge" style="background-color:{color};">{r['benchmark']}</span>
            </div>
        </div>"""

    st.markdown(f"""
<style>
    .benchmark-card {{ background-color: #ffffff; border-radius: 14px; padding: 1.5rem 1.75rem; margin-bottom: 1.5rem; }}
    .benchmark-row {{
        display: flex; justify-content: space-between; align-items: center;
        padding: 0.65rem 0; border-bottom: 1px solid #f1f5f9;
    }}
    .benchmark-row:last-child {{ border-bottom: none; }}
    .benchmark-name {{ font-size: 0.95rem; font-weight: 600; color: #111827; }}
    .benchmark-right {{ display: flex; align-items: center; gap: 0.75rem; }}
    .benchmark-km {{ font-size: 0.82rem; color: #9ca3af; }}
    .benchmark-badge {{
        display: inline-block; color: #ffffff; font-size: 0.78rem; font-weight: 700;
        padding: 0.3rem 0.8rem; border-radius: 999px; min-width: 110px; text-align: center;
    }}
    @media (max-width: 640px) {{
        .benchmark-card {{ padding: 1.1rem 1.2rem; }}
        .benchmark-badge {{ min-width: 90px; font-size: 0.72rem; }}
        .benchmark-km {{ display: none; }}
    }}
</style>
<div class="benchmark-card">{badge_rows_html}
</div>
""", unsafe_allow_html=True)
