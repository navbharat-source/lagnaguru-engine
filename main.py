from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import swisseph as swe
import os
import math
from datetime import datetime
from typing import Dict, List, Any
import json

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
RASI_NAMES_EN = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
NAKSHATRAS = ["Ashwini","Bharani","Krittika","Rohini","Mrigashirsha","Ardra","Punarvasu","Pushya","Ashlesha","Magha","Purva Phalguni","Uttara Phalguni","Hasta","Chitra","Swati","Vishakha","Anuradha","Jyeshtha","Mula","Purva Ashadha","Uttara Ashadha","Shravana","Dhanishta","Shatabhisha","Purva Bhadrapada","Uttara Bhadrapada","Revati"]
PLANETS = {0: "Sun", 1: "Moon", 2: "Mercury", 3: "Venus", 4: "Mars", 5: "Jupiter", 6: "Saturn", 7: "Rahu", 8: "Ketu"}
PLANET_LORDS = {
    0: ["Sun"], 1: ["Moon"], 2: ["Mercury"], 3: ["Venus"], 4: ["Mars"], 
    5: ["Jupiter"], 6: ["Saturn"], 7: ["Rahu"], 8: ["Ketu"],
    9: ["Sun", "Mars"], 10: ["Venus", "Mercury"], 11: ["Mercury"], 12: ["Moon"],
    13: ["Sun"], 14: ["Mercury", "Ketu"], 15: ["Venus", "Saturn"], 16: ["Mars"],
    17: ["Jupiter", "Mercury"], 18: ["Saturn"], 19: ["Saturn", "Jupiter"],
    20: ["Jupiter"], 21: ["Saturn"], 22: ["Saturn", "Rahu"], 23: ["Jupiter", "Saturn"]
}

# House Meanings
HOUSE_MEANINGS = {
    1: "Self, personality, body, appearance",
    2: "Wealth, family, speech, possessions",
    3: "Courage, siblings, short travels, communication",
    4: "Mother, home, happiness, vehicles",
    5: "Children, intelligence, romance, past merits",
    6: "Health, debts, enemies, service",
    7: "Marriage, partnership, business, travel",
    8: "Longevity, obstacles, secrets, inheritance",
    9: "Fortune, father, guru, higher learning",
    10: "Career, fame, authority, profession",
    11: "Gains, income, friends, aspirations",
    12: "Losses, expenses, foreign, liberation"
}

# Planet Strengths
EXALTATION_DEG = {0: 10, 1: 3, 2: 15, 3: 27, 4: 28, 5: 5, 6: 20}
DEBILITATION_DEG = {0: 190, 1: 193, 2: 165, 3: 177, 4: 148, 5: 185, 6: 200}

# --- HELPER: Calculate D9 (Navamsa) ---
def get_navamsa_sign(lon_deg):
    d9_lon = (lon_deg * 9) % 360
    return int(d9_lon / 30)

# --- HELPER: Panchangam ---
def get_panchangam(jd):
    moon = swe.calc_ut(jd, 1)[0][0]
    sun = swe.calc_ut(jd, 0)[0][0]
    diff = (moon - sun) % 360
    tithi_idx = int(diff / 12) + 1
    
    total = (moon + sun) % 360
    yoga_idx = int(total / 13.3333) + 1
    
    # Nakshatra of Moon
    moon_nakshatra = int(moon / 13.3333)
    
    # Day of week
    day_num = int(jd + 1.5) % 7
    days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    
    return {
        "tithi": tithi_idx,
        "yoga": yoga_idx,
        "nakshatra": NAKSHATRAS[moon_nakshatra],
        "day": days[day_num],
        "sunrise": "06:00",  # Simplified - should calculate properly
        "sunset": "18:00"
    }

# --- HELPER: Calculate Planetary Aspects ---
def get_aspects(planet_sign, planet_name):
    aspects = []
    if planet_name == "Saturn":
        aspects.append((planet_sign + 3) % 12)  # 3rd aspect
        aspects.append((planet_sign + 7) % 12)  # 7th aspect
        aspects.append((planet_sign + 10) % 12) # 10th aspect
    elif planet_name == "Mars":
        aspects.append((planet_sign + 4) % 12)  # 4th aspect
        aspects.append((planet_sign + 7) % 12)  # 8th aspect
    elif planet_name == "Jupiter":
        aspects.append((planet_sign + 5) % 12)  # 5th aspect
        aspects.append((planet_sign + 7) % 12)  # 7th aspect
        aspects.append((planet_sign + 9) % 12)  # 9th aspect
    else:
        aspects.append((planet_sign + 7) % 12)  # 7th aspect for others
    
    return list(set(aspects))

