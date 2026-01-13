from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import swisseph as swe
import os
import math
from datetime import datetime

app = FastAPI(title="LagnaGuru Pro Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONFIG ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
swe.set_ephe_path(BASE_DIR)
swe.set_sid_mode(swe.SIDM_LAHIRI)

RASI_NAMES = ["Mesham", "Rishabam", "Mithunam", "Kadagam", "Simham", "Kanni", "Thulaam", "Vrischikam", "Dhanusu", "Makaram", "Kumbham", "Meenam"]
NAKSHATRAS = ["Ashwini","Bharani","Krittika","Rohini","Mrigashirsha","Ardra","Punarvasu","Pushya","Ashlesha","Magha","Purva Phalguni","Uttara Phalguni","Hasta","Chitra","Swati","Vishakha","Anuradha","Jyeshtha","Mula","Purva Ashadha","Uttara Ashadha","Shravana","Dhanishta","Shatabhisha","Purva Bhadrapada","Uttara Bhadrapada","Revati"]
PLANETS = {0: "Sun", 1: "Moon", 2: "Mercury", 3: "Venus", 4: "Mars", 5: "Jupiter", 6: "Saturn"}

# --- HELPER: Calculate D9 (Navamsa) ---
def get_navamsa_sign(lon_deg):
    # Formula: (Longitude * 9) % 360
    d9_lon = (lon_deg * 9) % 360
    return int(d9_lon / 30)

# --- HELPER: Panchangam ---
def get_panchangam(jd):
    # Tithi: (Moon - Sun) / 12
    moon = swe.calc_ut(jd, 1)[0][0]
    sun = swe.calc_ut(jd, 0)[0][0]
    diff = (moon - sun) % 360
    tithi_idx = int(diff / 12) + 1
    
    # Yoga: (Moon + Sun) / 13.333
    total = (moon + sun) % 360
    yoga_idx = int(total / 13.3333) + 1
    
    return {"tithi": tithi_idx, "yoga": yoga_idx}

@app.get("/calculate_report")
def calculate_report(dob: str, tob: str, lat: float, lon: float):
    # 1. Parse Date/Time
    dt = datetime.strptime(f"{dob} {tob}", "%Y-%m-%d %H:%M")
    hour = dt.hour + dt.minute/60.0 + dt.second/3600.0
    jd = swe.julday(dt.year, dt.month, dt.day, hour - 5.5) # Convert IST to UT

    # 2. Get Ayanamsa
    ayanamsa = swe.get_ayanamsa_ut(jd)

    # 3. Calculate Lagna (D1 & D9)
    houses, ascmc = swe.houses(jd, lat, lon, b'P')
    lagna_sid = (ascmc[0] - ayanamsa) % 360
    lagna_data = {
        "name": "Lagna",
        "d1_sign": int(lagna_sid / 30),
        "d9_sign": get_navamsa_sign(lagna_sid),
        "degree": round(lagna_sid % 30, 2),
        "nakshatra": NAKSHATRAS[int(lagna_sid / 13.3333)]
    }

    # 4. Calculate Planets (D1 & D9)
    planet_data = []
    
    # 7 Main Planets
    for pid, name in PLANETS.items():
        pos = swe.calc_ut(jd, pid)[0][0]
        sid_pos = (pos - ayanamsa) % 360
        planet_data.append({
            "id": pid,
            "name": name,
            "d1_sign": int(sid_pos / 30),
            "d9_sign": get_navamsa_sign(sid_pos),
            "degree": round(sid_pos % 30, 2),
            "nakshatra": NAKSHATRAS[int(sid_pos / 13.3333)],
            "pada": int((sid_pos % 13.3333) / 3.3333) + 1
        })

    # Rahu/Ketu
    rahu_mean = swe.calc_ut(jd, swe.MEAN_NODE)[0][0]
    rahu_sid = (rahu_mean - ayanamsa) % 360
    ketu_sid = (rahu_sid + 180) % 360
    
    planet_data.append({"id": 7, "name": "Rahu", "d1_sign": int(rahu_sid/30), "d9_sign": get_navamsa_sign(rahu_sid), "degree": round(rahu_sid%30, 2), "nakshatra": NAKSHATRAS[int(rahu_sid/13.3333)], "pada": int((rahu_sid%13.3333)/3.3333)+1})
    planet_data.append({"id": 8, "name": "Ketu", "d1_sign": int(ketu_sid/30), "d9_sign": get_navamsa_sign(ketu_sid), "degree": round(ketu_sid%30, 2), "nakshatra": NAKSHATRAS[int(ketu_sid/13.3333)], "pada": int((ketu_sid%13.3333)/3.3333)+1})

    # 5. Panchangam
    panchang = get_panchangam(jd)

    return {
        "meta": {"dob": dob, "tob": tob, "place": f"{lat}, {lon}"},
        "lagna": lagna_data,
        "planets": planet_data,
        "panchang": panchang
    }
