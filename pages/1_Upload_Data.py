"""
Upload-pagina voor nieuwe testmoment-data (alleen voor de eigenaar/beheerder).

De beheerder sleept hier de CSV uit de testtool in, kiest voor welk team
de data is, de pagina controleert en zet 'm om naar het interne format,
toont een preview, en zet 'm bij bevestiging direct in de GitHub-repo.
Streamlit Cloud detecteert die wijziging automatisch en herlaadt het
dashboard (meestal binnen ~1 minuut) — dus geen handmatige git-stappen nodig.

Coaches loggen op het hoofddashboard (app.py) in met hun eigen account en
zien daar automatisch alleen hun eigen team — deze pagina is niet voor hen
bedoeld en staat nergens op het dashboard gelinkt.
"""
import base64
import datetime as dt
import io
import json

import pandas as pd
import requests
import streamlit as st

from data_utils import (
    normalize_players_df,
    REQUIRED_FIELDS,
    TEAMS_MANIFEST_PATH,
    slugify,
    team_players_path,
    team_testmoment_path,
)

st.set_page_config(page_title="Testdata Uploaden", layout="centered")

st.markdown("## Nieuw testmoment uploaden")
st.caption("Voeg hier de CSV van een testmoment toe. Na bevestigen wordt het dashboard automatisch bijgewerkt.")

# ---------------------------------------------------------------------------
# Simpel wachtwoord-hekje, zodat niet zomaar iedereen data kan overschrijven.
# Wachtwoord staat in Streamlit secrets als UPLOAD_PASSWORD.
# ---------------------------------------------------------------------------
if "upload_authed" not in st.session_state:
    st.session_state.upload_authed = False

if not st.session_state.upload_authed:
    pw = st.text_input("Wachtwoord", type="password")
    if st.button("Inloggen"):
        if pw and pw == st.secrets.get("UPLOAD_PASSWORD"):
            st.session_state.upload_authed = True
            st.rerun()
        else:
            st.error("Onjuist wachtwoord.")
    st.stop()

# ---------------------------------------------------------------------------
# GitHub-instellingen (uit Streamlit secrets, zie SETUP_UPLOAD.md)
# ---------------------------------------------------------------------------
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN")
GITHUB_REPO = st.secrets.get("GITHUB_REPO")  # bv. "dmostafa76-pixel/speler-dashboard"
GITHUB_BRANCH = st.secrets.get("GITHUB_BRANCH", "main")

if not GITHUB_TOKEN or not GITHUB_REPO:
    st.error(
        "GITHUB_TOKEN en/of GITHUB_REPO ontbreken in de Streamlit secrets. "
        "Zie SETUP_UPLOAD.md voor hoe je dit instelt."
    )
    st.stop()

API_ROOT = f"https://api.github.com/repos/{GITHUB_REPO}/contents"
HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
}


def github_get_sha(path: str):
    """Geeft de huidige sha van een bestand in de repo terug, of None als het nog niet bestaat."""
    resp = requests.get(f"{API_ROOT}/{path}", headers=HEADERS, params={"ref": GITHUB_BRANCH}, timeout=15)
    if resp.status_code == 200:
        return resp.json()["sha"]
    if resp.status_code == 404:
        return None
    resp.raise_for_status()


def github_get_file(path: str):
    """Geeft de inhoud (bytes) van een bestand terug, of None als het nog niet bestaat."""
    resp = requests.get(f"{API_ROOT}/{path}", headers=HEADERS, params={"ref": GITHUB_BRANCH}, timeout=15)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return base64.b64decode(resp.json()["content"])


