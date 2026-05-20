import json
import re

with open("scratch/songsterr.html", "r", encoding="utf-8") as f:
    html = f.read()

match = re.search(r'<script id="state" type="application/json">(.*?)</script>', html, re.DOTALL)
if match:
    state_text = match.group(1)
    state = json.loads(state_text)
    for key in ['screen', 'preferences', 'drawPreferences', 'drawSettings', 'browser', 'hash']:
        if key in state:
            print(f"{key.upper()}:", json.dumps(state[key], indent=2))
else:
    print("NO STATE ELEMENT FOUND")
