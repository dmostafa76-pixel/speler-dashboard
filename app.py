import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Speler Prestatie Dashboard", layout="wide")

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
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
@st.cache_data
def load_data():
    return pd.read_csv("data/players.csv")

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
    "uithoudingsvermogen": (7, 14, False),
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
        "Uithoud-vermogen": normalize(row["uithoudingsvermogen_km"], *RANGES["uithoudingsvermogen"][:2]),
    }

all_scores = [player_scores(r) for _, r in df.iterrows()]
categories = list(all_scores[0].keys())
team_scores = {cat: float(np.mean([s[cat] for s in all_scores])) for cat in categories}

# ---------------------------------------------------------------------------
# Navigatie
# ---------------------------------------------------------------------------
tab1, tab2 = st.tabs(["Spider Chart", "Agility Analyse"])

# =============================================================================
# TAB 1 — SPIDER CHART (MET SMOOTH TRANSITIE)
# =============================================================================
with tab1:
    st.markdown('<div class="dash-title">Spider Chart - Algehele Prestatie</div>', unsafe_allow_html=True)
    st.markdown('<div class="dash-subtitle">Vergelijking speler vs. teamgemiddelde</div>', unsafe_allow_html=True)

    st.markdown('<div class="white-card">', unsafe_allow_html=True)

    col_sel, col_toggle = st.columns([3, 1])
    with col_sel:
        st.markdown("**Selecteer Speler**")
        player_options = (df["naam"] + " - " + df["positie"]).tolist()
        selected_label = st.selectbox("Selecteer Speler", player_options, label_visibility="collapsed")
        selected_name = selected_label.split(" - ")[0]
    with col_toggle:
        st.write("")
        show_team_avg = st.checkbox("Toon Team Gemiddelde", value=True)

    player_row = df[df["naam"] == selected_name].iloc[0]
    scores = player_scores(player_row)

    fig = go.Figure()
    if show_team_avg:
        fig.add_trace(go.Scatterpolar(
            r=list(team_scores.values()) + [list(team_scores.values())[0]],
            theta=categories + [categories[0]],
            fill="toself", name="Team Gemiddelde",
            line_color="#3b82f6", fillcolor="rgba(59,130,246,0.15)",
        ))
    fig.add_trace(go.Scatterpolar(
        r=list(scores.values()) + [list(scores.values())[0]],
        theta=categories + [categories[0]],
        fill="toself", name=selected_name,
        line_color="#14b8a6", fillcolor="rgba(20,184,166,0.35)",
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], gridcolor="#e5e7eb"),
            # Zorgt ervoor dat zoom/rotatie behouden blijft tussen reruns,
            # zodat Plotly de update als transitie ziet i.p.v. een nieuwe grafiek
            uirevision="spider-chart",
        ),
        showlegend=False,
        margin=dict(l=40, r=40, t=20, b=20),
        height=420,
        paper_bgcolor="white", plot_bgcolor="white",
        # --- Smooth transitie wanneer data verandert (speler wisselen) ---
        transition=dict(duration=600, easing="cubic-in-out"),
    )

    col_chart, col_info = st.columns([2, 1])
    with col_chart:
        st.plotly_chart(fig, use_container_width=True)
        legend_html = '<div style="display:flex; gap:1.5rem; justify-content:center; font-size:0.85rem; color:#374151;">'
        if show_team_avg:
            legend_html += ('<div><span style="display:inline-block;width:10px;height:10px;'
                             'background:#3b82f6;border-radius:2px;margin-right:6px;"></span>Team Gemiddelde</div>')
        legend_html += (f'<div><span style="display:inline-block;width:10px;height:10px;'
                         f'background:#14b8a6;border-radius:2px;margin-right:6px;"></span>{selected_name}</div></div>')
        st.markdown(legend_html, unsafe_allow_html=True)

    with col_info:
        st.markdown(f'<div class="card-title">{selected_name}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="card-subtitle">{player_row["positie"]}</div>', unsafe_allow_html=True)

        stat_defs = [
            ("Agility", f'{player_row["agility_zonder_bal_s"]:.1f}s', scores["Agility"], "#22c55e"),
            ("Acceleratie", f'{player_row["acceleratie_kmh"]:.1f} km/h', scores["Acceleratie"], "#3b82f6"),
            ("Max. Snelheid", f'{player_row["max_snelheid_kmh"]:.1f} km/h', scores["Max Snelheid"], "#a855f7"),
            ("Sprong", f'{player_row["sprong_cm"]:.0f} cm', scores["Sprong"], "#f97316"),
            ("Uithoudingsvermogen", f'{player_row["uithoudingsvermogen_km"]:.1f} km', scores["Uithoud-vermogen"], "#ef4444"),
        ]
        for label, value_str, pct, color in stat_defs:
            st.markdown(f"""
            <div class="stat-row">
                <div class="stat-label-row"><span>{label}</span><span>{value_str}</span></div>
                <div class="stat-bar-bg"><div class="stat-bar-fill" style="width:{pct}%; background-color:{color};"></div></div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("""
        <div class="note-box">
        <b>Opmerking</b><br>
        De spider chart toont genormaliseerde waarden (0-100) voor een directe vergelijking tussen verschillende metrics.
        </div>
        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

# =============================================================================
# TAB 2 — AGILITY ANALYSE
# =============================================================================
with tab2:
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