def github_put_file(path: str, content_bytes: bytes, message: str):
    """Maakt of overschrijft een bestand in de repo via de GitHub Contents API."""
    sha = github_get_sha(path)
    payload = {
        "message": message,
        "content": base64.b64encode(content_bytes).decode("utf-8"),
        "branch": GITHUB_BRANCH,
    }
    if sha:
        payload["sha"] = sha
    resp = requests.put(f"{API_ROOT}/{path}", headers=HEADERS, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def load_teams():
    """Leest data/teams/teams.json uit de repo. {} als het bestand nog niet bestaat."""
    raw = github_get_file(TEAMS_MANIFEST_PATH)
    if raw is None:
        return {}
    return json.loads(raw.decode("utf-8"))


# ---------------------------------------------------------------------------
# Team kiezen (of nieuw team aanmaken)
# ---------------------------------------------------------------------------
teams = load_teams()  # {slug: {"display_name": "..."}}

st.markdown("#### Team")
team_options = ["+ Nieuw team aanmaken"] + [t["display_name"] for t in teams.values()]
slug_by_display = {t["display_name"]: slug for slug, t in teams.items()}

gekozen = st.selectbox("Voor welk team is deze data?", team_options)

if gekozen == "+ Nieuw team aanmaken":
    nieuw_team_naam = st.text_input("Naam van het nieuwe team (bv. 'JO17 Zaterdag 1')")
    team_slug = slugify(nieuw_team_naam) if nieuw_team_naam else None
    team_display_name = nieuw_team_naam
    if nieuw_team_naam and team_slug in teams:
        st.warning(f"Er bestaat al een team met (bijna) deze naam: '{teams[team_slug]['display_name']}'. Kies die hierboven, of gebruik een andere naam.")
else:
    team_display_name = gekozen
    team_slug = slug_by_display[gekozen]

st.markdown("---")

# ---------------------------------------------------------------------------
# Formulier
# ---------------------------------------------------------------------------
col1, col2 = st.columns(2)
with col1:
    testmoment_nr = st.number_input("Testmoment nummer", min_value=1, value=1, step=1)
with col2:
    testmoment_datum = st.date_input("Datum testmoment", value=dt.date.today())

maak_actief = st.checkbox(
    "Maak dit de actieve dataset voor het dashboard van dit team",
    value=True,
    help="Overschrijft de dataset die coaches van dit team nu op hun dashboard zien.",
)

uploaded_file = st.file_uploader("CSV-bestand van het testmoment", type=["csv"])

if uploaded_file is not None and team_slug:
    raw_bytes = uploaded_file.getvalue()
    try:
        raw_df = pd.read_csv(io.BytesIO(raw_bytes))
    except Exception as e:
        st.error(f"Kon het CSV-bestand niet lezen: {e}")
        st.stop()

    clean_df, missing_required, unused_columns = normalize_players_df(raw_df)

    if missing_required:
        st.error(
            "Dit bestand mist verplichte kolommen en kan niet worden verwerkt: "
            f"{missing_required}.\n\nVerwacht (interne namen): {REQUIRED_FIELDS}\n\n"
            f"Gevonden kolommen in het bestand: {raw_df.columns.tolist()}"
        )
        st.stop()

    st.success(f"Bestand gelezen: {len(clean_df)} spelers herkend voor team '{team_display_name}'.")
    if unused_columns:
        st.info(f"Niet-gebruikte kolommen (worden genegeerd): {unused_columns}")

    st.markdown("#### Preview")
    st.dataframe(clean_df, use_container_width=True)

    st.markdown("---")
    if st.button("Bevestigen en naar dashboard sturen", type="primary"):
        date_str = testmoment_datum.isoformat()
        base_name = f"testmoment_{int(testmoment_nr)}_{date_str}"
        clean_csv_bytes = clean_df.to_csv(index=False).encode("utf-8")
        is_new_team = team_slug not in teams

        with st.spinner("Bezig met wegschrijven naar GitHub..."):
            try:
                github_put_file(
                    team_testmoment_path(team_slug, base_name, "raw"),
                    raw_bytes,
                    f"[{team_display_name}] Ruwe data testmoment {int(testmoment_nr)} ({date_str})",
                )
                github_put_file(
                    team_testmoment_path(team_slug, base_name, "clean"),
                    clean_csv_bytes,
                    f"[{team_display_name}] Verwerkte data testmoment {int(testmoment_nr)} ({date_str})",
                )
                if maak_actief:
                    github_put_file(
                        team_players_path(team_slug),
                        clean_csv_bytes,
                        f"[{team_display_name}] Dashboard bijgewerkt met testmoment {int(testmoment_nr)} ({date_str})",
                    )
                if is_new_team:
                    teams[team_slug] = {"display_name": team_display_name}
                    github_put_file(
                        TEAMS_MANIFEST_PATH,
                        json.dumps(teams, ensure_ascii=False, indent=2).encode("utf-8"),
                        f"Nieuw team toegevoegd: {team_display_name}",
                    )
            except requests.HTTPError as e:
                st.error(f"Wegschrijven naar GitHub is mislukt: {e}")
                st.stop()

        st.success(
            "Gelukt! De data staat in GitHub. Het dashboard herlaadt automatisch "
            "(meestal binnen ~1 minuut)."
        )
        if is_new_team:
            st.info(
                f"Nieuw team '{team_display_name}' aangemaakt (slug: `{team_slug}`). "
                "Vergeet niet om in Streamlit secrets een coach-account voor dit team aan te "
                "maken — zie SETUP_TEAMS.md."
            )
        if maak_actief:
            st.balloons()
