import json
import re

with open("scratch/song_raining_blood.html", "r", encoding="utf-8") as f:
    html = f.read()

match = re.search(r'<script id="state" type="application/json">(.*?)</script>', html, re.DOTALL)
if match:
    state_text = match.group(1)
    state = json.loads(state_text)
    print("CONSTRAINTS:", state["player"].get("constraints"))
    print("TYPE:", state["player"].get("type"))
    print("ONBOARDING:", state.get("onboarding"))
    print("DEMO:", state.get("demo"))
    print("PROMO:", state.get("promo"))
    print("ADS:", state.get("ads"))
