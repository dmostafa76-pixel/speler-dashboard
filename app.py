import json
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Speler Prestatie Dashboard", layout="wide")

st.markdown("""
<style>
/* Verberg Streamlit's eigen header/menu voor een clean look */
#MainMenu {visibility: hidden;}
header {visibility: hidden;}

.top-navbar {
    display: flex;
    align-items: center;
    background-color: #1e1b3a;
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
    color: #a5b4fc;
    margin-top: 0.1rem;
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
    <div class="navbar-logo">KICK<span class="sub">COMPETITION</span></div>
</div>

<div class="page-title">Baseline Dashboard - 1e Testmoment</div>
<div class="page-subtitle">Overzicht van alle prestatiegegevens van het team</div>
""", unsafe_allow_html=True)

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
def load_data():
    raw = pd.read_csv("data/players.csv")

    # De brondata gebruikt andere kolomnamen dan de rest van dit script.
    # Hier hernoemen we ze één keer naar interne, consistente namen.
    column_map = {
        "Player Name": "naam",
        "Prefered Position": "positie",
        "Acc speed (km/h)": "acceleratie_kmh",
        "Top speed (km/h)": "max_snelheid_kmh",
        "Jump height (cm)": "sprong_cm",
        "Agilitiy Time (sec)": "agility_zonder_bal_s",
        "DribbelingTime (sec)": "agility_met_bal_s",
        "Distance (m)": "afstand_m",
    }
    raw = raw.rename(columns=column_map)
    return raw

df = load_data()

POSITION_COLORS = {
    "Aanvaller": "#ef4444",
    "Middenvelder": "#3b82f6",
    "Verdediger": "#22c55e",
    "Doelman": "#f97316",
}

