with open("scratch/appClient.css", "r", encoding="utf-8") as f:
    css = f.read()

# Let's search for some patterns
import re

print("LENGTH OF CSS:", len(css))

# Find media queries or classes containing print or scale or zoom
print("Searching for 'transform: scale'...")
matches = re.findall(r'[^{}]*?\{[^}]*?scale[^}]*?\}', css)
for m in matches[:10]:
    print("-", m.strip())

print("\nSearching for '@media print'...")
print("Found @media print count:", css.count("@media print"))

print("\nSearching for classes containing 'tablature'...")
matches_tab = re.findall(r'\.[a-zA-Z0-9_-]*?tablature[^{}]*?\{[^{}]*?\}', css)
for m in matches_tab[:10]:
    print("-", m.strip())
