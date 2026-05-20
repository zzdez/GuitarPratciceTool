with open("scratch/appClient.css", "r", encoding="utf-8") as f:
    css = f.read()

import re
matches = re.finditer(r'([^{}]*?tablature[^{}]*?)\{([^}]*?)\}', css, re.IGNORECASE)
print("ALL TABLATURE RULES IN CSS:")
for m in matches:
    print(f"Selector: {m.group(1).strip()}")
    print(f"  Style: {m.group(2).strip()}")
