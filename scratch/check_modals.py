content = open("web/index.html", "r", encoding="utf-8").read()
idx = content.find("settings-modal")
while idx != -1:
    lines = content[:idx].count("\n") + 1
    print("Found settings-modal in index.html at line:", lines)
    lines_list = content.split("\n")
    for i in range(lines-2, lines+15):
         line = lines_list[i].encode("ascii", "replace").decode("ascii")
         print(f"  {i+1}: {line}")
    idx = content.find("settings-modal", idx + 1)
