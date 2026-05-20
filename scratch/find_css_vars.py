with open("scratch/appClient.css", "r", encoding="utf-8") as f:
    css = f.read()

import re
variables = set(re.findall(r'--[a-zA-Z0-9_-]+', css))
print("ALL CSS VARIABLES IN APPCLIENT:")
for v in sorted(variables):
    print("-", v)
