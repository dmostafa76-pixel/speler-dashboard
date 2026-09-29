"""
Gedeelde logica voor het inlezen en valideren van speler-testdata.

Wordt gebruikt door zowel app.py (het dashboard) als pages/1_Upload_Data.py
(de upload-pagina), zodat een CSV op precies dezelfde manier wordt
gecontroleerd en omgezet, ongeacht waar hij vandaan komt.
"""
import pandas as pd


def norm(col: str) -> str:
    """Normaliseert een kolomnaam: alleen letters/cijfers, kleine letters.
    Spaties, haakjes, regeleinden en hoofdletters maken dan niet meer uit."""
    return "".join(ch for ch in str(col).lower() if ch.isalnum())


# Canonieke interne naam -> lijst van bekende varianten in brondata.
# Voeg hier een nieuwe regel toe zodra een testtool een andere kolomnaam
# blijkt te gebruiken (bv. een taal- of spellingsvariant).
COLUMN_ALIASES = {
    "naam": ["Player Name", "Name"],
    "positie": ["Prefered Position", "Preferred Position", "Position"],
    "acceleratie_kmh": ["Acc speed (km/h)", "Acceleration Speed (km/h)"],
    "max_snelheid_kmh": ["Top speed (km/h)", "Max speed (km/h)"],
    "sprong_cm": ["Jump height (cm)"],
    # "Agilitiy" (met tikfout) is de spelling die in de huidige players.csv
    # in de repo staat; "Agility" is de correcte spelling die de nieuwe
    # pilot-data gebruikt. Allebei worden geaccepteerd.
    "agility_zonder_bal_s": ["Agility Time (sec)", "Agilitiy Time (sec)"],
    "agility_met_bal_s": ["Dribbeling Time (sec)", "DribbelingTime (sec)", "Dribbling Time (sec)"],
    "afstand_m": ["Distance (m)"],
    "power_watt": ["Explosive Power (watt)"],
    "geslacht": ["Gender", "Geslacht", "Sex"],
}

REQUIRED_FIELDS = [
    "naam", "positie", "acceleratie_kmh", "max_snelheid_kmh",
    "sprong_cm", "agility_zonder_bal_s", "agility_met_bal_s", "afstand_m",
]

# power_watt is optioneel: als hij ontbreekt valt de sprong-analyse terug op
# een neutrale kleur i.p.v. te crashen (zie app.py).


def _build_column_map():
    mapping = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            mapping[norm(alias)] = canonical
    return mapping


_COLUMN_MAP = _build_column_map()


def normalize_players_df(raw: pd.DataFrame):
    """Zet een ruwe CSV (zoals geëxporteerd door de testtool) om naar het
    interne schema dat het dashboard verwacht.

    Retourneert (clean_df, missing_required, unused_columns):
      - clean_df: dataframe met de herkende/hernoemde kolommen
      - missing_required: lijst met verplichte velden die niet gevonden zijn
      - unused_columns: kolommen uit de brondata die niet herkend/gebruikt zijn
    """
    rename_dict = {}
    used_original_cols = set()
    for original_col in raw.columns:
        key = norm(original_col)
        if key in _COLUMN_MAP:
            rename_dict[original_col] = _COLUMN_MAP[key]
            used_original_cols.add(original_col)

    clean = raw.rename(columns=rename_dict)

    if "positie" in clean.columns:
        clean["positie"] = clean["positie"].astype(str).str.strip()
    if "naam" in clean.columns:
        clean["naam"] = clean["naam"].astype(str).str.strip()

    missing_required = [f for f in REQUIRED_FIELDS if f not in clean.columns]
    unused_columns = [c for c in raw.columns if c not in used_original_cols]

    return clean, missing_required, unused_columns


TEAMS_MANIFEST_PATH = "data/teams/teams.json"


def slugify(name: str) -> str:
    """Zet een teamnaam om in een veilige mapnaam, bv. 'JO17 - Zaterdag 1' -> 'jo17-zaterdag-1'."""
    chars = [ch.lower() if ch.isalnum() else "-" for ch in str(name).strip()]
    slug = "".join(chars)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-") or "team"


def team_players_path(team_slug: str) -> str:
    return f"data/teams/{team_slug}/players.csv"


def team_testmoment_path(team_slug: str, base_name: str, kind: str) -> str:
    # kind is "raw" of "clean"
    return f"data/teams/{team_slug}/testmomenten/{base_name}_{kind}.csv"


# "Benchmark TopEnd Sport (Adults only)" classificatie voor de Yo-Yo
# Intermittent Recovery Test Level 1 (afstand in meter), gebaseerd op de
# normtabel van topendsports.com. Drempelwaarden zijn geslachtsafhankelijk;
# zonder bekend geslacht kan er geen classificatie worden bepaald.
TOPEND_BENCHMARK_ORDER = ["Poor", "Below Average", "Average", "Good", "Excellent", "Elite"]
TOPEND_BENCHMARK_COLORS = {
    "Poor": "#dc2626",
    "Below Average": "#f97316",
    "Average": "#eab308",
    "Good": "#84cc16",
    "Excellent": "#22c55e",
    "Elite": "#15803d",
}

_MALE_ALIASES = {"male", "man", "m", "jongen", "boy"}
_FEMALE_ALIASES = {"female", "vrouw", "v", "f", "meisje", "girl"}

_MALE_THRESHOLDS = [(2400, "Elite"), (2000, "Excellent"), (1520, "Good"), (1040, "Average"), (520, "Below Average")]
_FEMALE_THRESHOLDS = [(1600, "Elite"), (1320, "Excellent"), (1000, "Good"), (680, "Average"), (320, "Below Average")]


def classify_topend_benchmark(afstand_m, geslacht):
    """Geeft de Benchmark TopEnd Sport-categorie terug voor een Yo-Yo IR1
    afstand (meter), of None als het geslacht niet herkend wordt."""
    g = str(geslacht).strip().lower()
    if g in _MALE_ALIASES:
        thresholds = _MALE_THRESHOLDS
    elif g in _FEMALE_ALIASES:
        thresholds = _FEMALE_THRESHOLDS
    else:
        return None
    for threshold, label in thresholds:
        if afstand_m > threshold:
            return label
    return "Poor"


def load_players_csv(path_or_buffer):
    """Leest een CSV-bestand (pad of file-achtig object) en normaliseert 'm.
    Gooit een ValueError met duidelijke boodschap als verplichte kolommen
    ontbreken."""
    raw = pd.read_csv(path_or_buffer)
    clean, missing_required, unused_columns = normalize_players_df(raw)
    if missing_required:
        raise ValueError(
            "Deze verwachte kolommen zijn niet gevonden: "
            f"{missing_required}. Gevonden kolommen in het bestand: {raw.columns.tolist()}"
        )
    return clean, unused_columns
