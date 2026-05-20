with open("scratch/master_of_puppets.html", "r", encoding="utf-8") as f:
    html = f.read()

import re
match = re.search(r'<div id="apptab".*?</div>', html, re.DOTALL)
if match:
    print("APPTAB ELEMENT:")
    print(match.group(0))
else:
    # Print the lines around "apptab"
    lines = html.splitlines()
    for i, line in enumerate(lines):
        if "apptab" in line:
            print(f"Line {i}: {line}")
