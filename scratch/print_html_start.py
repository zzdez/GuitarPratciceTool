with open("scratch/song_raining_blood.html", "r", encoding="utf-8") as f:
    text = f.read()
print("LENGTH:", len(text))
print("FIRST 1000 CHARACTERS:")
print(text[:1000])
