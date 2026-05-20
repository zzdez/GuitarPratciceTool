import re

with open("scratch/master_of_puppets.html", "r", encoding="utf-8") as f:
    html = f.read()

stylesheets = re.findall(r'href="(https://static3\.songsterr\.com/.*?\.css)"', html)
print("STYLESHEETS:", stylesheets)
