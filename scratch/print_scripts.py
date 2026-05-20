with open("scratch/song_raining_blood.html", "r", encoding="utf-8") as f:
    html = f.read()

import re
scripts = re.findall(r'<script.*?>', html)
for s in scripts:
    print(s)