# (min, max, invert) -> invert=True betekent: lager is beter
RANGES = {
    "agility": (6.5, 11.0, True),
    "acceleratie": (25, 40, False),
    "max_snelheid": (28, 42, False),
    "sprong": (40, 70, False),
    "uithoudingsvermogen": (7000, 14000, False),  # nu in meters (was voorheen km)
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
# SECTIE 1 — SPIDER CHART (CLIENT-SIDE, MET ECHTE SMOOTH TRANSITIE)
# =============================================================================
st.markdown('<div class="dash-title">Spider Chart - Algehele Prestatie</div>', unsafe_allow_html=True)
st.markdown('<div class="dash-subtitle">Vergelijking speler vs. teamgemiddelde</div>', unsafe_allow_html=True)

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
            "Uithoud-vermogen": f'{row["afstand_m"] / 1000:.2f} km',
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
        overflow: hidden;
    }
    .stat-bar-fill {
        border-radius: 999px;
        height: 7px;
        transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
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
            <div style="flex:1; min-width:260px;">
                <span class="sel-label">Selecteer Speler</span>
                <select id="playerSelect"></select>
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
                <div class="note-box">
                    <b>Opmerking</b><br>
                    De spider chart toont genormaliseerde waarden (0-100) voor een directe vergelijking tussen verschillende metrics.
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
    var toggleEl = document.getElementById("teamToggle");

    PLAYER_NAMES.forEach(function (name, i) {
        var opt = document.createElement("option");
        opt.value = name;
        opt.textContent = LABEL_OPTIONS[i];
        if (name === DEFAULT_NAME) opt.selected = true;
        selectEl.appendChild(opt);
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

    function buildTraces(name, showTeam) {
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

    function updateLegend(name, showTeam) {
        var html = "";
        if (showTeam) {
            html += '<div><span class="dot" style="background:#3b82f6;"></span>Team Gemiddelde</div>';
        }
        html += '<div><span class="dot" style="background:#14b8a6;"></span>' + name + "</div>";
        document.getElementById("legendBox").innerHTML = html;
    }

    function updateInfoPanel(name) {
        var p = PLAYERS[name];
        document.getElementById("playerName").textContent = name;
        document.getElementById("playerPos").textContent = p.positie;

        var barsHtml = "";
        CATEGORIES.forEach(function (cat) {
            var pct = p.scores[cat];
            var value = p.raw[cat];
            var color = STAT_COLORS[cat];
            var label = STAT_LABELS[cat];
            barsHtml += (
                '<div class="stat-row">' +
                '<div class="stat-label-row"><span>' + label + "</span><span>" + value + "</span></div>" +
                '<div class="stat-bar-bg"><div class="stat-bar-fill" style="width:' + pct + '%; background-color:' + color + ';"></div></div>' +
                "</div>"
            );
        });
        document.getElementById("statBars").innerHTML = barsHtml;
    }

    function renderChart(name) {
        var showTeam = toggleEl.checked;
        var traces = buildTraces(name, showTeam);

        if (!chartInitialized) {
            Plotly.newPlot("spiderChart", traces, baseLayout, { displayModeBar: false, responsive: true });
            chartInitialized = true;
        } else {
            animateToTraces(traces);
        }
        updateLegend(name, showTeam);
        updateInfoPanel(name);

        if (typeof resizeFrame === "function") {
            setTimeout(resizeFrame, 50);
        }
    }

    selectEl.addEventListener("change", function () {
        renderChart(selectEl.value);
    });
    toggleEl.addEventListener("change", function () {
        renderChart(selectEl.value);
    });

    renderChart(DEFAULT_NAME);

    // --- Iframe-hoogte automatisch laten meebewegen met de inhoud ---
    // (voorkomt witruimte op desktop en afgesneden content op mobiel,
    // waar de kolommen onder elkaar komen te staan)
    function resizeFrame() {
        var frame = window.frameElement;
        if (frame) {
            frame.style.height = document.body.scrollHeight + "px";
        }
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
components.html(html_out, height=700, scrolling=False)

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

col_bar, col_scatter = st.columns(2)

# --- Agility per speler (bar chart) ---
with col_bar:
    st.markdown('<div class="white-card">', unsafe_allow_html=True)
    top_row = st.columns([3, 1])
    with top_row[0]:
        st.markdown('<div class="card-title">Agility per Speler</div>', unsafe_allow_html=True)
        st.markdown('<div class="card-subtitle">Gesorteerd op prestatie (lager is beter)</div>', unsafe_allow_html=True)
    with top_row[1]:
        show_ref = st.checkbox("Referentielijn", value=True)

    sorted_df = df.sort_values("agility_zonder_bal_s")
    colors = [POSITION_COLORS[p] for p in sorted_df["positie"]]

    bar_fig = go.Figure(go.Bar(
        x=sorted_df["agility_zonder_bal_s"],
        y=sorted_df["naam"],
        orientation="h",
        marker_color=colors,
    ))
    if show_ref:
        bar_fig.add_vline(x=avg_zonder, line_dash="dash", line_color="#9ca3af")
    bar_fig.update_layout(
        xaxis_title=None, yaxis_title=None,
        yaxis=dict(autorange="reversed"),
        height=430,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="white", plot_bgcolor="white",
    )
    st.plotly_chart(bar_fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# --- Agility matrix (scatter) ---
with col_scatter:
    st.markdown('<div class="white-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">Agility Matrix</div>', unsafe_allow_html=True)
    st.markdown('<div class="card-subtitle">Zonder bal vs. Met bal</div>', unsafe_allow_html=True)

    scatter_fig = go.Figure()
    for pos, color in POSITION_COLORS.items():
        sub = df[df["positie"] == pos]
        if sub.empty:
            continue
        scatter_fig.add_trace(go.Scatter(
            x=sub["agility_zonder_bal_s"], y=sub["agility_met_bal_s"],
            mode="markers", marker=dict(color=color, size=10),
            name=pos, text=sub["naam"], hovertemplate="%{text}<extra></extra>",
        ))
    scatter_fig.add_vline(x=avg_zonder, line_dash="dot", line_color="#d1d5db")
    scatter_fig.add_hline(y=avg_met, line_dash="dot", line_color="#d1d5db")
    scatter_fig.update_layout(
        xaxis=dict(title="Agility Zonder Bal (s) →", autorange="reversed"),
        yaxis=dict(title="Agility Met Bal (s) ↑", autorange="reversed"),
        height=380,
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=-0.35),
        paper_bgcolor="white", plot_bgcolor="white",
    )
    st.plotly_chart(scatter_fig, use_container_width=True)

    q1, q2 = st.columns(2)
    with q1:
        st.markdown("""
        <div class="quad-box" style="background-color:#dcfce7;">
            <div class="quad-title" style="color:#166534;">Linksboven: Game Changer</div>
            <div style="color:#166534;">Explosief + technisch sterk</div>
        </div>""", unsafe_allow_html=True)
        st.markdown("""
        <div class="quad-box" style="background-color:#dbeafe;">
            <div class="quad-title" style="color:#1e40af;">Linksonder</div>
            <div style="color:#1e40af;">Technisch sterk, minder wendbaar</div>
        </div>""", unsafe_allow_html=True)
    with q2:
        st.markdown("""
        <div class="quad-box" style="background-color:#fee2e2;">
            <div class="quad-title" style="color:#991b1b;">Rechtsonder: Probleem</div>
            <div style="color:#991b1b;">Traag + slechte balcontrole</div>
        </div>""", unsafe_allow_html=True)
        st.markdown("""
        <div class="quad-box" style="background-color:#ffedd5;">
            <div class="quad-title" style="color:#9a3412;">Rechtsboven</div>
            <div style="color:#9a3412;">Wendbaar, balvaardigheid onder druk</div>
        </div>""", unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
