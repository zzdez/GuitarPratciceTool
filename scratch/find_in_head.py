import subprocess

res = subprocess.run(["git", "show", "HEAD:web/app.js"], capture_output=True, text=True, encoding="utf-8")
head_content = res.stdout

import re
matches = [m.start() for m in re.finditer("Songsterr Plus", head_content)]
print("Matches in HEAD:", matches)
if matches:
    pos = matches[0]
    print(repr(head_content[pos:pos+3000]))