# --- HELPER: Calculate Planetary Strength ---
def get_planet_strength(planet_id, sign, degree):
    strength = 5.0  # Base strength
    
    # Exaltation/Debilitation
    if planet_id in EXALTATION_DEG:
        exalt_deg = EXALTATION_DEG[planet_id]
        debil_deg = DEBILITATION_DEG[planet_id]
        deg_diff = min(abs(degree - exalt_deg), 360 - abs(degree - exalt_deg))
        
        if deg_diff < 5:
            strength += 2.0  # Exalted
        elif abs(degree - debil_deg) < 5:
            strength -= 2.0  # Debilitated
    
    # Own sign (simplified)
    own_signs = {
        0: [4],  # Sun: Leo
        1: [3],  # Moon: Cancer
        2: [2, 10],  # Mercury: Gemini, Virgo
        3: [1, 6],  # Venus: Taurus, Libra
        4: [0, 7],  # Mars: Aries, Scorpio
        5: [8, 10], # Jupiter: Sagittarius, Pisces
        6: [9, 10]  # Saturn: Capricorn, Aquarius
    }
    
    if planet_id in own_signs and sign in own_signs[planet_id]:
        strength += 1.5
    
    # Friend/Enemy sign
    friendly_signs = {
        0: [0, 1, 4, 8, 9],  # Sun friends
        4: [0, 1, 4, 8],     # Mars friends
        5: [0, 1, 4, 5, 8, 9] # Jupiter friends
    }
    
    if planet_id in friendly_signs:
        if sign in friendly_signs[planet_id]:
            strength += 0.5
        else:
            strength -= 0.5
    
    return round(max(1.0, min(10.0, strength)), 2)

# --- HELPER: Calculate House Placement ---
def get_house_placement(ascendant_sign, planet_sign):
    """Calculate which house a planet is in"""
    return ((planet_sign - ascendant_sign) % 12) + 1

# --- HELPER: Generate Interpretation ---
def generate_interpretation(planet_data, lagna_data):
    interpretations = []
    
    for planet in planet_data:
        name = planet["name"]
        sign = RASI_NAMES[planet["d1_sign"]]
        house = get_house_placement(lagna_data["d1_sign"], planet["d1_sign"])
        nakshatra = planet["nakshatra"]
        strength = get_planet_strength(planet["id"], planet["d1_sign"], planet["degree"])
        
        interpretation = f"{name} in {sign} ({RASI_NAMES_EN[planet['d1_sign']]}) "
        interpretation += f"situated in {house}th house of {HOUSE_MEANINGS[house].split(',')[0]}. "
        
        # Add strength commentary
        if strength >= 7:
            interpretation += f"This is a strong placement ({strength}/10). "
        elif strength <= 4:
            interpretation += f"This placement needs attention ({strength}/10). "
        
        # Special interpretations
        if name == "Moon":
            interpretation += f"Emotional nature influenced by {nakshatra} nakshatra. "
        elif name == "Sun":
            interpretation += f"Indicates vitality and self-expression. "
        elif name == "Mars":
            interpretation += f"Energy and drive manifest through {HOUSE_MEANINGS[house].split(',')[0]}. "
        elif name == "Jupiter":
            interpretation += f"Wisdom and expansion areas. "
        elif name in ["Rahu", "Ketu"]:
            interpretation += f"Karmic influence affecting {HOUSE_MEANINGS[house].split(',')[0]}. "
        
        interpretations.append({
            "planet": name,
            "interpretation": interpretation,
            "strength": strength,
            "house": house,
            "sign": sign,
            "nakshatra": nakshatra
        })
    
    return interpretations

# --- HELPER: Calculate Dashas ---
def get_current_dasha(dob_datetime):
    # Simplified Vimshottari Dasha calculation
    moon_nakshatra = 0  # Should calculate actual moon nakshatra
    dasha_order = ["Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury", "Ketu"]
    dasha_lengths = [20, 6, 10, 7, 18, 16, 19, 17, 7]
    
    # For demo - returns current Venus dasha
    return {
        "mahadasha": "Venus",
        "antardasha": "Sun",
        "start_date": "2020-01-01",
        "end_date": "2040-01-01",
        "interpretation": "Period of relationships, arts, and comforts."
    }

