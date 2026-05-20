with open("scratch/appClient.css", "r", encoding="utf-8") as f:
    css = f.read()

import re
matches = re.finditer(r'[^{}]*?max-tab-width[^{}]*?\{([^}]*?)\}', css)
print("MAX TAB WIDTH OCCURRENCES:")
for m in matches:
    print(m.group(0))

# Also search for "max-width:var(--max-tab-width)" or similar
print("\nGeneral search for '--max-tab-width' in CSS:")
lines = css.splitlines()
for line in lines:
    if "--max-tab-width" in line:
        print(line[:150])
