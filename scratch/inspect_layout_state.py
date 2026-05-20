import json
import re

with open("scratch/song_raining_blood.html", "r", encoding="utf-8") as f:
    html = f.read()

match = re.search(r'<script id="state" type="application/json">(.*?)</script>', html, re.DOTALL)
if match:
    state_text = match.group(1)
    state = json.loads(state_text)
    print("SCREEN:", state.get("screen"))
    print("PREFERENCES:", state.get("preferences"))
    print("DRAW PREFERENCES:", state.get("drawPreferences"))
    print("DRAW SETTINGS:", state.get("drawSettings"))
    print("BROWSER:", state.get("browser"))
