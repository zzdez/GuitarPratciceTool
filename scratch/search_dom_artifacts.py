import os
import glob
import re

folder = "C:/Users/ZZDeZ/.gemini/antigravity/brain/c7f4d6d5-5c16-4443-8586-91d93cdb5c8e/.tempmediaStorage"
txt_files = glob.glob(os.path.join(folder, "dom_*.txt"))
# Sort by size descending
txt_files.sort(key=lambda x: os.path.getsize(x), reverse=True)

print("TOTAL FILES:", len(txt_files))
for path in txt_files[:5]:
    size = os.path.getsize(path)
    print(f"File: {os.path.basename(path)}, Size: {size}")
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    svg_count = content.count("<svg")
    print(f"  SVG count: {svg_count}")
    # Let's search for "tablature"
    tab_classes = re.findall(r'class="[^"]*?tablature[^"]*?"', content, re.IGNORECASE)
    print(f"  Tab classes: {tab_classes[:3]}")
    # Let's print some HTML surrounding the tablature or print-preview if found
    if "tablature" in content.lower():
        print("  'tablature' found in content!")
        # Find some elements with id or class having tab
        matches = re.findall(r'<[^>]*?class="[^"]*?tablature[^"]*?"[^>]*?>', content, re.IGNORECASE)
        print(f"  Sample tags: {matches[:3]}")
