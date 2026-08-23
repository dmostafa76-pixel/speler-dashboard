"""
Upload-pagina voor nieuwe testmoment-data.

Een coach/trainer sleept hier de CSV uit de testtool in, de pagina
controleert en zet 'm om naar het interne format, toont een preview,
en zet 'm bij bevestiging direct in de GitHub-repo. Streamlit Cloud
detecteert die wijziging automatisch en herlaadt het dashboard
(meestal binnen ~1 minuut) — dus geen handmatige git-stappen nodig.
"""
import base64
import datetime as dt
import io

import pandas as pd
import requests
import streamlit as st

from data_utils import normalize_players_df, REQUIRED_FIELDS

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


# ---------------------------------------------------------------------------
# Formulier
# ---------------------------------------------------------------------------
col1, col2 = st.columns(2)
with col1:
    testmoment_nr = st.number_input("Testmoment nummer", min_value=1, value=1, step=1)
with col2:
    testmoment_datum = st.date_input("Datum testmoment", value=dt.date.today())

maak_actief = st.checkbox(
    "Maak dit de actieve dataset voor het dashboard",
    value=True,
    help="Overschrijft data/players.csv, dus wat bezoekers nu op het dashboard zien.",
)

uploaded_file = st.file_uploader("CSV-bestand van het testmoment", type=["csv"])

if uploaded_file is not None:
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

    st.success(f"Bestand gelezen: {len(clean_df)} spelers herkend.")
    if unused_columns:
        st.info(f"Niet-gebruikte kolommen (worden genegeerd): {unused_columns}")

    st.markdown("#### Preview")
    st.dataframe(clean_df, use_container_width=True)

    st.markdown("---")
    if st.button("Bevestigen en naar dashboard sturen", type="primary"):
        date_str = testmoment_datum.isoformat()
        base_name = f"testmoment_{int(testmoment_nr)}_{date_str}"
        clean_csv_bytes = clean_df.to_csv(index=False).encode("utf-8")

        with st.spinner("Bezig met wegschrijven naar GitHub..."):
            try:
                github_put_file(
                    f"data/testmomenten/{base_name}_raw.csv",
                    raw_bytes,
                    f"Ruwe data testmoment {int(testmoment_nr)} ({date_str})",
                )
                github_put_file(
                    f"data/testmomenten/{base_name}_clean.csv",
                    clean_csv_bytes,
                    f"Verwerkte data testmoment {int(testmoment_nr)} ({date_str})",
                )
                if maak_actief:
                    github_put_file(
                        "data/players.csv",
                        clean_csv_bytes,
                        f"Dashboard bijgewerkt met testmoment {int(testmoment_nr)} ({date_str})",
                    )
            except requests.HTTPError as e:
                st.error(f"Wegschrijven naar GitHub is mislukt: {e}")
                st.stop()

        st.success(
            "Gelukt! De data staat in GitHub. Het dashboard herlaadt automatisch "
            "(meestal binnen ~1 minuut)."
        )
        if maak_actief:
            st.balloons()
