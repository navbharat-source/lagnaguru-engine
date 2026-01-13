from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import swisseph as swe
import os

app = FastAPI(title="LagnaGuru Parāśari Engine")

# Allow browser calls
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ephemeris setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
swe.set_ephe_path(BASE_DIR)
swe.set_sid_mode(swe.SIDM_LAHIRI)

RASI_NAMES = [
    "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
    "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"
]

NAKSHATRA_NAMES = [
    "Ashwini","Bharani","Krittika","Rohini","Mrigashirsha","Ardra",
    "Punarvasu","Pushya","Ashlesha","Magha","Purva Phalguni","Uttara Phalguni",
    "Hasta","Chitra","Swati","Vishakha","Anuradha","Jyeshtha",
    "Mula","Purva Ashadha","Uttara Ashadha","Shravana","Dhanishta",
    "Shatabhisha","Purva Bhadrapada","Uttara Bhadrapada","Revati"
]

@app.get("/")
def health():
    return {"status": "LagnaGuru engine running"}

@app.get("/calculate")
def calculate(
    year: int,
    month: int,
    day: int,
    hour: float,
    lat: float,
    lon: float
):
    # Julian Day
    jd = swe.julday(year, month, day, hour)

    # Ascendant
    houses, ascmc = swe.houses(jd, lat, lon)
    asc_tropical = ascmc[0]

    # Sidereal correction
    ayanamsa = swe.get_ayanamsa(jd)
    asc_sidereal = (asc_tropical - ayanamsa) % 360

    rasi_index = int(asc_sidereal // 30)
    degree_in_rasi = round(asc_sidereal % 30, 2)

    nak_index = int(asc_sidereal // (360 / 27))
    pada = int((asc_sidereal % (360 / 27)) // (360 / 108)) + 1

    return {
        "lagna": RASI_NAMES[rasi_index],
        "degree": degree_in_rasi,
        "nakshatra": NAKSHATRA_NAMES[nak_index],
        "pada": pada
    }