# --- HELPER: Generate Summary Report ---
def generate_summary_report(lagna_data, planet_data, interpretations):
    # Find strongest and weakest planets
    strengths = [(p['name'], p['strength']) for p in interpretations]
    strengths.sort(key=lambda x: x[1], reverse=True)
    
    strong_planets = strengths[:3]
    weak_planets = strengths[-3:]
    
    # Key placements
    sun_place = next(p for p in interpretations if p['planet'] == 'Sun')
    moon_place = next(p for p in interpretations if p['planet'] == 'Moon')
    asc_sign = RASI_NAMES[lagna_data["d1_sign"]]
    
    summary = f"""
    PERSONALITY OVERVIEW:
    Your Ascendant (Lagna) is {asc_sign}, indicating a {RASI_NAMES_EN[lagna_data['d1_sign']]} rising personality.
    This suggests you approach life with {['energy and initiative', 'stability and patience', 'curiosity and adaptability', 
    'emotional sensitivity', 'confidence and leadership', 'analytical precision', 'balance and harmony', 
    'intensity and transformation', 'optimism and exploration', 'discipline and ambition', 
    'innovation and independence', 'compassion and intuition'][lagna_data['d1_sign']]}.
    
    CORE INDICATORS:
    • Sun in {sun_place['sign']} ({sun_place['house']}H): {sun_place['interpretation'].split('.')[1][:100]}...
    • Moon in {moon_place['sign']} ({moon_place['house']}H): {moon_place['interpretation'].split('.')[1][:100]}...
    • Navamsa Lagna: {RASI_NAMES[lagna_data['d9_sign']]} (Spiritual inclinations)
    
    PLANETARY STRENGTHS:
    Strongest: {', '.join([f'{p[0]} ({p[1]}/10)' for p in strong_planets])}
    Areas needing attention: {', '.join([f'{p[0]} ({p[1]}/10)' for p in weak_planets])}
    
    KEY INFLUENCES:
    • Career indicator (10th lord) in house {((9 - lagna_data['d1_sign']) % 12) + 1}
    • Relationship indicator (7th house) ruled by {RASI_NAMES[(lagna_data['d1_sign'] + 6) % 12]}
    • Financial potential (2nd & 11th houses): Moderate to Good
    
    RECOMMENDATIONS:
    1. Enhance {strong_planets[0][0]}'s positive qualities
    2. Balance {weak_planets[0][0]} through remedial measures
    3. Focus on {HOUSE_MEANINGS[((9 - lagna_data['d1_sign']) % 12) + 1].split(',')[0]} for career growth
    """
    
    return summary.strip()

@app.get("/calculate_report")
def calculate_report(dob: str, tob: str, lat: float, lon: float):
    # 1. Parse Date/Time
    dt = datetime.strptime(f"{dob} {tob}", "%Y-%m-%d %H:%M")
    hour = dt.hour + dt.minute/60.0 + dt.second/3600.0
    jd = swe.julday(dt.year, dt.month, dt.day, hour - 5.5)  # IST to UT

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
        "nakshatra": NAKSHATRAS[int(lagna_sid / 13.3333)],
        "nakshatra_pada": int((lagna_sid % 13.3333) / 3.3333) + 1
    }

    # 4. Calculate Planets (D1 & D9)
    planet_data = []
    
    # 7 Main Planets
    for pid, name in PLANETS.items():
        if pid > 8:  # Skip Rahu/Ketu here, handle separately
            continue
        pos = swe.calc_ut(jd, pid)[0][0] if pid < 7 else swe.calc_ut(jd, swe.MEAN_NODE)[0][0]
        sid_pos = (pos - ayanamsa) % 360
        
        # Calculate aspects
        aspects = get_aspects(int(sid_pos / 30), name)
        
        planet_data.append({
            "id": pid,
            "name": name,
            "d1_sign": int(sid_pos / 30),
            "d9_sign": get_navamsa_sign(sid_pos),
            "degree": round(sid_pos % 30, 2),
            "nakshatra": NAKSHATRAS[int(sid_pos / 13.3333)],
            "pada": int((sid_pos % 13.3333) / 3.3333) + 1,
            "longitude": round(sid_pos, 4),
            "aspects": aspects,
            "retrograde": False  # Can calculate with swe.calc_ut(jd, pid, swe.FLG_SWIEPH)[0][3]
        })

    # 5. Generate Interpretations
    interpretations = generate_interpretation(planet_data, lagna_data)
    
    # 6. Generate Summary
    summary = generate_summary_report(lagna_data, planet_data, interpretations)
    
    # 7. Calculate Dashas
    dasha_info = get_current_dasha(dt)
    
    # 8. Panchangam
    panchang = get_panchangam(jd)
    
    # 9. Additional Metrics
    strengths = {p['planet']: p['strength'] for p in interpretations}
    
    return {
        "meta": {
            "dob": dob,
            "tob": tob,
            "place": f"{lat}, {lon}",
            "calculated_on": datetime.now().isoformat()
        },
        "chart": {
            "lagna": lagna_data,
            "planets": planet_data,
            "houses": [{"number": i+1, "sign": RASI_NAMES[int((houses[i] - ayanamsa) % 360 / 30)]} for i in range(12)]
        },
        "interpretations": interpretations,
        "summary_report": summary,
        "dasha": dasha_info,
        "panchang": panchang,
        "strengths": strengths,
        "recommendations": {
            "strengthen": [p for p in interpretations if p['strength'] < 4][:2],
            "focus_areas": [HOUSE_MEANINGS[i] for i in [1, 5, 9, 10]],
            "auspicious_times": f"Based on {panchang['nakshatra']}, good for starting new ventures"
        }
    }

@app.get("/")
def root():
    return {
        "message": "LagnaGuru Pro Astrology API",
        "version": "2.0",
        "endpoints": {
            "/calculate_report": "GET - Generate complete astrological report",
            "/docs": "API documentation"
        },
        "tagline": "Your Ascendant, Your Destiny"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
